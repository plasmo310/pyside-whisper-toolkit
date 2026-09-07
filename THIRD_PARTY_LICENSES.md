# Third-party Licenses

Whisper Toolkit is released under the MIT License (see [`LICENSE`](LICENSE)).
It depends on the following third-party software. None of it is redistributed in
this repository; each is installed with `pip` (or downloaded at first run).

| Name | License | Notes |
| --- | --- | --- |
| Python | Python Software Foundation License | Required to run this project. Not redistributed in this repository. |
| faster-whisper | MIT | Whisper inference. Bundles the Silero VAD model (MIT). |
| CTranslate2 | MIT | Whisper backend. Its wheel bundles Intel oneDNN / OpenMP (Apache-2.0) and NVIDIA cuDNN (proprietary EULA). |
| onnxruntime | MIT | Runs the Silero VAD model. |
| tokenizers | Apache-2.0 | Used via faster-whisper. |
| huggingface-hub | Apache-2.0 | Model download. |
| PyAV | BSD-3-Clause | Python code is BSD; the wheel bundles FFmpeg and codec libraries (LGPL-2.1+, and GPL-2.0+ when built with x264/x265). |
| NumPy | BSD-3-Clause | |
| PySide6 | LGPLv3 / GPLv3 / Commercial | Used under LGPLv3. GUI only. Not redistributed in this repository. |
| shiboken6 | LGPLv3 / GPLv3 / Commercial | Runtime for PySide6. Used under LGPLv3. Not redistributed in this repository. |
| Qt | LGPLv3 / GPLv3 / Commercial | Used via PySide6 under LGPLv3. Not redistributed in this repository. |
| Whisper models | MIT | Downloaded from Hugging Face at first run. Not redistributed in this repository. |
| PyInstaller | GPLv2-or-later with bootloader exception | Optional build tool. Generated binaries are not distributed in this repository. |

> When distributing a PyInstaller binary (`build_env/` → `release/`), the bundle
> embeds Qt, FFmpeg, and CTranslate2's native libraries. Include their license
> texts, keep the `--onedir` layout, prefer an LGPL-only FFmpeg build (drop
> x264/x265), and drop `cudnn64_9.dll` for CPU-only releases.
