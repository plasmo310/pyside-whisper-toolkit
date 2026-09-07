# 全体構成

```
python/
└─ wsptoolkit/   GUI・CLI・処理本体をまとめたパッケージ
```

## python/wsptoolkit — アプリケーションパッケージ

Whisper の推論も歌詞の照合もここにあります。**画面出力もプロセス終了もしない**
のが約束で、そのおかげで CLI からも GUI からも同じ API を呼べます。

| 決まりごと | 理由 |
| --- | --- |
| `print()` しない。進捗は `logging` の `whisper_sample` 名前空間へ | 呼ぶ側が Handler を差し替えるだけで出力先を変えられる |
| `sys.exit()` しない。失敗は `WhisperSampleError` | GUI から呼んだときにプロセスが落ちない |
| 長い処理は逐次コールバック (`on_segment` / `on_word`) を受け取る | 進捗表示と協調キャンセルに使える |
| 既定値は dataclass (`WhisperConfig` など) が持つ | CLI と GUI で既定がずれない |

```
wsptoolkit/
├─ main.py             ← GUI の起点。QApplication を作って Controller を起動
├─ cli/                コマンドラインの入口
│   ├─ common.py           共通の引数・ログ処理
│   ├─ transcribe.py
│   ├─ word_timestamps.py
│   └─ sync_lyrics.py
├─ tool_config.py      GUI の設定とリソースのパス
├─ definitions.py      画面に並べる選択肢の Enum
├─ logger.py           logging を Qt のシグナルへ中継
├─ task_runner.py      時間のかかる処理を回す QThread
├─ gui/                Model / View / Controller と画面部品
└─ lib/                CLI / GUI 共用の処理本体
    ├─ data/               受け渡すデータクラス
    │   ├─ interface.py        共通の約束ごと (OutputDocument)
    │   ├─ transcription.py    ① Segment / TranscriptionResult
    │   ├─ word_timings.py     ② Word / WordTimingsResult
    │   └─ lyrics.py           ③ LyricLine / LyricsDocument
    ├─ whisper/            Whisper の推論
    │   ├─ whisper_manager.py  ← WhisperManager / WhisperConfig
    │   └─ device.py           CPU / CUDA の判定
    ├─ lyrics/             歌詞との照合（Whisper 非依存）
    │   ├─ lyrics_sync.py      ← sync_lyrics()
    │   ├─ file_loader.py      歌詞ファイルの読み込みと文字の正規化
    │   └─ char_matcher.py     difflib で 1 文字ずつ照合
    ├─ paths.py            入出力フォルダの解決
    ├─ settings.py         OS 差分 / 例外 / ロガー
    └─ timecode.py         時刻の書式 (SRT / LRC)
```

`data/` の各クラスは「自分をどの形式でどう書き出すか」を自分で知っているので、
呼び出し側は形式ごとの分岐を持ちません。

```python
from wsptoolkit.lib.whisper import WhisperConfig, WhisperManager

manager = WhisperManager(WhisperConfig(model="small", language="ja"))
result = manager.transcribe("input/audio/sample.mp3")   # data.TranscriptionResult
result.write("output", "sample", ["txt", "srt"])        # 書き出し方は結果自身が知っている
```

## GUI

Command Launcher (`Reference/`) と同じ手書き MVC です。

```
gui/
    ├─ main_model.py       処理モジュールの呼び出しと QSettings への保存
    ├─ main_view.py        タブとログの組み立て
    ├─ main_controller.py  View と Model の接続
    └─ widgets/
        ├─ option_rows.py           入力行と共通の Whisper オプション
        ├─ transcription_tab.py     ① のタブ
        └─ word_timestamps_tab.py   ② + ③ のタブ
```

### 役割分担

- **View** は Qt のウィジェットだけを持ちます。Model を知らず、Controller への
  通知はクラス変数の `Signal` (`on_*_signal`)。ダイアログは View 側
  (`show_confirm_dialog()` は bool を返すだけ)。
