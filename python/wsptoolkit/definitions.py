"""画面に並べる選択肢の定義。

値はそのまま処理モジュールに渡せる文字列にしてあるので、画面と処理側の
あいだで変換を挟まない。ここに無いモデルや言語を使いたいときは CLI
(`wsptoolkit.cli`) を使う。
"""

from __future__ import annotations

from enum import Enum


class ModelType(Enum):
    """モデルの選択肢。値は Whisper に渡すモデル名。"""

    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE_V3 = "large-v3"
    LARGE_V3_TURBO = "large-v3-turbo"
    DISTIL_LARGE_V3 = "distil-large-v3"

    @classmethod
    def from_name(cls, name: str) -> ModelType | None:
        """モデル名から種別を返却する。該当が無ければ None。"""
        for member in cls:
            if member.value == name:
                return member
        return None


class LanguageType(Enum):
    """言語の選択肢。

    Attributes:
        code (str): Whisper に渡す言語コード。空文字なら自動判定。
        label (str): プルダウンに出す表示名。
    """

    AUTO = ("", "Auto Detect")
    JAPANESE = ("ja", "Japanese (ja)")
    ENGLISH = ("en", "English (en)")
    CHINESE = ("zh", "Chinese (zh)")
    KOREAN = ("ko", "Korean (ko)")
    SPANISH = ("es", "Spanish (es)")
    FRENCH = ("fr", "French (fr)")
    GERMAN = ("de", "German (de)")
    ITALIAN = ("it", "Italian (it)")
    PORTUGUESE = ("pt", "Portuguese (pt)")
    RUSSIAN = ("ru", "Russian (ru)")

    def __init__(self, code: str, label: str) -> None:
        """メンバを作る。

        Args:
            code: Whisper に渡す言語コード。
            label: プルダウンに出す表示名。
        """
        self.code = code
        self.label = label

    @classmethod
    def from_code(cls, code: str | None) -> LanguageType:
        """言語コードから種別を返却する。該当が無ければ AUTO。"""
        for member in cls:
            if member.code == (code or ""):
                return member
        return cls.AUTO


class TaskType(Enum):
    """文字起こしの種別。値は WhisperManager.transcribe() の task。"""

    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"

    @classmethod
    def from_name(cls, name: str) -> TaskType:
        """種別名から種別を返却する。該当が無ければ TRANSCRIBE。"""
        for member in cls:
            if member.value == name:
                return member
        return cls.TRANSCRIBE
