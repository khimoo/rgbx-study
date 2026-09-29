# 必要な環境

- x86_64 の WSL 2 と、WSL 内にインストールした Nix（flakes を有効にする）
- NVIDIA GPU と、Windows 側にインストールした WSL 対応の NVIDIA ドライバ

WSL 内に Linux 用の NVIDIA ドライバや CUDA Toolkit を追加する必要はありません。

# 実行方法

WSL の端末で実行します。

```sh
nix run github:khimoo/rgbx-study
```

端末に表示される Gradio のローカル URL を Windows のブラウザで開いてください。
初回起動時にはモデルの重みがダウンロードされます。

モデルファイルや RGB→X デモで保存した画像は、`${XDG_DATA_HOME:-$HOME/.local/share}/rgbx/rgb2x/` に保存されます。
