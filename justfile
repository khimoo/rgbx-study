default:
    @just --list

# Gradio デモを起動する
demo:
    nix run .#default

# ディレクトリ内の画像をまとめて処理する（既定は albedo のみ）
#   just batch 入力 出力 [--aov albedo normal --steps 20 ...]
batch input output *args:
    nix run .#batch -- --input {{ input }} --output {{ output }} {{ args }}

# 連番の下 digits 桁を切り捨て、各グループの先頭だけを work に link する
#   just thin 入力 work 2   -> 整数の連番なら 100 番ごとに 1 枚
#   just thin 入力 work 6   -> 1234567890.123456 形式なら整数部が変わるたびに 1 枚
thin input work digits:
    nix run .#select -- --input {{ input }} --output {{ work }} --truncate {{ digits }}

# 連番順に step 枚ごとに 1 枚を work に link する
#   just every 入力 work 25     -> 25 枚に 1 枚
#   just every 入力 work 25 3   -> 4 枚目から数え始める
every input work step index="0":
    nix run .#select -- --input {{ input }} --output {{ work }} --every {{ step }} --index {{ index }}

# 間引いてから処理する
#   just thin-batch 入力 work 出力 2 [--steps 20 ...]
thin-batch input work output digits *args:
    @just thin {{ input }} {{ work }} {{ digits }}
    @just batch {{ work }} {{ output }} {{ args }}

# step 枚ごとに 1 枚だけ処理する
#   just every-batch 入力 work 出力 25 [--steps 20 ...]
every-batch input work output step *args:
    @just every {{ input }} {{ work }} {{ step }}
    @just batch {{ work }} {{ output }} {{ args }}
