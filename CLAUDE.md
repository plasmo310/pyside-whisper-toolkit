# CLAUDE.md

Whisper Toolkit — faster-whisper を使った文字起こし / 単語タイムスタンプ /
歌詞同期のツール。GUI (PySide6) と CLI の 2 つの入口を持つ。

詳細は `docs/` にあります。**このファイルには内容を複製せず、必ずそちらを見てください。**

## まずこれを読む

| 目的 | ドキュメント |
| --- | --- |
| **コードを書く前に必ず** | [docs/instructions/code_guide.md](docs/instructions/code_guide.md) |
| 全体構成・MVC・import のルール | [docs/development/architecture.md](docs/development/architecture.md) |
| ドキュメントの一覧 | [docs/README.md](docs/README.md) |
| 使い方（利用者向け） | [README.md](README.md) |

## 構成のかいつまみ

```
python/wsptoolkit/  GUI・CLI・処理本体をまとめたパッケージ
  cli/              コマンドラインの入口
  lib/              data / lyrics / whisper と CLI / GUI 共用処理
resources/          アイコンと stylesheet.qss（色とサイズは全部ここ）
build_env/          PyInstaller でのビルド環境
Reference/          設計の参考（Command Launcher）。編集しない
```

## よく使うコマンド

```bat
REM GUI 起動
scripts\win\LaunchApp.bat

REM Lint / Format（変更したら必ず通す）
ruff check python/wsptoolkit
ruff format python/wsptoolkit

REM CLI
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 -l ja
```

`ruff` は `requirements.txt` に入っていないので、必要なら一時的に入れて
使い終わったら消してください（実行用 `.venv` を汚さないため）。

## 気をつけること

- `python/wsptoolkit/lib`の約束（`print`しない / `sys.exit`しない / 失敗は
  `WhisperSampleError`）を壊さない
- 色・サイズは `resources/ui/stylesheet.qss` に置く。Python 側にハードコード
  しない
- `Reference/` は読むだけ。編集しない
- 1 行 79 文字、docstring とコメントは日本語、識別子と UI 文字列は英語
