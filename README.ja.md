# Whisper Toolkit

[English](README.md) | 日本語

<img src="docs/readme/00_Tool_Icon.png" width="200">

**OpenAI の音声認識モデル **Whisper** を、GUI から使えるようにしたツール** です。（Windows / macOS）

推論エンジンには本家 `openai-whisper` ではなく **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** を使っています。  
本家と同じモデルを最適化したもので、**CPU でも 4 倍程度速く**、**ffmpeg の別途インストールが不要**です。

**解説記事：** [【PySide6】Whisperで文字起こし・歌詞の表示時刻を取得するGUIツールを作る【Whisper Toolkit】](https://elekibear.com/post/20260907_01_whisper_toolkit)

| できること                                                                                    | 出力                               |
| --------------------------------------------------------------------------------------------- | ---------------------------------- |
| **文字起こし** — 音声/動画から全文テキストと字幕を書き出す                                    | `.txt` / `.srt` / `.vtt` / `.json` |
| **単語単位の時間** — 単語ごとの開始/終了時刻と確信度を書き出す                                | `.json` / `.csv`                   |
| **歌詞との突き合わせ** — 単語単位の時間に**正解の歌詞テキスト**を貼り直してカラオケ字幕を作る | `.json` / `.lrc` / `.srt`          |

<img src="docs/readme/01_Tool_GUI.png" width="720">

---

## 1. 必要環境

| 項目     | 内容                                                                                                                |
| -------- | ------------------------------------------------------------------------------------------------------------------- |
| OS       | Windows 10 / 11、macOS（Linux でも mac 用スクリプトがそのまま使えます）                                             |
| Python   | **3.13 に固定**（→ [docs/development/python_version.md](docs/development/python_version.md)）                       |
| ディスク | モデル用に 1〜5GB 程度（`small` で約 0.5GB、`large-v3` で約 3GB）                                                   |
| GPU      | 任意。NVIDIA GPU + CUDA 12 があれば大幅に高速化（無くても CPU で動きます）。**macOS は CUDA 非対応なので CPU 実行** |

---

## 2. セットアップ

仮想環境を作って依存をインストールします。

**Windows**（bat をダブルクリックでも可）

```bat
scripts\win\setup_venv.bat
```

GPU (CUDA 12) を使う場合は引数 `gpu` を付けると cuBLAS / cuDNN も一緒に入ります。

```bat
scripts\win\setup_venv.bat gpu
```

**macOS / Linux**

```sh
./scripts/mac/setup_venv.sh
```

実行できない場合は `chmod +x scripts/mac/setup_venv.sh` を一度実行してください。

どちらのスクリプトも、Python 3.13 を探して `.venv` を作り、
`requirements.txt`（faster-whisper と PySide6）をインストールします。

> 手動でやる場合は `py -3.13 -m venv .venv` →
> `.venv\Scripts\activate` → `pip install -r requirements.txt`。

---

## 3. 使い方

### 起動する

**Windows**（bat をダブルクリックでも可）

```bat
scripts\win\LaunchApp.bat
```

**macOS / Linux**

```sh
./scripts/mac/LaunchApp.sh
```

画面は上下 2 段で、上が入力タブ、下がログです。

### 音声を用意する

`input\audio\` フォルダに音声ファイル（wav / mp3 / m4a / mp4 など）を置くと、ファイル選択ダイアログが最初にそこを開きます。  
手元に無い場合は Windows の「サウンド レコーダー」で録音するか、標準の音声合成で作れます。

```powershell
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SetOutputToWaveFile("$PWD\input\audio\sample.wav")
$s.Speak("Hello. This is a Whisper sample for speech recognition.")
$s.Dispose()
```

macOS なら `say -o input/audio/sample.aiff "..."` で作れます。  
Whisper は内部で 16kHz モノラルに変換するため、事前変換は必須ではありません。

### Transcription タブ — 文字起こし

**音声/動画から全文テキストと字幕を書き出す機能** です。

`Input Audio` で音声を選び、必要に応じてオプションを変更して `Run` を押します。

<img src="docs/readme/02_Tool_Transcription.png" width="600">

#### Input / Output

| 項目           | 既定値       | 説明                                                                                  |
| -------------- | ------------ | ------------------------------------------------------------------------------------- |
| Input Audio    | 未指定       | 入力する音声／動画ファイル。`...` を押すと `input/audio/` から選択できます            |
| Output Dir     | `output/`    | 結果の書き出し先                                                                      |
| Output Formats | `txt`, `srt` | `txt` / `srt` / `vtt` / `json` から選択。すべて外すとファイルを書き出しません         |
| Task           | `transcribe` | `transcribe` は原語のまま文字起こし、`translate` は英語へ翻訳しながら文字起こしします |

#### Whisper Options

| 項目       | 既定値        | 説明                                                                                  |
| ---------- | ------------- | ------------------------------------------------------------------------------------- |
| Model      | `small`       | 使用する Whisper モデル。大きいモデルほど高精度ですが、処理時間と必要メモリが増えます |
| Language   | `Auto Detect` | 音声の言語。分かっている場合は指定した方が速く正確です                                |
| VAD Filter | ON            | Silero VAD で無音区間を除去します。歌の後半が崩れる場合は OFF も試してください        |

`output\<ファイル名>.transcribe.txt` などが書き出されます。

### Word Timestamps タブ — 単語単位の時間 + 歌詞の貼り直し

**単語ごとの開始/終了時刻と確信度を書き出す機能** です。  
オプションで **正解の歌詞テキストを貼り直してカラオケ字幕を作る機能** も同梱しています。

`Input Audio` で音声を選び、必要に応じてオプションを変更して `Run` を押します。

<img src="docs/readme/03_Tool_Word.png" width="600">

#### Input / Output

| 項目           | 既定値        | 説明                                                                       |
| -------------- | ------------- | -------------------------------------------------------------------------- |
| Input Audio    | 未指定        | 入力する音声／動画ファイル。`...` を押すと `input/audio/` から選択できます |
| Output Dir     | `output/`     | 結果の書き出し先                                                           |
| Output Formats | `json`, `csv` | 単語ごとの開始時刻・終了時刻・確信度を書き出す形式                         |

#### Whisper Options

| 項目       | 既定値        | 説明                                           |
| ---------- | ------------- | ---------------------------------------------- |
| Model      | `small`       | 使用する Whisper モデル                        |
| Language   | `Auto Detect` | 音声の言語。分かっている場合は指定を推奨します |
| VAD Filter | ON            | Silero VAD で無音区間を除去します              |

#### Lyrics Sync

| 項目           | 既定値        | 説明                                                              |
| -------------- | ------------- | ----------------------------------------------------------------- |
| Lyrics Sync    | OFF           | ON にすると、単語タイムスタンプ取得後に歌詞の貼り直しを実行します |
| Lyrics File    | 未指定        | 正解の歌詞テキスト。UTF-8、1 行 1 フレーズで用意します            |
| Lyrics Formats | `json`, `lrc` | 貼り直した歌詞の出力形式。`json` / `lrc` / `srt` から選べます     |
| Offset         | `0.00 sec`    | 出力時刻全体に加算する秒数。負値にすると歌詞を早く表示します      |
| Keep Blank     | OFF           | 歌詞の空行を残します。間奏で歌詞を消したい場合に使います          |

通常は `output\<ファイル名>.words.json` / `.words.csv` が書き出されます。

**Lyrics Sync** にチェックを入れて歌詞テキストを選ぶと、続けて「認識した時刻の上に正解の歌詞を貼り直す」後処理まで走り、カラオケ字幕 `.lrc` が書き出されます。  
ログの末尾に **一致率と「認識 → 歌詞」の差分**が出るので、「シュート → 周到」のように時刻はそのままで文字だけが直っていることを確認できます。

歌詞ファイルは **UTF-8 で 1 行 1 フレーズ**。  
空行・`#` の行・`【1番】` のような見出し行は自動でスキップされます。

### 実行中の操作

- 推論は別スレッドで動くので、実行中も画面は固まりません
- `Cancel` は**次のセグメント／単語が確定した時点で**止まります
- 選んだモデルが手元に無いときは、実行前にダウンロードの確認ダイアログが出ます
  （初回は数分かかることがあります）
- 完了すると出力フォルダが開きます
- ウィンドウの位置・サイズと入力値は終了時に保存され、次回起動時に戻ります
- `File > Clear Saved Settings...` で保存値を消去し、画面を既定値へ戻せます
- `Help > Open Document` でプロジェクトの GitHub ページを開けます

各オプションの詳細は **[docs/gui/usage.md](docs/gui/usage.md)** を参照してください。

---

## 4. フォルダ構成

```
python-whisper-sample/
├─ python/
│   └─ wsptoolkit/       GUI・CLI・処理をまとめたパッケージ
│       ├─ main.py           ← 起点。-m wsptoolkit.main で起動する
│       ├─ tool_config.py    タイトル・サイズ・リソースのパス
│       ├─ definitions.py    画面に並べる選択肢（モデル・言語・タスク）
│       ├─ logger.py         ログを画面へ流す
│       ├─ task_runner.py    推論を別スレッドで回す
│       ├─ gui/              Model / View / Controller と画面部品
│       ├─ cli/              3つのCLIモジュールと共通処理
│       └─ lib/              CLI / GUI 共用の処理本体
│           ├─ data/             受け渡すデータクラス
│           ├─ whisper/          Whisper の推論
│           ├─ lyrics/           歌詞との照合（Whisper 非依存）
│           └─ paths.py / settings.py / timecode.py
├─ resources/          アイコンとスタイルシート
├─ build_env/          PyInstaller でのビルド環境
├─ docs/               詳細ドキュメント
├─ input/              入力（中身は .gitignore 対象）
│   ├─ audio/            音声ファイルを置く
│   └─ lyrics/           歌詞テキストを置く
├─ output/             書き出し結果
├─ scripts/
│   ├─ win/setup_venv.bat / LaunchApp.bat
│   └─ mac/setup_venv.sh  / LaunchApp.sh
├─ .python-version     使う Python のバージョン (3.13)
├─ requirements.txt
└─ pyproject.toml      Ruff の設定
```

すべてのPythonコードは`python/wsptoolkit/`にまとめています。  
処理モジュールは画面出力もプロセス終了もしない（進捗は`logging`、失敗は例外）ので、CLIとGUIが同じAPIをそのまま呼べます。

入出力の既定パスは**カレントディレクトリではなくリポジトリルート基準**で解決されるため、どこから実行しても結果は同じ場所 (`output/`) に書き出されます。

---

## 5. CUI で実行する

GUI と同じ処理をコマンドラインからも実行できます。  
仮想環境を有効化してから実行してください（Windows は `.venv\Scripts\activate`、mac は `source .venv/bin/activate`）。  
Command Launcherと同様、検索パスには `<root>/python`だけを指定します。

```bat
REM Windows（リポジトリルートで実行）
set PYTHONPATH=%CD%\python
```

```sh
# macOS / Linux（リポジトリルートで実行）
export PYTHONPATH="$PWD/python"
```

```bat
REM ① 文字起こし
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 --model medium --language ja
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 --formats txt,srt,vtt,json

REM ② 単語単位の時間
python -m wsptoolkit.cli.word_timestamps input\audio\sample.mp3 --language ja
python -m wsptoolkit.cli.word_timestamps input\audio\song.wav -l ja -m large-v3 --no-vad

REM ③ 歌詞との突き合わせ（② の JSON を使う）
python -m wsptoolkit.cli.sync_lyrics song.words.json --lyrics input\lyrics\song.txt
python -m wsptoolkit.cli.sync_lyrics song.words.json --lyrics input\lyrics\song.txt --offset -0.3
```

GUI が画面に出していないオプション（`--device` / `--compute-type` / `--beam-size` / `--initial-prompt`、単語の絞り込み、繰り返し崩れ対策など）はすべて CLI 側にあります。  
全オプションは `-h` で確認できます。

- [docs/cli/common_options.md](docs/cli/common_options.md) — 共通オプション
- [docs/cli/transcribe.md](docs/cli/transcribe.md) — ① 文字起こし
- [docs/cli/word_timestamps.md](docs/cli/word_timestamps.md) — ② 単語単位の時間
- [docs/cli/sync_lyrics.md](docs/cli/sync_lyrics.md) — ③ 歌詞との突き合わせ

---

## 6. ドキュメント

詳しい仕様・オプション・実装の話は [docs/](docs/README.md) にあります。

|                                                                      |                                          |
| -------------------------------------------------------------------- | ---------------------------------------- |
| [docs/gui/usage.md](docs/gui/usage.md)                               | GUI の全オプション                       |
| [docs/guide/models.md](docs/guide/models.md)                         | モデルサイズの選び方                     |
| [docs/guide/gpu.md](docs/guide/gpu.md)                               | GPU (CUDA) で動かす                      |
| [docs/guide/word_timestamps_ja.md](docs/guide/word_timestamps_ja.md) | 日本語の注意点、長い曲が崩れるときの対処 |
| [docs/guide/troubleshooting.md](docs/guide/troubleshooting.md)       | トラブルシューティング                   |
| [docs/development/architecture.md](docs/development/architecture.md) | 全体構成と MVC の作り                    |
| [docs/development/build.md](docs/development/build.md)               | PyInstaller での exe / app 化            |
| [docs/instructions/code_guide.md](docs/instructions/code_guide.md)   | コーディングルール                       |

---
