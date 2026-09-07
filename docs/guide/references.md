# 参考文献

## Whisper 本体

- OpenAI Whisper (GitHub) — https://github.com/openai/whisper
- 論文: *Robust Speech Recognition via Large-Scale Weak Supervision* — https://arxiv.org/abs/2212.04356
- OpenAI 公式解説 — https://openai.com/index/whisper/
- Speech to text (OpenAI API 版) — https://platform.openai.com/docs/guides/speech-to-text

## 本ツールが使っている実装

- faster-whisper (GitHub) — https://github.com/SYSTRAN/faster-whisper
- CTranslate2 ドキュメント — https://opennmt.net/CTranslate2/
- Hugging Face のモデル (例: large-v3) — https://huggingface.co/Systran/faster-whisper-large-v3
- Silero VAD（無音区間除去） — https://github.com/snakers4/silero-vad

## 単語アライメントを深掘りする

- WhisperX — https://github.com/m-bain/whisperX
- stable-ts — https://github.com/jianfch/stable-ts
- 単語タイムスタンプの議論 (openai/whisper discussions) — https://github.com/openai/whisper/discussions/1478
- `difflib.SequenceMatcher`（③ が使っているテキスト照合） — https://docs.python.org/ja/3/library/difflib.html
- LRC フォーマット（拡張 LRC の文字タグを含む） — https://en.wikipedia.org/wiki/LRC_(file_format)

## GUI / 配布

- PySide6 (Qt for Python) — https://doc.qt.io/qtforpython-6/
- Qt Style Sheets Reference — https://doc.qt.io/qt-6/stylesheet-reference.html
- PyInstaller — https://pyinstaller.org/en/stable/

## Python 環境

- venv — 仮想環境の作成 — https://docs.python.org/ja/3/library/venv.html
- FFmpeg — https://ffmpeg.org/
