# ② 単語単位の時間 — `wsptoolkit.cli.word_timestamps`

単語ごとの開始/終了時刻と確信度を取得して JSON/CSV に書き出します。
`word_timestamps=True` を指定すると、Whisper の cross-attention から
**DTW（動的時間伸縮）** で各単語の時刻が推定されます。

```bat
REM 単語ごとの時刻を表示し、JSON と CSV に書き出す
python -m wsptoolkit.cli.word_timestamps input\audio\sample.mp3 --language ja

REM 確信度 0.5 未満の単語だけ表示（聞き取りが怪しい箇所の洗い出し）
python -m wsptoolkit.cli.word_timestamps input\audio\sample.mp3 --min-prob 0.5

REM 特定の語が何秒に出てくるか探す
python -m wsptoolkit.cli.word_timestamps input\audio\sample.mp3 --find 売上

REM 歌もので後半が繰り返し・ハルシネーションで崩れるとき
python -m wsptoolkit.cli.word_timestamps input\audio\song.wav -l ja -m large-v3 --no-vad
```

実行例:

```
       start           end   prob  word
------------------------------------------------
00:00:00.000  00:00:00.520   0.98  本日
00:00:00.520  00:00:00.780   0.99  は
00:00:00.780  00:00:01.460   0.95  お集まり
...
[info] 143 words / 2 segments
[info] 平均確信度 0.921
[info] wrote output\sample.words.json
[info] wrote output\sample.words.csv
```

CSV の列: `index, segment_id, word, start, end, duration, probability`

JSON の構造:

```json
{
  "model": "small",
  "language": "ja",
  "duration": 12.4,
  "segments": [{ "id": 0, "start": 0.0, "end": 4.12, "text": "本日は…" }],
  "words":    [{ "index": 0, "segment_id": 0, "word": "本日",
                 "start": 0.0, "end": 0.52, "probability": 0.98 }]
}
```

## 固有のオプション

共通オプションは [common_options.md](common_options.md) を参照。

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--min-prob P` | なし | この確信度未満の単語だけを**表示**する（書き出しは常に全単語） |
| `--find WORD` | なし | 指定した文字列を含む単語だけを**表示**する（同上） |
| `--no-condition-on-previous-text` | 使う | 直前の出力を次区間のプロンプトにしない |
| `--no-repeat-ngram-size N` | `0` | 同じ N-gram の連続生成を禁止。0 で無効 |
| `--hallucination-silence-threshold SEC` | なし | ハルシネーション検出時に無音区間をスキップ |

下 3 つは長い曲が崩れるとき用です。使い分けは
[../guide/word_timestamps_ja.md](../guide/word_timestamps_ja.md) を参照してください。
