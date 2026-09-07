# コーディングルール

このリポジトリに手を入れるときの決まりごとです。全体構成は
[../development/architecture.md](../development/architecture.md) を参照してください。

## 言語

- **識別子・UI の文字列・ログ・ファイル名は英語**
- **docstring とコメントは日本語**
- docstring は Google スタイル。`Args:` / `Returns:` / `Raises:` を使う。
  クラスには必要に応じて `Attributes:` を書く

```python
def resolve_input(path: str, default_dir: str | None = None) -> str:
    """入力ファイルのパスを解決する。

    Args:
        path: 利用者が指定したパス。絶対パスならそのまま扱う。
        default_dir: 3 番目に探す既定の置き場。None なら探さない。

    Returns:
        str: 実在が確認できた最初のパス。
    """
```

## 書式

- **Ruff** で `check` と `format` の両方を通す。設定は `pyproject.toml`
  ```bat
  ruff check python/wsptoolkit
  ruff format python/wsptoolkit
  ```
- **1 行 79 文字**、インデント 4 スペース、ダブルクォート
- `from __future__ import annotations` をファイル先頭に置く
- 型ヒントは引数・戻り値に必ず付ける（`-> None` も省略しない）。
  `str | None` の記法を使う

## 命名

- ファイルは `snake_case.py`。1 ファイル 1 クラスを基本とし、ファイル名は
  クラス名の snake_case（`main_view.py` → `MainView`）
- private な状態は `self.__foo`（ダブルアンダースコア）。公開は `@property`
- モジュール内だけで使うクラス・定数は先頭 1 つのアンダースコア
  （`_LogPane`, `_DEFAULT_FORMATS`）
- 接尾辞: `*_tab`（タブ）、`*_row`（入力行）、`*_panel`（コンテナ）、
  `*_config`、`*_runner`

### Qt のシグナルとスロット

- シグナルは `on_<動詞>_<名詞>_signal`（例: `on_click_run_signal`,
  `on_close_window_signal`）
- 受け側のスロットは `__on_<...>`（例: `__on_click_run_transcription_button`）

## MVC

- **View** は Qt のウィジェットだけ。Model / Controller を import しない。
  外への通知はクラス変数の `Signal`、外からの反映は公開メソッド
- **Model** は処理と永続化。Qt のウィジェットに触らない（`QSettings` は可）
- **Controller** が両方を生成し、`__setup_connections()` でシグナルを繋ぐ
- ダイアログは View 側に置き、Controller には `bool` などの結果だけ返す

### レイアウト

- レイアウトは `__build_<section>() -> QtWidgets.QWidget` を返す private
  ビルダーに分ける
- Qt の enum はフル修飾で書く
  （`QtCore.Qt.AlignmentFlag.AlignVCenter`。`Qt.AlignVCenter` とは書かない）
- 色・サイズは `resources/ui/stylesheet.qss` に置き、Python 側は
  `setProperty("class", "...")` でタグを付けるだけにする

## python/wsptoolkit/lib の約束

GUI からも CLI からも呼ぶので、次を守ります。

- `print()` しない。進捗は `logging`（`settings.get_logger(__name__)`）
- `sys.exit()` しない。失敗は `WhisperSampleError` を投げる
- 長い処理は逐次コールバックを受け取れるようにする
- 既定値は dataclass に持たせ、CLI と GUI の両方がそれを唯一の出どころにする
- 書き出しは `OutputDocument` を継承したデータクラス自身が知っている
  （呼び出し側に形式ごとの分岐を作らない）

## import

- `__init__.py` は置かない（暗黙の名前空間パッケージ）
- 書き分けは [../development/architecture.md](../development/architecture.md)
  の「import のルール」を参照
- 検索パスは`python`だけとし、`sys.path`をコードから変更しない
- サブパッケージをまたぐimportは`wsptoolkit`から始まる絶対importにする

## やらないこと

- `Reference/` は設計の参考として置いてあるだけなので**編集しない**
- `Reference/python/cmdlaunch/gui/main_model.py` にある
  `__logger = get_tool_logger()` をクラス内から参照するパターンは、名前
  マングリングで `NameError` になるので真似しない（`_logger` を使う）
