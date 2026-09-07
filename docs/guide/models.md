# モデルサイズの目安

| モデル | パラメータ | メモリ目安 | 相対速度 | 用途 |
| --- | --- | --- | --- | --- |
| `tiny` | 39M | ~1GB | 最速 | 動作確認 |
| `base` | 74M | ~1GB | 速い | 下書き |
| `small` | 244M | ~2GB | 中 | **日本語の実用下限・本ツールの既定** |
| `medium` | 769M | ~5GB | 遅い | 日本語で精度が要るとき |
| `large-v3` | 1550M | ~10GB | 最遅 | 最高精度 |
| `large-v3-turbo` | 809M | ~6GB | large の約 5 倍速 | 精度と速度のバランス |
| `distil-large-v3` | — | ~6GB | 速い | 英語中心の蒸留モデル |

## モデルのダウンロードについて

初回実行時に Hugging Face からモデルが自動ダウンロードされ、
Windows なら `%USERPROFILE%\.cache\huggingface\hub`、macOS / Linux なら
`~/.cache/huggingface/hub` にキャッシュされます（2 回目以降はオフラインで動作）。

GUI では、選んだモデルが手元に無いときに実行前の確認ダイアログが出ます
（判定は `whisper.is_model_downloaded()`）。

ディスクはモデル用に 1〜5GB 程度を見ておいてください
（`small` で約 0.5GB、`large-v3` で約 3GB）。
