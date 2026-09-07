# CLI 共通オプション

リポジトリルートで`PYTHONPATH=python`相当を設定し、`python -m`で起動します。
Windowsは`set PYTHONPATH=%CD%\python`、macOS / Linuxは
`export PYTHONPATH="$PWD/python"`です。

`wsptoolkit.cli.transcribe` (①) と `wsptoolkit.cli.word_timestamps` (②) で共通です。
定義は`python/wsptoolkit/cli/common.py`の`add_whisper_args()` / `add_output_args()`。

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `-m, --model` | `small` | `tiny` / `base` / `small` / `medium` / `large-v3` / `large-v3-turbo` / `distil-large-v3` またはローカルパス |
| `-l, --language` | 自動判定 | `ja`, `en` など。**指定した方が速く正確** |
| `-d, --device` | `auto` | `cpu` / `cuda`。auto は CUDA があれば使う |
| `--compute-type` | 自動 | `int8` / `int8_float16` / `float16` / `float32` |
| `--beam-size` | `5` | 大きいほど高精度・低速。`1` で greedy |
| `--no-vad` | — | 無音除去 (Silero VAD) を無効化 |
| `--initial-prompt` | なし | 固有名詞や表記を揃えるヒント文（例: `--initial-prompt "議事録、Whisper、CTranslate2"`） |
| `-o, --output-dir` | `output` | 書き出し先 |
| `-f, --formats` | ① `txt,srt` ② `json,csv` | カンマ区切り。`none` で書き出さない |

全オプションは`python -m wsptoolkit.cli.transcribe -h`で確認できます。

## 入出力パスの解決

入出力の既定パスは**カレントディレクトリではなくリポジトリルート基準**で
解決されるため、どのディレクトリから実行しても結果は同じ場所 (`output/`) に
書き出されます。入力ファイルは相対パスなら「カレント → リポジトリルート →
既定の置き場」の順に探すので、`input/audio/song.wav` でも `song.wav` だけでも
渡せます (`python/wsptoolkit/lib/paths.py` の `resolve_input()`)。

## 出力ファイル名

`<名前>.<ラベル>.<形式>` に統一されています。

| サンプル | ラベル | 例 |
| --- | --- | --- |
| ① 文字起こし | `transcribe` | `song.transcribe.srt` |
| ② 単語単位の時間 | `words` | `song.words.json` |
| ③ 歌詞との突き合わせ | `lyrics` | `song.lyrics.lrc` |
