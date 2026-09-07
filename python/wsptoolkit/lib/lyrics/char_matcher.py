"""認識結果と正解の歌詞を 1 文字ずつ照合し、歌詞側の文字に時刻を張る。

`lyrics_sync.py` から呼ばれる部品。

② が出した単語タイムスタンプは「Whisper が聞き取った文字」なので、
「番さ/晩さ」のような誤認識がそのまま時刻に紐づいている。一方で時刻
そのものは概ね正しいので、音声を再処理せずに difflib で照合し、時刻の
上に正しい文字を貼り直す。追加ライブラリは不要（標準ライブラリのみ）。

これは音声から時刻を作り直す「強制アライメント」ではない。時刻は ② が
出したものをそのまま使い、その上に載る文字だけを差し替える（→ README §6）。
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from wsptoolkit.lib.data import LyricLine, Word

from .file_loader import _normalize_char


@dataclass
class DiffRow:
    """差分レポートの 1 行。

    Attributes:
        at: この差分が起きた時刻 (秒)。不明なら None。
        hyp: 認識側の文字列。歌詞にしか無い箇所は "(認識なし)"。
        ref: 歌詞側の文字列。認識にしか無い箇所は "(歌詞になし)"。
        note: 補足（"一致" / "※ 時刻は前後から補間" / "※ 無視"）。
    """

    at: float | None
    hyp: str
    ref: str
    note: str


@dataclass
class MatchReport:
    """照合の統計と差分。

    差分の組み立てに要る生データ（正規化前の文字列・opcode）は
    非公開の属性として持ち、外へは `diff_rows()` で整形して渡す。

    Attributes:
        ref_len: 歌詞側の照合対象文字数。
        matched: 認識と直接一致した文字数。
        interpolated: 時刻を補間で埋めた行数。
    """

    ref_len: int = 0
    matched: int = 0
    interpolated: int = 0
    _hyp_src: list[str] = field(default_factory=list, repr=False)
    _hyp_starts: list[float | None] = field(default_factory=list, repr=False)
    _ref_src: list[str] = field(default_factory=list, repr=False)
    _ref_starts: list[float | None] = field(default_factory=list, repr=False)
    _opcodes: list[tuple[str, int, int, int, int]] = field(
        default_factory=list, repr=False
    )

    @property
    def match_rate(self) -> float:
        """一致率 (0.0-1.0)。

        Returns:
            float: matched / ref_len。歌詞が空なら 0.0。
        """
        return (self.matched / self.ref_len) if self.ref_len else 0.0

    def diff_rows(self, show_all: bool = False) -> list[DiffRow]:
        """認識 → 歌詞 の差分を行のリストにする。

        表示は呼び出し側 (CLI / GUI) の役目。時刻は歌詞側の開始時刻を
        使うが、歌詞に対応が無い delete 行だけは認識側の時刻を使う。

        Args:
            show_all: True なら一致した箇所も含めて全件返す。
                False なら差分のある箇所だけ。

        Returns:
            list[DiffRow]: 差分の行。
        """
        rows: list[DiffRow] = []
        for tag, i1, i2, j1, j2 in self._opcodes:
            if tag == "equal" and not show_all:
                continue
            hyp_text = _ellipsis("".join(self._hyp_src[i1:i2]))
            ref_text = _ellipsis("".join(self._ref_src[j1:j2]))
            if tag == "delete":
                # 歌詞側に対応が無いので、時刻は認識側から取る
                source = self._hyp_starts
                at = source[i1] if i1 < len(source) else None
            else:
                source = self._ref_starts
                at = source[j1] if j1 < len(source) else None

            if tag == "insert":
                rows.append(
                    DiffRow(
                        at,
                        "(not recognized)",
                        ref_text,
                        "Note: timestamp interpolated from adjacent lines",
                    )
                )
            elif tag == "delete":
                rows.append(
                    DiffRow(at, hyp_text, "(not in lyrics)", "Note: ignored")
                )
            elif tag == "replace":
                rows.append(DiffRow(at, hyp_text, ref_text, ""))
            else:
                rows.append(DiffRow(at, hyp_text, ref_text, "match"))
        return rows


def _ellipsis(s: str, limit: int = 24) -> str:
    """表示が崩れないよう長すぎる差分を省略する。

    Args:
        s: 省略対象の文字列。
        limit: 省略後の最大文字数（末尾の「…」を含む）。

    Returns:
        str: limit 以下ならそのまま、超えていれば末尾を「…」にした文字列。
    """
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _build_hyp(words: list[Word]) -> tuple[str, list[int], list[str]]:
    """認識結果の word 列を照合用の 1 本の文字列にする。

    差分レポートで「番さ」と元表記のまま見せたいので、正規化前の文字も
    並行して残す。

    Args:
        words: 単語のリスト。

    Returns:
        tuple[str, list[int], list[str]]: (正規化文字列, 各文字がどの
            word 由来かを示すインデックスのリスト, 各文字の正規化前の
            文字のリスト)。3 つの長さは一致する。
    """
    norm_chars: list[str] = []
    owners: list[int] = []
    src_chars: list[str] = []
    for wi, w in enumerate(words):
        for ch in w.word:
            norm = _normalize_char(ch)
            if not norm:
                continue
            norm_chars.append(norm)
            owners.append(wi)
            src_chars.append(ch)
    return "".join(norm_chars), owners, src_chars


def _build_ref(
    lines: list[LyricLine],
) -> tuple[str, list[tuple[int, int]], list[str]]:
    """歌詞側を照合用の 1 本の文字列にする。

    Args:
        lines: LyricLine のリスト。

    Returns:
        tuple[str, list[tuple[int, int]], list[str]]: (正規化文字列,
            各文字の (行 index, 行内の match_text 上の位置) のリスト,
            各文字の正規化前の文字のリスト)。3 つの長さは一致する。
    """
    norm_chars: list[str] = []
    owners: list[tuple[int, int]] = []
    src_chars: list[str] = []
    for line in lines:
        for k, ch in enumerate(line.match_text):
            norm_chars.append(ch)
            owners.append((line.index, k))
            src_chars.append(line.display[line.match_pos[k]])
    return "".join(norm_chars), owners, src_chars


def _fill_gaps(
    starts: list[float | None],
    ends: list[float | None],
    duration: float | None,
    max_char: float = 0.0,
) -> None:
    """時刻が付かなかった文字の区間を、前後の既知時刻で等分して埋める。

    Args:
        starts: 文字ごとの開始時刻。None の要素がここで埋まる
            （破壊的に更新する）。
        ends: 文字ごとの終了時刻。starts と同じ長さで、同様に更新する。
        duration: 音声全体の長さ (秒)。末尾が未割り当てのときの右端に使う。
            None なら直前の終了時刻で代用する。
        max_char: 1 文字あたりの持ち時間の上限 (秒)。0 で無制限。
            前後の既知時刻の間隔が広すぎる（＝長い間奏を挟んで Whisper が
            丸ごと聞き逃した）場合に、歌詞を間奏いっぱいに引き伸ばさず、
            左端に詰めて残りを空けておくために使う。こうすると再生側で
            「間奏中は歌詞が消える」挙動になる。

    Returns:
        None: starts と ends を破壊的に更新する。
    """
    n = len(starts)
    i = 0
    while i < n:
        if starts[i] is not None:
            i += 1
            continue
        j = i
        while j < n and starts[j] is None:
            j += 1
        # [i, j) が未割り当ての区間。前後の既知時刻で挟んで等分する
        left = ends[i - 1] if i > 0 else 0.0
        if j < n:
            right = starts[j]
        elif duration is not None:
            right = max(duration, left)
        else:
            right = left
        right = max(right, left)
        step = (right - left) / (j - i)
        if max_char > 0:
            step = min(step, max_char)  # 広すぎる間隔は詰める（右側を空ける）
        for k in range(i, j):
            starts[k] = left + step * (k - i)
            ends[k] = left + step * (k - i + 1)
        i = j


def match_chars(
    words: list[Word],
    lines: list[LyricLine],
    duration: float | None = None,
    max_char: float = 0.0,
) -> MatchReport:
    """認識結果と歌詞を difflib で照合し、歌詞側の各文字に時刻を張る。

    difflib の対応は単調なので、1 番と 2 番で同じ歌詞が繰り返されても
    順序は壊れない。opcode ごとの扱いは次の通り。

    - equal   : 認識側 word の時刻をそのまま使う
    - replace : 認識側の区間を歌詞側の文字数で比例配分する
    - insert  : 聞き逃し。_fill_gaps() で前後から補間する
    - delete  : 認識にしかない「あー」等。無視する

    Args:
        words: 認識結果の単語のリスト。
        lines: LyricLine のリスト。各行の start / end / char_times /
            matched_chars / interpolated を破壊的に更新する。
        duration: 音声全体の長さ (秒)。末尾の補間に使う。
        max_char: 1 文字あたりの持ち時間の上限 (秒、0 で無制限)。
            詳細は _fill_gaps() を参照。

    Returns:
        MatchReport: 一致率などの統計と、差分レポート用のデータ。
    """
    hyp, hyp_owner, hyp_src = _build_hyp(words)
    ref, ref_owner, ref_src = _build_ref(lines)
    hyp_starts = [words[wi].start for wi in hyp_owner]

    starts: list[float | None] = [None] * len(ref)
    ends: list[float | None] = [None] * len(ref)
    assigned: list[bool] = [False] * len(ref)
    matched = 0
    opcodes: list[tuple[str, int, int, int, int]] = []

    matcher = difflib.SequenceMatcher(None, hyp, ref, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        opcodes.append((tag, i1, i2, j1, j2))

        if tag == "equal":
            # 認識と歌詞が一致。word の時刻をそのまま使う
            for k in range(j2 - j1):
                w = words[hyp_owner[i1 + k]]
                starts[j1 + k] = w.start
                ends[j1 + k] = w.end
                assigned[j1 + k] = True
            matched += j2 - j1

        elif tag == "replace":
            # 誤認識。文字は違っても「その時間帯を歌っている」ことは合っているので、
            # 認識側の区間の時間幅を歌詞側の文字数で比例配分する
            left = words[hyp_owner[i1]].start
            right = words[hyp_owner[i2 - 1]].end

            if (j2 - j1) > 2 * (i2 - i1):
                # 歌詞の方が極端に長い = Whisper がその区間をほぼ聞き逃していて、
                # たまたま数文字だけ拾ってしまった状態。認識できた数文字の時間幅に
                # 押し込むと歌詞が一瞬に潰れるので、前後の無音まで含めた区間に広げる
                if i1 > 0:
                    prev_end = words[hyp_owner[i1 - 1]].end
                    if prev_end is not None:
                        left = min(left, prev_end)
                if i2 < len(hyp_owner):
                    next_start = words[hyp_owner[i2]].start
                    if next_start is not None:
                        right = max(right, next_start)

            if left is None or right is None or right < left:
                continue
            span = (right - left) / (j2 - j1)
            if max_char > 0:
                span = min(span, max_char)  # 聞き逃し区間を広げすぎない
            for k in range(j2 - j1):
                starts[j1 + k] = left + span * k
                ends[j1 + k] = left + span * (k + 1)
                assigned[j1 + k] = True

        # tag == "insert" (歌詞にしかない = 聞き逃し) は _fill_gaps で補間する
        # tag == "delete" (認識にしかない = 余計な「あー」等) は無視する

    _fill_gaps(starts, ends, duration, max_char)

    # 文字の時刻を行に集約する
    for j, (line_index, k) in enumerate(ref_owner):
        line = lines[line_index]
        if line.start is None or starts[j] < line.start:
            line.start = starts[j]
        if line.end is None or ends[j] > line.end:
            line.end = ends[j]
        line.char_times[line.match_pos[k]] = (starts[j], ends[j])
        if assigned[j]:
            line.matched_chars += 1

    # 照合対象の文字が無かった行（空行・記号だけの行）を前後から補間する
    for line in lines:
        if line.start is not None:
            line.interpolated = line.matched_chars == 0
            continue
        line.interpolated = True
        prev_end = next(
            (
                other.end
                for other in reversed(lines[: line.index])
                if other.end is not None
            ),
            0.0,
        )
        next_start = next(
            (
                other.start
                for other in lines[line.index + 1 :]
                if other.start is not None
            ),
            None,
        )
        if next_start is None:
            next_start = duration if duration is not None else prev_end
        line.start = prev_end
        line.end = max(next_start, prev_end)

    # 単調性を保証する（LRC は時刻が前後すると再生側の表示が壊れる）
    prev = None
    for line in lines:
        if prev is not None and line.start <= prev:
            line.start = prev + 0.01
        if line.end is None or line.end < line.start:
            line.end = line.start
        prev = line.start

    return MatchReport(
        ref_len=len(ref),
        matched=matched,
        interpolated=sum(1 for line in lines if line.interpolated),
        _hyp_src=hyp_src,
        _hyp_starts=hyp_starts,
        _ref_src=ref_src,
        _ref_starts=starts,
        _opcodes=opcodes,
    )
