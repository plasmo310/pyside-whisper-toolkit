# GUI (Whisper Toolkit) の使い方

`scripts\win\LaunchApp.bat` / `./scripts/mac/LaunchApp.sh` で起動します。
画面は上下 2 段で、上が入力タブ、下がログです。

- 推論は別スレッドで動くので、実行中も画面は固まりません
- `Cancel` は **次のセグメント／単語が確定した時点で**止まります
- ログ欄には CLI と同じ内容が流れます (`File > Clear Log` で消去)
- 完了すると出力フォルダが開きます
- ウィンドウの位置・サイズと各タブの入力値は終了時に保存され、次回起動時に戻ります
- `File > Clear Saved Settings...` で保存値を消去し、画面を既定値へ戻せます
- `Help > Open Document` でプロジェクトの GitHub ページを開けます

## 共通オプション (Whisper Options)

2 つのタブに共通で、`WhisperConfig` (`python/wsptoolkit/lib/whisper/whisper_manager.py`)
に 1 対 1 で対応します。

| 項目 | 既定 | 説明 |
| --- | --- | --- |
| Model | `small` | モデルサイズ。選択肢は `python/wsptoolkit/definitions.py` の `ModelType` |
| Language | `Auto Detect` | 言語。選択肢は同ファイルの `LanguageType`。**指定した方が速く正確** |
| VAD Filter | ON | 無音区間を除去する Silero VAD。歌もので後半が崩れるときは、まずこれを OFF |

**画面に無いオプションは CLI 側にあります。** `--device` / `--compute-type` /
`--beam-size` / `--initial-prompt`、単語の絞り込み (`--min-prob` / `--find`)、
繰り返し崩れ対策のデコード調整、LRC のタグまわりなどは
[cli/common_options.md](../cli/common_options.md) を参照してください。
GUI が指定しない項目は CLI と同じ既定値で動きます。

選択肢を増やしたいときは `python/wsptoolkit/definitions.py` の Enum に
1 行足してください。

## Transcription タブ

音声を文字起こしします (CLI の `wsptoolkit.cli.transcribe` と同じ)。

| 項目 | 既定 | 説明 |
| --- | --- | --- |
| Input Audio | — | 入力音声/動画。空欄なら `input/audio/` からダイアログが開く |
| Output Dir | `output/` | 書き出し先 |
| Output Formats | `txt` `srt` | `txt` / `srt` / `vtt` / `json`。全部外すと書き出さない |
| Task | `transcribe` | `translate` を選ぶと英語に翻訳しながら文字起こし |

出力: `output/<名前>.transcribe.txt` など。

## Word Timestamps タブ

単語ごとの開始/終了時刻と確信度を取ります (CLI の
`wsptoolkit.cli.word_timestamps` と同じ)。

| 項目 | 既定 | 説明 |
| --- | --- | --- |
| Input Audio | — | 入力音声/動画 |
| Output Dir | `output/` | 書き出し先 |
| Output Formats | `json` `csv` | `json` / `csv` |

出力: `output/<名前>.words.json` / `.words.csv`。

### Lyrics Sync

チェックを入れると、単語タイムスタンプの取得に続けて
**正解の歌詞テキストで文字を貼り直し**、カラオケ字幕 (LRC) を書き出します
(CLI の `wsptoolkit.cli.sync_lyrics` と同じ)。音声もモデルも触らない後処理です。

| 項目 | 既定 | 説明 |
| --- | --- | --- |
| Lyrics File | — | 正解の歌詞テキスト (UTF-8、1 行 1 フレーズ) |
| Lyrics Formats | `json` `lrc` | `json` / `lrc` / `srt` |
| Offset | `0.00 sec` | 全時刻に加算する秒数 (負値で早出し) |
| Keep Blank | OFF | 歌詞の空行を残す。VAD Filter を OFF にしたときは合わせて ON |

ログの末尾に **一致率と「認識 → 歌詞」の差分レポート**が出ます。
これがこの機能の本体で、「シュート → 周到」のように時刻はそのままで文字だけが
正しく差し替わっていることを確認できます。一致率が低いときは、たいてい歌詞
ファイル側の問題です。詳しくは [cli/sync_lyrics.md](../cli/sync_lyrics.md)。

> `sync_lyrics()` は `.words.json` のファイルを読むので、Lyrics Sync が ON の
> ときに `Output Formats` の `json` が外れていると、自動で足して書き出します
> (その旨をログに 1 行出します)。

## モデル未ダウンロード時の確認

選んだモデルが手元に無いときは、実行前に「ダウンロードに数分かかることがある」
という確認ダイアログを出します。判定は
`whisper.is_model_downloaded()` (Hugging Face のキャッシュを見る) です。

初回のダウンロード先は Windows なら `%USERPROFILE%\.cache\huggingface\hub`、
macOS / Linux なら `~/.cache/huggingface/hub` で、2 回目以降はオフラインで動きます。
