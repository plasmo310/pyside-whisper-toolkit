"""Whisper (faster-whisper) を扱うパッケージ。

起点は `whisper_manager.py` の `WhisperManager`。ここを読めば流れが分かる。

    whisper_manager.py   ← 起点。モデルのロードから推論までを通す
      └ device.py            CPU / CUDA の判定

結果は `data` のデータクラスで受け取り、そのクラス自身の `write()` で
ファイルに書き出す。

    from wsptoolkit.lib.data import TranscriptionResult
    from wsptoolkit.lib.whisper import WhisperConfig, WhisperManager

    manager = WhisperManager(WhisperConfig(model="small", language="ja"))
    result = manager.transcribe("input/audio/sample.mp3")
    result.write("output", "sample", ["txt", "srt"])
"""

from .whisper_manager import (
    MODEL_CHOICES,
    DecodeOptions,
    WhisperConfig,
    WhisperManager,
    is_model_downloaded,
)

__all__ = [
    "MODEL_CHOICES",
    "DecodeOptions",
    "WhisperConfig",
    "WhisperManager",
    "is_model_downloaded",
]
