default:
    @just --list

# Gradio デモを起動する
demo:
    nix run .#default

# ディレクトリ内の画像をまとめて処理する
#   just batch 入力ディレクトリ 出力ディレクトリ [--steps 20 --seed 0 ...]
batch input output *args:
    nix run .#batch -- --input {{ input }} --output {{ output }} {{ args }}
