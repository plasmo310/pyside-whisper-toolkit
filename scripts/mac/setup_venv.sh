#!/usr/bin/env bash
# ============================================================
#  Whisper サンプル用の Python 仮想環境 (.venv) を作成する (macOS / Linux)
#
#   使い方:
#     ./scripts/mac/setup_venv.sh
#
#  フォルダ構成:
#     python/wsptoolkit/  ... GUI・CLI・処理本体
#     input/    ... 入力 (audio: 音声 / lyrics: 歌詞)
#     output/   ... 書き出し結果
#
#  Python のバージョンは PYVER (= .python-version) に固定しています。
#  変更するときは両方を書き換えてください。
#
#  ※ Windows は scripts/win/setup_venv.bat を使ってください
# ============================================================
set -euo pipefail

# Windows の venv は .venv/Scripts/ を作るためこのスクリプトとは構成が合わない。
# Git Bash や MSYS から誤って実行されたときに中途半端に走らせないよう、先に弾く。
case "$(uname -s)" in
    Darwin | Linux) ;;
    *)
        echo "[ERROR] このスクリプトは macOS / Linux 用です。"
        echo "        Windows では scripts\\win\\setup_venv.bat を使ってください。"
        exit 1
        ;;
esac

# scripts/mac/ から見て 2 階層上がリポジトリルート
# (`sh setup_venv.sh` のように bash 以外から起動されると BASH_SOURCE が未定義なので $0 で代替)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/../.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR=".venv"
PYVER="3.13"
PYEXE=""

fail() {
    echo ""
    echo "[ERROR] セットアップに失敗しました。上のメッセージを確認してください。"
    exit 1
}

# --- Python $PYVER を探す ---
# pythonX.Y という名前のコマンドを優先し、無ければ python3 / python の実バージョンを見る
is_pyver() {
    "$1" -c "import sys;v=sys.version_info;raise SystemExit(0 if f'{v[0]}.{v[1]}' == '$PYVER' else 1)" \
        >/dev/null 2>&1
}

for candidate in "python$PYVER" python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && is_pyver "$candidate"; then
        PYEXE="$candidate"
        break
    fi
done

if [ -z "$PYEXE" ]; then
    echo "[ERROR] Python $PYVER が見つかりません。"
    echo "        このプロジェクトは Python $PYVER に固定しています。"
    echo ""
    echo "        Homebrew:  brew install python@$PYVER"
    echo "        pyenv:     pyenv install $PYVER && pyenv local $PYVER"
    echo "        公式:      https://www.python.org/downloads/"
    echo ""
    echo "        別のバージョンを使う場合は、このスクリプトの PYVER と"
    echo "        .python-version の両方を書き換えてください。"
    fail
fi

echo "[1/4] Python のバージョン確認 ($PYVER に固定)"
"$PYEXE" --version || fail

VPY="$VENV_DIR/bin/python"

if [ -x "$VPY" ]; then
    if ! is_pyver "$VPY"; then
        echo "[ERROR] 既存の $VENV_DIR は Python $PYVER ではありません。"
        "$VPY" --version || true
        echo "        $VENV_DIR ディレクトリを削除してから再実行してください。"
        fail
    fi
    echo "[2/4] 既存の仮想環境を使用します: $VENV_DIR"
else
    echo "[2/4] 仮想環境を作成します: $VENV_DIR"
    "$PYEXE" -m venv "$VENV_DIR" || fail
fi

echo "[3/4] pip を更新します"
"$VPY" -m pip install --upgrade pip || fail

echo "[4/4] 依存パッケージをインストールします"
"$VPY" -m pip install -r requirements.txt || fail

# macOS には NVIDIA GPU / CUDA が無いため、GPU オプションは用意していない。
# CTranslate2 は Apple Silicon でも CPU (Accelerate) で動く。
if [ "$(uname -s)" = "Darwin" ]; then
    echo ""
    echo "[info] macOS では CUDA を使えないため CPU で実行されます。"
    echo "       Apple Silicon なら --compute-type int8 のまま十分実用的です。"
fi

cat <<EOS

============================================================
 セットアップ完了

 1) 仮想環境を有効化:  source .venv/bin/activate
  2) モジュール検索パス:  export PYTHONPATH="$PWD/python"
  3) 文字起こし:        python -m wsptoolkit.cli.transcribe input/audio/sample.wav
  4) 単語単位の時間:    python -m wsptoolkit.cli.word_timestamps input/audio/sample.wav
  5) 歌詞との突き合わせ: python -m wsptoolkit.cli.sync_lyrics sample.words.json --lyrics sample.txt

 初回実行時に Whisper モデルが自動ダウンロードされます
 (small で約 0.5GB / ~/.cache/huggingface に保存)
============================================================
EOS
