# ① 文字起こし — `wsptoolkit.cli.transcribe`

音声/動画から全文テキストと字幕 (SRT/VTT/JSON) を書き出します。

```bat
REM 最小構成（言語は自動判定、結果は output\ へ）
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3

REM 日本語を明示 + 精度重視のモデル
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 --model medium --language ja

REM 字幕ファイルも一式書き出す
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 --formats txt,srt,vtt,json

REM 英語に翻訳しながら文字起こし
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 --task translate
```

実行例:

```
[info] loading model: small (device=cpu, compute_type=int8)
[info] detected language: ja (probability=0.99), duration=12.4s
[00:00:00.000 --> 00:00:04.120] 本日はお集まりいただきありがとうございます。
[00:00:04.120 --> 00:00:08.640] まずは先月の売上について報告します。

--- 全文 ---
本日はお集まりいただきありがとうございます。まずは先月の売上について報告します。

[info] 2 segments / 処理時間 3.4s (音声長の 3.6x speed)
[info] wrote output\sample.transcribe.txt
[info] wrote output\sample.transcribe.srt
```

出力ファイル: `output\<ファイル名>.transcribe.txt` / `.srt` / `.vtt` / `.json`

## 固有のオプション

共通オプションは [common_options.md](common_options.md) を参照。

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--task` | `transcribe` | `transcribe` = そのまま / `translate` = 英語に翻訳しながら文字起こし |
