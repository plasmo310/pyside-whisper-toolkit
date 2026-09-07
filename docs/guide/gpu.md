# GPU で動かす（Windows / NVIDIA GPU）

macOS では CUDA を使えません（CTranslate2 は Metal 非対応）。Apple Silicon なら
CPU のまま `--compute-type int8` で実用的な速度が出ます。

```bat
scripts\win\setup_venv.bat gpu
.venv\Scripts\activate
python -m wsptoolkit.cli.transcribe input\audio\sample.mp3 --model large-v3-turbo --device cuda
```

`scripts\win\setup_venv.bat` に引数 `gpu` を付けて実行すると、cuBLAS / cuDNN も
一緒に入ります。

pip で入れた `nvidia-cublas-cu12` / `nvidia-cudnn-cu12` の DLL は PATH に載らない
ため、`python/wsptoolkit/lib/whisper/device.py`で`os.add_dll_directory()`に登録しています。

`--device auto` は「CUDA デバイスがある」だけでなく **`cublas64_12.dll` /
`cudnn64_9.dll` が実際にロードできるか**まで確認し、ダメなら CPU にフォール
バックします（確認せずに cuda を選ぶと推論の途中で
`Library cublas64_12.dll is not found` で落ちるため）。

`Could not load library cudnn_ops64_9.dll` のようなエラーが出る場合は cuDNN 9 系が
入っていないかバージョン不一致です。`scripts\win\setup_venv.bat gpu` を実行するか、
CPU (`--device cpu`) で実行してください。

> GUI には `Device` の項目がありません。`auto` 固定なので、CUDA が使える環境なら
> 自動的に GPU を使います。明示したいときは CLI を使ってください。
