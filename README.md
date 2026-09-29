# Nix で rgbx デモを起動する

Nix および対応する NVIDIA GPU を備えた x86_64 Linux PC では、次のコマンドで RGB→X デモを起動できます。

```sh
nix run github:YOUR_USER/YOUR_REPOSITORY
```

端末に表示される Gradio のローカル URL をブラウザで開いてください。初回起動時にはモデルの重みがダウンロードされます。モデルファイルや RGB→X デモで保存した画像は、`${XDG_DATA_HOME:-$HOME/.local/share}/rgbx/rgb2x/` に保存されます。

なお、本環境は NixOS の NVIDIA ドライバのパスを使用しているため、他の Linux ディストリビューションではドライバの設定変更が必要になる場合があります。
