@echo off
setlocal

rem ============================================================
rem  Whisper サンプル用の Python 仮想環境 (.venv) を作成する
rem
rem   使い方:
rem     setup_venv.bat        ... CPU 版をインストール
rem     setup_venv.bat gpu    ... GPU 実行用の CUDA ライブラリも追加
rem
rem  フォルダ構成:
rem     python\wsptoolkit\cli\ ... コマンドラインの入口
rem     python\wsptoolkit\lib\ ... ライブラリ
rem     input\    ... 入力 (audio: 音声 / lyrics: 歌詞)
rem     output\   ... 書き出し結果
rem
rem  Python のバージョンは PYVER (= .python-version) に固定しています。
rem  変更するときは両方を書き換えてください。
rem
rem  ※ このファイルは Shift_JIS(CP932) + CRLF で保存すること
rem ============================================================

rem scripts\win\ から見て 2 階層上がリポジトリルート
cd /d "%~dp0..\.."

set "VENV_DIR=.venv"
set "PYVER=3.13"
set "PYEXE="

rem --- Python %PYVER% を探す (py ランチャー優先) ---
rem pyenv-win などの .bat シムを呼んでも制御が戻るよう call を付けている
call py -%PYVER% --version >nul 2>nul && set "PYEXE=py -%PYVER%"
if not defined PYEXE (
    rem py ランチャーが無い環境では、PATH の python が %PYVER% かどうかを見る
    call python -c "import sys;v=sys.version_info;raise SystemExit(0 if str(v[0])+'.'+str(v[1])=='%PYVER%' else 1)" >nul 2>nul && set "PYEXE=python"
)
if not defined PYEXE (
    echo [ERROR] Python %PYVER% が見つかりません。
    echo         このプロジェクトは Python %PYVER% に固定しています。
    echo         https://www.python.org/downloads/ から %PYVER% 系をインストールし、
    echo         インストーラの "Add python.exe to PATH" にチェックを入れてください。
    echo.
    echo         別のバージョンを使う場合は、setup_venv.bat の PYVER と
    echo         .python-version の両方を書き換えてください。
    goto :fail
)

echo [1/4] Python のバージョン確認 (%PYVER% に固定)
call %PYEXE% --version || goto :fail

if exist "%VENV_DIR%\Scripts\python.exe" (
    "%VENV_DIR%\Scripts\python.exe" -c "import sys;v=sys.version_info;raise SystemExit(0 if str(v[0])+'.'+str(v[1])=='%PYVER%' else 1)" >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] 既存の %VENV_DIR% は Python %PYVER% ではありません。
        call "%VENV_DIR%\Scripts\python.exe" --version
        echo         %VENV_DIR% フォルダを削除してから再実行してください。
        goto :fail
    )
    echo [2/4] 既存の仮想環境を使用します: %VENV_DIR%
) else (
    echo [2/4] 仮想環境を作成します: %VENV_DIR%
    call %PYEXE% -m venv "%VENV_DIR%" || goto :fail
)

set "VPY=%VENV_DIR%\Scripts\python.exe"

echo [3/4] pip を更新します
"%VPY%" -m pip install --upgrade pip || goto :fail

echo [4/4] 依存パッケージをインストールします
"%VPY%" -m pip install -r requirements.txt || goto :fail

if /i "%~1"=="gpu" (
    echo [extra] GPU 実行用の CUDA/cuDNN ライブラリをインストールします
    "%VPY%" -m pip install "nvidia-cublas-cu12" "nvidia-cudnn-cu12==9.*" || goto :fail
)

echo.
echo ============================================================
echo  セットアップ完了
echo.
echo   1) 仮想環境を有効化:  .venv\Scripts\activate
echo   2) Module path:       set PYTHONPATH=%CD%\python
echo   3) 文字起こし:        python -m wsptoolkit.cli.transcribe input\audio\sample.wav
echo   4) 単語単位の時間:    python -m wsptoolkit.cli.word_timestamps input\audio\sample.wav
echo   5) 歌詞との突き合わせ:  python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt
echo.
echo  初回実行時に Whisper モデルが自動ダウンロードされます
echo  (small で約 0.5GB / %USERPROFILE%\.cache\huggingface に保存)
echo ============================================================
echo.
pause
exit /b 0

:fail
echo.
echo [ERROR] セットアップに失敗しました。上のメッセージを確認してください。
echo.
pause
exit /b 1
