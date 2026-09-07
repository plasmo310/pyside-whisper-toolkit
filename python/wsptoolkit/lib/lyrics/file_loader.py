"""歌詞テキストファイルを読んで LyricLine の並びにする。

`lyrics_sync.py` から呼ばれる部品。照合用の文字正規化もここに置く。
Whisper にも Word にも依存しない、純粋なテキスト処理。
"""

from __future__ import annotations

import re
import unicodedata

from wsptoolkit.lib.data import LyricLine

# 照合時に無視する記号。歌唱では発音されないものだけを並べる。
# 長音符「ー」と促音「っ/ッ」は発音そのものなので絶対に含めないこと。
# NFKC 後の文字と照合するので、全角記号だけでなく半角側 (. , ! ? など) も入れておく
# （「…」は NFKC で「...」になるなど、全角記号は半角に潰れてから判定される）。
_IGNORE_CHARS = set(
    "、。，．,.！？!?｢｣「」『』〈〉《》（）()［］[]｛｝{}"
    "…‥・､･:;：；\"'“”‘’＿_/／|｜*＊+＋=＝<>＜＞@＠#＃$＄%％&＆^＾`"
    "-−–—―~〜～\\￥＼"
)

# 【1番】(サビ) のような、行全体が括弧で囲まれたセクション見出し
_SECTION_RE = re.compile(r"^[\[【(（〔＜<].*[\]】)）〕＞>]$")


def _normalize_char(ch: str) -> str:
    """1 文字を照合用に正規化する。

    NFKC で全角英数・半角カナを揃え、カタカナはひらがなに寄せる
    （「キョロキョロ」と「きょろきょろ」の表記揺れを吸収するため）。
    半角の濁点分離 (ｶ + ﾞ) は 1 文字ずつ処理する都合上まとまらないが、
    歌詞では稀。

    Args:
        ch: 正規化する 1 文字。

    Returns:
        str: 正規化後の 1 文字。空白・記号など照合対象外の文字なら
            空文字列。
    """
    ch = unicodedata.normalize("NFKC", ch)
    if not ch:
        return ""
    ch = ch[0]  # 「㌔」→「キロ」のように増える場合があるので先頭だけ使う
    if ch.isspace() or ch in _IGNORE_CHARS:
        return ""
    code = ord(ch)
    if 0x30A1 <= code <= 0x30F6:  # カタカナ → ひらがな
        ch = chr(code - 0x60)
    return ch.lower()


def load_lyrics(
    path: str, keep_blank: bool = False
) -> tuple[list[LyricLine], int]:
    """歌詞ファイルを読み、照合対象の行を組み立てる。

    コメント行 (#) と 【1番】(サビ) のようなセクション見出し行は
    読み飛ばす。空行は keep_blank で扱いが変わる。

    Args:
        path: 歌詞テキストのパス (UTF-8、BOM 付きも可)。
        keep_blank: True なら空行を空の LyricLine として残す
            （間奏中に歌詞を消す目印になる）。False なら読み飛ばす。

    Returns:
        tuple[list[LyricLine], int]: (照合対象の行, 読み飛ばした行数)。

    Raises:
        OSError: ファイルを開けないとき。
    """
    with open(path, encoding="utf-8-sig") as f:
        raw_lines = f.read().splitlines()

    lines: list[LyricLine] = []
    skipped = 0
    for lineno, raw in enumerate(raw_lines, start=1):
        text = raw.strip().strip("　").strip()

        if not text:
            if keep_blank:
                lines.append(
                    LyricLine(index=len(lines), lineno=lineno, display="")
                )
            else:
                skipped += 1
            continue
        if text.startswith("#"):  # コメント行
            skipped += 1
            continue
        if _SECTION_RE.match(text):  # 【1番】(サビ) などの見出し行
            skipped += 1
            continue

        line = LyricLine(index=len(lines), lineno=lineno, display=text)
        chars = []
        for pos, ch in enumerate(text):
            norm = _normalize_char(ch)
            if norm:
                chars.append(norm)
                line.match_pos.append(pos)
        line.match_text = "".join(chars)
        lines.append(line)

    return lines, skipped
