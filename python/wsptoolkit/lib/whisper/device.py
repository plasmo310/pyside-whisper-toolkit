"""推論デバイス (CPU / CUDA) の判定。

`whisper_manager.py` から呼ばれる部品。pip で入れた CUDA ライブラリの
探索を含む、Windows + NVIDIA GPU 環境まわりの面倒をここに閉じ込める。
"""

from __future__ import annotations

import os

from wsptoolkit.lib.settings import IS_WINDOWS, get_logger

logger = get_logger(__name__)


def _add_nvidia_dll_dirs() -> None:
    """pip で入れた CUDA ライブラリの DLL を検索パスに追加する。

    nvidia-cublas-cu12 / nvidia-cudnn-cu12 の DLL は
    site-packages/nvidia/*/bin に入るが、Windows ではそこが PATH に
    載らないため、そのままだと CUDA ライブラリが見つからない。
    Windows 以外では何もしない。

    Returns:
        None
    """
    if os.name != "nt":
        return
    try:
        import nvidia
    except ImportError:
        return
    base = os.path.dirname(nvidia.__file__)
    for sub in ("cublas", "cudnn", "cuda_runtime"):
        directory = os.path.join(base, sub, "bin")
        if os.path.isdir(directory):
            try:
                os.add_dll_directory(directory)
            except (AttributeError, OSError):
                pass
            os.environ["PATH"] = (
                directory + os.pathsep + os.environ.get("PATH", "")
            )


def _cuda_libraries_loadable() -> bool:
    """CUDA 実行に必要な DLL が実際にロードできるか確かめる。

    厳密に判定するのは Windows のみ。他の OS では判定手段が異なるため
    常に True を返し、呼び出し側の CUDA デバイス数の判定に任せる。

    Returns:
        bool: cublas64_12.dll と cudnn64_9.dll の両方をロードできれば
            True。Windows 以外は常に True。
    """
    if os.name != "nt":
        return True
    import ctypes

    for dll in ("cublas64_12.dll", "cudnn64_9.dll"):
        try:
            ctypes.WinDLL(dll)
        except OSError:
            return False
    return True


def pick_device(
    requested: str = "auto", compute_type: str | None = None
) -> tuple[str, str]:
    """使用デバイスと計算精度を決める。

    requested が "auto" のときは、CUDA デバイスがあり、かつ CUDA/cuDNN の
    DLL が実際にロードできる場合だけ cuda を選ぶ（ライブラリが無いのに
    cuda を選ぶと推論の途中で "Library cublas64_12.dll is not found" に
    なるため）。"cuda" を明示したのにライブラリが無い場合は警告を出すが、
    指定はそのまま尊重する。

    Args:
        requested: "auto" / "cpu" / "cuda" のいずれか。
        compute_type: 計算精度 (int8, int8_float16, float16, float32)。
            None なら cuda→float16 / cpu→int8 を自動で選ぶ。

    Returns:
        tuple[str, str]: (デバイス名, 計算精度) の組。
    """
    _add_nvidia_dll_dirs()

    device = requested
    if device == "auto":
        device = "cpu"
        try:
            import ctranslate2

            if (
                ctranslate2.get_cuda_device_count() > 0
                and _cuda_libraries_loadable()
            ):
                device = "cuda"
        except Exception:  # ctranslate2 が CUDA 無しでビルドされている等
            device = "cpu"
    elif device == "cuda" and not _cuda_libraries_loadable():
        hint = (
            "Run `scripts\\win\\setup_venv.bat gpu` or specify --device cpu."
            if IS_WINDOWS
            else "CUDA is unavailable on this OS. Specify --device cpu."
        )
        logger.warning("CUDA/cuDNN libraries were not found. %s", hint)

    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type
