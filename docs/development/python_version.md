# Python のバージョン固定について

このプロジェクトは **Python 3.13 系に固定**しています。バージョンの記載場所は
次の 4 か所です。

| ファイル | 役割 |
| --- | --- |
| `.python-version` | `3.13`。pyenv-win / uv などのバージョン管理ツールが読む |
| `scripts\win\setup_venv.bat` / `scripts/mac/setup_venv.sh` の `PYVER` | セットアップ時に実際に使う Python を決める |
| `python/wsptoolkit/cli/common.py` の `_REQUIRED_PYTHON` | CLI 起動時の警告に使う |
| `pyproject.toml` の `target-version` | Ruff がどの文法・非推奨 API を前提に見るか |

`build_env/scripts/*/Setup.*` にも同じ `PYVER` があります。

固定の効き方:

- 3.13 が見つからないとセットアップスクリプトは**インストールを始めずに終了**します
- 既にある `.venv` が 3.13 でなければ、その旨を表示して停止します
  （`.venv` を削除して作り直してください）
- CLI は起動時に実行中の Python を確認し、違っていれば `[warn]` を出します
  （`.venv` を有効化し忘れてシステムの Python で動かしている、という取り違えに
  気づくため）

**別のバージョンに切り替えるとき**は上の 4 か所（+ `build_env`）を揃えて書き換え、
`.venv` を作り直してください。

> パッチバージョン（`3.13.13` など）までは固定していません。`venv` は既にある
> Python を使うだけでインタプリタ自体は入れないため、パッチまで揃えたい場合は
> pyenv-win や uv でインタプリタを管理し、`.python-version` にフルバージョンを
> 書いてください。

> `scripts\win\setup_venv.bat` などの bat は **Shift_JIS (CP932) + CRLF** で
> 保存しています（cmd.exe はバッチファイルをシステムの ANSI コードページで
> 解釈するため）。編集するときは文字コードを変えないでください。なお pyenv-win の
> `python` はバッチファイル（シム）なので、bat 内から呼ぶ箇所には `call` を
> 付けています。
