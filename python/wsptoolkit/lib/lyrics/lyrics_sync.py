"""このパッケージの起点。words.json と歌詞テキストを突き合わせる。

「file_loader.py で読み込む → char_matcher.py で照合する → 書き出せる
LyricsDocument を作る」までを `sync_lyrics()` の 1 回の呼び出しにまとめる。
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from wsptoolkit.lib.data import LyricsDocument, LyricsMeta, WordTimingsResult
from wsptoolkit.lib.settings import WhisperSampleError, get_logger

from .char_matcher import MatchReport, match_chars
from .file_loader import load_lyrics

logger = get_logger(__name__)


@dataclass
class SyncOptions:
    """歌詞の貼り直しの設定。CLI のオプションと 1 対 1 で対応する。

    Attributes:
        keep_blank: 歌詞の空行を残すか（間奏で歌詞を消す目印になる）。
        offset: 全時刻に加算する秒数（負値で早出し）。
        max_gap_fill: Whisper が丸ごと聞き逃した区間を歌詞で埋めるときの
            1 文字あたり上限秒。0 で無効。
        word_tags: 拡張 LRC (<mm:ss.xx> の文字タグ) を付けるか。
        end_tag: LRC の最終行の後ろに終了時刻だけの行を入れるか。
        title: LRC の [ti:] タグ。
        artist: LRC の [ar:] タグ。
    """

    keep_blank: bool = False
    offset: float = 0.0
    max_gap_fill: float = 0.6
    word_tags: bool = False
    end_tag: bool = True
    title: str | None = None
    artist: str | None = None


@dataclass
class SyncResult:
    """`sync_lyrics()` の結果。

    Attributes:
        document: 書き出せる時刻付き歌詞。
        report: 一致率などの統計と差分レポート。
    """

    document: LyricsDocument
    report: MatchReport


def sync_lyrics(
    words_json_path: str,
    lyrics_path: str,
    options: SyncOptions | None = None,
) -> SyncResult:
    """words.json と歌詞テキストを突き合わせ、時刻付き歌詞を作る。

    Args:
        words_json_path: ② が出した `<名前>.words.json` のパス。
        lyrics_path: 正解の歌詞テキストのパス (UTF-8, 1行1フレーズ)。
        options: 貼り直しの設定。None なら既定値。

    Returns:
        SyncResult: 書き出せる LyricsDocument と照合の統計。

    Raises:
        WhisperSampleError: 入力が無い、words が空、歌詞に対象行が
            無いとき。
    """
    options = options or SyncOptions()

    if not os.path.isfile(words_json_path):
        raise WhisperSampleError(
            f"Words JSON not found: {words_json_path}"
        )
    if not os.path.isfile(lyrics_path):
        raise WhisperSampleError(
            f"Lyrics file not found: {lyrics_path}"
        )

    words = WordTimingsResult.load(words_json_path)
    lines, skipped = load_lyrics(lyrics_path, keep_blank=options.keep_blank)
    if not lines:
        raise WhisperSampleError(
            f"No usable lyric lines found: {lyrics_path}"
        )

    logger.info(
        "Loaded %d lyric lines (%d skipped)", len(lines), skipped
    )
    logger.info(
        "Recognition result: %d words / duration=%s",
        len(words.words),
        words.duration,
    )

    report = match_chars(
        words.words,
        lines,
        duration=words.duration,
        max_char=options.max_gap_fill,
    )

    document = LyricsDocument(
        lines=lines,
        meta=LyricsMeta(
            title=options.title,
            artist=options.artist,
            duration=words.duration,
            model=words.model,
            language=words.language,
            match_rate=round(report.match_rate, 4),
        ),
        offset=options.offset,
        word_tags=options.word_tags,
        end_tag=options.end_tag,
    )
    return SyncResult(document=document, report=report)
