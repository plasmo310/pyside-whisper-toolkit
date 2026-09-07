# 本家 openai-whisper で書く場合

本ツールは推論エンジンに本家 `openai-whisper` ではなく
**[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** を使っています。

- 本家と同じ Whisper モデルを CTranslate2 で最適化したもの。**CPU でも 4 倍程度
  速く、メモリも少ない**
- 音声デコードに PyAV を同梱しているため **ffmpeg の別途インストールが不要**
  （Windows で詰まりやすい所を回避）
- `word_timestamps=True` で単語単位のタイムスタンプに標準対応

本家で書く場合は次のようになります。

```bat
pip install -r requirements-openai-whisper.txt
winget install Gyan.FFmpeg
```

（本家版は ffmpeg が PATH に必要です）

```python
import whisper

model = whisper.load_model("small")            # 初回はモデルを自動ダウンロード
result = model.transcribe(
    "input/audio/sample.mp3",
    language="ja",
    word_timestamps=True,                      # ← 単語単位の時刻
)

print(result["text"])                          # ① 文字起こし全文

for seg in result["segments"]:                 # ② 単語単位の時間
    for w in seg["words"]:
        print(f"{w['start']:7.2f} - {w['end']:7.2f}  {w['word']}")
```

API 名は違いますが、`word_timestamps=True` を渡す点も得られる情報も本ツールと同じです。
