"""入出力フォルダの場所を解決するモジュール。

Whisper とは無関係な「このリポジトリのフォルダ構成」だけを扱う。

    <ルート>/python/wsptoolkit/lib/  ... ライブラリ（このファイルの置き場所）
    <ルート>/python/wsptoolkit/cli/  ... CLI モジュール
    <ルート>/input/audio/   ... 入力音声
    <ルート>/input/lyrics/  ... 歌詞テキスト
    <ルート>/output/        ... 書き出し結果

既定のパスは「実行時のカレントディレクトリ」ではなく
「このファイルの位置から辿ったリポジトリルート」を基準にする。
そうしないと実行時のカレントディレクトリに `output/` が作られてしまう。

Attributes:
    LIB_DIR (str): ライブラリ (`python/wsptoolkit/lib/`) の絶対パス。
    PACKAGE_DIR (str): パッケージ (`python/wsptoolkit/`) の絶対パス。
    ROOT_DIR (str): リポジトリルートの絶対パス。
    INPUT_DIR (str): 入力ルート (`input/`) の絶対パス。
    AUDIO_DIR (str): 入力音声の既定の置き場 (`input/audio/`)。
    LYRICS_DIR (str): 歌詞テキストの既定の置き場 (`input/lyrics/`)。
    OUTPUT_DIR (str): 書き出し先 (`output/`)。
"""

from __future__ import annotations

import os

LIB_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(LIB_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(PACKAGE_DIR))
INPUT_DIR = os.path.join(ROOT_DIR, "input")
AUDIO_DIR = os.path.join(INPUT_DIR, "audio")
LYRICS_DIR = os.path.join(INPUT_DIR, "lyrics")
OUTPUT_DIR = os.path.join(ROOT_DIR, "output")


def resolve_input(path: str, default_dir: str | None = None) -> str:
    """入力ファイルのパスを解決する。

    1. 指定されたパスをそのまま（＝カレントディレクトリ基準）
    2. リポジトリルート基準
    3. 既定の置き場 (input/audio, input/lyrics, output) 基準

    の順に探し、最初に見つかったものを返す。

    これにより、リポジトリのどこから実行しても `input/audio/a.wav` と
    書けるうえ、ファイル名だけ (`a.wav`) を渡しても既定の置き場から拾える。

    Args:
        path: 利用者が指定したパス。絶対パスならそのまま扱う。
        default_dir: 3 番目に探す既定の置き場。None なら探さない。

    Returns:
        str: 実在が確認できた最初のパス。どれも見つからなければ `path`
            をそのまま返す（存在チェックと "見つかりません" の表示は
            呼び出し側の役目）。
    """
    candidates = [path]
    if not os.path.isabs(path):
        candidates.append(os.path.join(ROOT_DIR, path))
        if default_dir is not None:
            candidates.append(os.path.join(default_dir, path))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return path
