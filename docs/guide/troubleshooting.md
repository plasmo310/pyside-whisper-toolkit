# トラブルシューティング

| 症状 | 対処 |
| --- | --- |
| `'python' は認識されていません` | Python 未インストール、または PATH 未設定。インストーラで「Add python.exe to PATH」を有効に |
| GUI が起動しない / `Not found python env.` | セットアップ未実施。`scripts\win\setup_venv.bat` を実行する |
| `faster-whisper が見つかりません` | 仮想環境を有効化していない。Windows は `.venv\Scripts\activate`、mac は `source .venv/bin/activate` |
| `ModuleNotFoundError: No module named 'PySide6'` | GUI 用の依存が入っていない。`pip install -r requirements.txt` |
| PowerShell で activate できない | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| 初回実行が固まって見える | モデルのダウンロード中（`small` で約 0.5GB）。GUI なら事前に確認ダイアログが出る |
| コンソールが文字化けする | `chcp 65001` で UTF-8 に。出力ファイルは UTF-8（CSV は Excel 用に BOM 付き） |
| 精度が低い | 言語を明示する / `medium` 以上のモデル / `--initial-prompt` で固有名詞を与える |
| 同じ語を延々繰り返す | Whisper のハルシネーション。VAD の on/off を切り替える、モデルを変える、ノイズ除去で改善することがある |
| 長い曲で後半がまるごと欠ける | 間奏の無音を VAD が削ってのループ。VAD Filter を OFF にする（→ [word_timestamps_ja.md](word_timestamps_ja.md)） |
| CPU で遅い | `tiny` / `base`、`--beam-size 1`、`distil-large-v3` を試す |
| `Library cublas64_12.dll is not found` | GPU 用ライブラリ不足。`scripts\win\setup_venv.bat gpu` を実行するか `--device cpu`（→ [gpu.md](gpu.md)） |
| bat の日本語が化ける / 途中で止まる | bat を UTF-8 で保存し直していないか確認（CP932 で保存する） |
| mac で `permission denied` | `chmod +x scripts/mac/setup_venv.sh` を一度実行する |
| mac で `Python 3.13 が見つかりません` | `brew install python@3.13` または `pyenv install 3.13` |
