# ビルド（PyInstaller で exe / app にする）

`build_env/` に、アプリ本体とは別の仮想環境を作ってビルドします
（実行用の `.venv` に PyInstaller を混ぜないため）。

```
build_env/
├─ requirements.txt        アプリの依存 + pyinstaller
├─ python/run.py           PyInstaller の入口
└─ scripts/
    ├─ win/{Setup.bat, BuildApp.bat}
    └─ mac/{Setup.sh, BuildApp.sh}
```

## 1. ビルド環境を作る

```bat
REM Windows
build_env\scripts\win\Setup.bat
```

```sh
# macOS / Linux
./build_env/scripts/mac/Setup.sh
```

`build_env/.venv` に、`requirements.txt`（= 本体の依存）と PyInstaller が入ります。

## 2. ビルドする

```bat
REM Windows
build_env\scripts\win\BuildApp.bat
```

```sh
# macOS / Linux
./build_env/scripts/mac/BuildApp.sh
```

`build_env/scripts/<os>/dist/WhisperToolkit/` に出力されます。

## 何をしているか

```
pyinstaller --noconsole --onedir --name WhisperToolkit
    --paths <root>/python
    --hidden-import PySide6
    --collect-all faster_whisper
    --collect-all ctranslate2
    --collect-all onnxruntime
    --add-data <root>/resources;./resources
    --icon <root>/resources/icon/tool_icon_rect.ico
    build_env/python/run.py
```

- `--paths`には`python`だけを渡します。アプリケーションコードはすべて
  `wsptoolkit`パッケージとして収集されます。
- `--collect-all` は faster-whisper が同梱する VAD モデルや、CTranslate2 /
  onnxruntime のネイティブライブラリを取りこぼさないためです。
- `--add-data` で `resources/`（アイコンとスタイルシート）を同梱します。
  `ToolConfig` が `sys._MEIPASS` を見て、固めた場合は `_internal/resources/` を
  参照するようになっています。

入口の `build_env/python/run.py` は `-m wsptoolkit.main` の代わりです。

```python
from wsptoolkit.main import main

main()
```

アイコンは Windows が `tool_icon_rect.ico`、macOS が `tool_icon_round.icns` です。

## 注意

- 固めた実行ファイルは faster-whisper / CTranslate2 を含むため**数百 MB 規模**に
  なります。
- Whisper モデル自体は同梱されません。初回起動時に Hugging Face から
  ダウンロードされ、ユーザーのキャッシュに置かれます。
- `build_env/.venv` と `dist` / `build` は `.gitignore` 対象です。
