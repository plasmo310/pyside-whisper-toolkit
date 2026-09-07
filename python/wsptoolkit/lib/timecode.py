"""秒数を字幕・歌詞フォーマットの時刻文字列にする。

SRT / VTT 用 (`HH:MM:SS.mmm`) と LRC 用 (`mm:ss.xx`) は桁も区切りも
違う別物なので、関数を分けてある。
"""

from __future__ import annotations


def format_timestamp(seconds: float | None, sep: str = ".") -> str:
    """秒数を HH:MM:SS.mmm 形式にする。

    Args:
        seconds: 秒数。None は 0.0、負値は 0 に丸めて扱う。
        sep: 秒とミリ秒の区切り文字。SRT 用には "," を渡す。

    Returns:
        str: "HH:MM:SS.mmm" 形式の文字列。
    """
    if seconds is None:
        seconds = 0.0
    ms = int(round(seconds * 1000.0))
    ms = max(ms, 0)
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{ms:03d}"


def format_lrc_time(seconds: float | None) -> str:
    """秒数を LRC の mm:ss.xx 形式にする。

    format_timestamp() は HH:MM:SS.mmm で LRC 用とは別物なので流用しない。

    Args:
        seconds: 秒数。None と負値は 0.0 として扱う。

    Returns:
        str: "mm:ss.xx" 形式の文字列 (xx は 1/100 秒)。
    """
    if seconds is None or seconds < 0:
        seconds = 0.0
    centis = round(seconds * 100)
    minutes, centis = divmod(centis, 6000)
    secs, centis = divmod(centis, 100)
    return f"{minutes:02d}:{secs:02d}.{centis:02d}"
