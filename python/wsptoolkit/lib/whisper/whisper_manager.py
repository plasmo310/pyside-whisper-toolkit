"""このパッケージの起点。Whisper の呼び出しをまとめた WhisperManager。

モデルのロードから推論、結果データへの詰め替えまでを 1 クラスに閉じ込める。
呼び出し側は次の 3 行で済む。

    manager = WhisperManager(WhisperConfig(model="small", language="ja"))
    result = manager.transcribe("input/audio/sample.mp3")
    result.write("output", "sample", ["txt", "srt"])

GUI から使うときのために

- 画面出力は `logging` 経由（`print` しない）
- 依存が無いときは例外を投げる（`sys.exit` しない）
- 長い音声でも進捗を返せるよう逐次コールバックを受け取る
- モデルはインスタンスに保持するので、続けて複数ファイルを処理できる

という作りにしてある。
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass

from wsptoolkit.lib.data import (
    Segment,
    TranscriptionResult,
    Word,
    WordTimingsResult,
)
from wsptoolkit.lib.settings import (
    ACTIVATE_HINT,
    SETUP_SCRIPT,
    WhisperSampleError,
    get_logger,
)

from .device import pick_device

logger = get_logger(__name__)

# --model のヘルプに出す代表的なモデル名
MODEL_CHOICES = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v2",
    "large-v3",
    "large-v3-turbo",
    "turbo",
    "distil-large-v3",
]


def is_model_downloaded(model: str) -> bool:
    """モデルが手元にあるか（＝初回ダウンロードが不要か）を返す。

    初回実行では Hugging Face から数百 MB〜数 GB を取得するので、
    GUI から「時間がかかる」と事前に案内するために使う。

    Args:
        model: モデルサイズ名、またはローカルのモデルディレクトリ。

    Returns:
        bool: 手元にあれば True。判定できないときは True
            （余計な警告を出さない）。
    """
    if os.path.isdir(model):
        return True
    try:
        from faster_whisper.utils import _MODELS
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return True

    repo_id = _MODELS.get(model)
    if repo_id is None:
        return True
    # キャッシュに無いときは None、あるときはファイルのパスが返る
    return isinstance(try_to_load_from_cache(repo_id, "model.bin"), str)


@dataclass
class WhisperConfig:
    """推論の設定。CLI の共通オプションと 1 対 1 で対応する。

    Attributes:
        model: モデルサイズ名 (small, large-v3 など) またはローカルの
            モデルディレクトリのパス。
        language: 言語コード (ja, en ...)。None なら自動判定。
        device: "auto" / "cpu" / "cuda"。
        compute_type: 計算精度 (int8, float16 など)。None なら device に
            応じて自動で決める。
        beam_size: ビームサーチ幅。
        vad: 無音区間を除去する VAD フィルタを使うか。
        initial_prompt: 固有名詞や表記ゆれを揃えるためのヒント文。
    """

    model: str = "small"
    language: str | None = None
    device: str = "auto"
    compute_type: str | None = None
    beam_size: int = 5
    vad: bool = True
    initial_prompt: str | None = None


@dataclass
class DecodeOptions:
    """繰り返し・ハルシネーション対策の追加デコード設定。

    サビの連呼などでデコーダがループに陥り、後半がまるごと崩れるときに
    使う。既定値は faster-whisper の既定と同じ（＝何もしない）。

    Attributes:
        condition_on_previous_text: 直前の出力を次区間のプロンプトに使うか。
        no_repeat_ngram_size: 同じ N-gram の連続生成を禁止する。0 で無効。
        hallucination_silence_threshold: ハルシネーションを検出した無音区間を
            スキップする閾値 (秒)。None で無効。
    """

    condition_on_previous_text: bool = True
    no_repeat_ngram_size: int = 0
    hallucination_silence_threshold: float | None = None


class WhisperManager:
    """Whisper モデルを保持して推論を回す。

    `load()` を呼ばずに `transcribe()` などを呼んだ場合は、その中で
    自動的にロードする。
    """

    def __init__(self, config: WhisperConfig | None = None) -> None:
        """マネージャを作る（この時点ではモデルをロードしない）。

        Args:
            config: 推論の設定。None なら既定値。
        """
        self.config = config or WhisperConfig()
        self._model = None

    def load(self) -> None:
        """デバイスを決めてモデルをロードする。

        初回はモデルが手元に無いため、Hugging Face から自動ダウンロード
        される（数十秒〜数分かかる）。GUI から呼ぶときは別スレッドで。

        Returns:
            None

        Raises:
            WhisperSampleError: faster-whisper が未インストールのとき。
        """
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise WhisperSampleError(
                f"faster-whisper was not found. Run {SETUP_SCRIPT}, activate "
                f"the virtual environment with `{ACTIVATE_HINT}`, and try "
                "again."
            ) from e

        device, compute_type = pick_device(
            self.config.device, self.config.compute_type
        )
        logger.info(
            "loading model: %s (device=%s, compute_type=%s)",
            self.config.model,
            device,
            compute_type,
        )
        self._model = WhisperModel(
            self.config.model,
            device=device,
            compute_type=compute_type,
        )

    def transcribe(
        self,
        audio_path: str,
        task: str = "transcribe",
        on_segment: Callable[[Segment], None] | None = None,
    ) -> TranscriptionResult:
        """音声を文字起こしする (サンプル①)。

        Args:
            audio_path: 入力音声/動画のパス。
            task: "transcribe" (そのまま) / "translate" (英語に翻訳)。
            on_segment: セグメントが 1 つ確定するたびに呼ばれる関数。
                長い音声の進捗表示に使う。

        Returns:
            TranscriptionResult: セグメントと全文、処理時間を含む結果。

        Raises:
            WhisperSampleError: faster-whisper が未インストールのとき。
        """
        self.load()

        started = time.perf_counter()
        # segments はジェネレータ。for で回した時点ではじめて推論が進む。
        segments, info = self._model.transcribe(
            audio_path,
            language=self.config.language,
            task=task,
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad,
            initial_prompt=self.config.initial_prompt,
        )
        self._report_detected(info)

        collected: list[Segment] = []
        for seg in segments:
            item = Segment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
            )
            collected.append(item)
            if on_segment is not None:
                on_segment(item)

        return TranscriptionResult(
            model=self.config.model,
            language=info.language,
            language_probability=info.language_probability,
            duration=info.duration,
            segments=collected,
            elapsed=time.perf_counter() - started,
        )

    def transcribe_words(
        self,
        audio_path: str,
        options: DecodeOptions | None = None,
        on_word: Callable[[Word], None] | None = None,
    ) -> WordTimingsResult:
        """単語単位のタイムスタンプを取得する (サンプル②)。

        word_timestamps=True を指定すると、Whisper の cross-attention から
        DTW (Dynamic Time Warping) で各単語の開始/終了時刻が推定される。

        Args:
            audio_path: 入力音声/動画のパス。
            options: 繰り返し崩れ対策の追加設定。None なら既定値。
            on_word: 単語が 1 語確定するたびに呼ばれる関数。

        Returns:
            WordTimingsResult: 単語とセグメントを含む結果。

        Raises:
            WhisperSampleError: faster-whisper が未インストールのとき。
        """
        self.load()
        options = options or DecodeOptions()

        segments, info = self._model.transcribe(
            audio_path,
            language=self.config.language,
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad,
            initial_prompt=self.config.initial_prompt,
            word_timestamps=True,  # ← これが単語単位の時刻取得のポイント
            condition_on_previous_text=options.condition_on_previous_text,
            no_repeat_ngram_size=options.no_repeat_ngram_size,
            hallucination_silence_threshold=(
                options.hallucination_silence_threshold
            ),
        )
        self._report_detected(info)

        collected: list[Segment] = []
        words: list[Word] = []
        for seg in segments:
            collected.append(
                Segment(
                    id=seg.id,
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                )
            )
            for w in seg.words or []:
                item = Word(
                    index=len(words),
                    segment_id=seg.id,
                    # 前後の空白を含む「そのまま」の表記
                    word=w.word,
                    start=w.start,
                    end=w.end,
                    probability=w.probability,
                )
                words.append(item)
                if on_word is not None:
                    on_word(item)

        return WordTimingsResult(
            model=self.config.model,
            language=info.language,
            duration=info.duration,
            segments=collected,
            words=words,
        )

    def _report_detected(self, info) -> None:
        """言語判定の結果を通知する。

        Args:
            info: faster-whisper の TranscriptionInfo。
        """
        logger.info(
            "detected language: %s (probability=%.2f), duration=%.1fs",
            info.language,
            info.language_probability,
            info.duration,
        )