- **Model** は処理モジュールの呼び出しと `QSettings` への保存を持ちます。
  Qt のウィジェットには触りません。
- **Controller** が両方を作り、`__setup_connections()` で View の Signal を
  `__on_*` ハンドラに繋ぎます。Controller の存在は他のどこも知りません。

### 実行の流れ

```
Run 押下
  → View が Request dataclass を emit
  → Controller: モデルが未ダウンロードなら確認ダイアログ
  → Controller: View.set_running(True) → TaskRunner を起動
  → 進捗: TaskRunner.on_progress_signal → View.append_log()
          whisper_sample ロガー → logger.LogBridge → 同じログ欄
  → 完了 / 失敗: on_finished_signal / on_error_signal
```

### スレッドとキャンセル

推論は `TaskRunner` (QThread) で回します。`WhisperManager` にキャンセル用の
フックは無いので、`on_segment` / `on_word` のコールバックから
`TaskCanceledError` を投げてループを抜ける協調キャンセルにしています
(`gui/main_model.py`)。したがって Cancel は **次のセグメント／単語が確定した
時点で**効きます。

`MainModel` は `WhisperManager` を 1 つ保持し、`WhisperConfig` が変わったときだけ
作り直します（モデルの再ロードを避けるため）。

## import のルール

`PYTHONPATH=<root>/python`から`wsptoolkit`を解決します（Command Launcherと同じ）。
公開APIをまとめる`lib/data` / `lib/lyrics` / `lib/whisper`以外は、暗黙の名前空間パッケージです。

| 場所 | 書き方 |
| --- | --- |
| `main.py` | 相対 (`from .gui.main_controller import ...`) |
| `gui/` の中で兄弟を参照 | 相対 (`from .main_model import MainModel`) |
| `gui/` からパッケージ直下 | 絶対 (`from wsptoolkit.logger import ...`) |
| `gui/widgets/` | 常に絶対 (`from wsptoolkit.gui.widgets.option_rows import ...`) |
| サブパッケージをまたぐ参照 | 絶対 (`from wsptoolkit.lib.whisper import ...`) |
| 同一サブパッケージ内 | 相対 (`from .device import pick_device`) |

検索パスに加えるのは`<root>/python`だけです。追加の検索パスや`sys.path`を変更する
ブートストラップは使いません。GUIは`python -m wsptoolkit.main`、CLIは
`python -m wsptoolkit.cli.<command>`で起動します。

## 見た目

配色とサイズは `resources/ui/stylesheet.qss` にまとめ、Python 側は
`setProperty("class", ...)` でタグを付けるだけにしています。

- 背景 `#090a0d` / パネル `#0f1216` / グループ `#14171c` / 入力欄 `#0b0d11`
- 文字 `#ecedf0`、補助 `#9ea6b2`、無効 `#5b626d`
- アクセント青 `#1f6be5`、ボタン青 `#1a3d85`

`{RESOURCES_DIR}` プレースホルダは `ToolConfig.load_stylesheet()` が
`resources/` の絶対パスへ置換します（QSS の `url()` はカレントディレクトリ基準で
解決されてしまうため）。

### 縦位置を揃える

入力行は `ToolConfig.ROW_HEIGHT` に高さを固定し、中のウィジェットを全部
`AlignVCenter` で入れています（`gui/widgets/option_rows.py`）。ラベルと
チェックボックスの高さが違っても行の中心に並びます。

ボタンやタブの高さは QSS 側で指定しています。Python から `setFixedSize()` しても
スタイルシートの `min-height` に上書きされてしまうためです。

### スクロールバーの幅

タブごとにスクロールバーが出たり消えたりすると入力欄の幅がずれるため、
`build_form_scroll_area()` は縦スクロールバーの場所を常に確保し、スクロールが
不要なときは無効化して QSS 側でつまみを消しています。
