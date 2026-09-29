{
  description = "Pinned Nix environment for zheng95z/rgbx (RGB<->X, SIGGRAPH 2024)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    rgbx = {
      url = "github:zheng95z/rgbx/977e0df27d369d3e68900399f59a42b0156d4440";
      flake = false;
    };
  };

  outputs =
    {
      nixpkgs,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
      rgbx,
      ...
    }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (nixpkgs) lib;

      # アップストリームの environment.yml では python=3.9 が指定されているが、
      # nixpkgs ではサポート終了に伴い python39 および 3.10 が削除されている。
      # 利用可能な最も古いバージョンは 3.11 であり、uv.lock 内のすべての wheel にも
      # cp311 向けビルドが存在する。
      python = pkgs.python311;

      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

      # PyPI の wheel を優先する。conda 環境が pytorch-cuda 経由で導入する
      # CUDA 12.1 ランタイムが含まれており、torch のソースビルドも回避できる。
      pyprojectOverlay = workspace.mkPyprojectOverlay { sourcePreference = "wheel"; };

      # wheel の NEEDED エントリから autoPatchelf が推測できないネイティブライブラリについて、
      # パッケージ名ごとに明示的に指定する。
      extraNativeInputs = {
        opencv-python = [
          pkgs.libGL
          pkgs.glib
        ];
      };

      # uv2nix は wheel に autoPatchelfHook を適用する。各 wheel には libstdc++ と zlib も
      # 必要であり、torch および nvidia の wheel は実行時にホスト環境のドライバから
      # libcuda.so を読み込む。
      wheelFixups =
        _final: prev:
        let
          isWheel = drv: (drv.passthru.format or "") == "wheel";
          fixup =
            name: drv:
            drv.overrideAttrs (old: {
              buildInputs =
                (old.buildInputs or [ ])
                ++ [
                  pkgs.stdenv.cc.cc.lib
                  pkgs.zlib
                ]
                ++ (extraNativeInputs.${name} or [ ]);
              appendRunpaths = [ "${pkgs.addDriverRunpath.driverLink}/lib" ];
              autoPatchelfIgnoreMissingDeps = [ "*" ];
            });
        in
        lib.mapAttrs (name: drv: if isWheel drv then fixup name drv else drv) prev;

      pythonSet =
        (pkgs.callPackage pyproject-nix.build.packages { inherit python; }).overrideScope
          (lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            pyprojectOverlay
            wheelFixups
          ]);

      venv = pythonSet.mkVirtualEnv "rgbx-env" workspace.deps.default;

      # デモスクリプトは同じディレクトリ内にモデルの重みを保存し、RGB→X では
      # 画像も保存する仕様になっている。そのため、保存先をユーザーが書き込み可能な
      # ディレクトリへ変更する。
      demoSource = pkgs.runCommand "rgbx-demo-source" { } ''
        cp -r ${rgbx}/rgb2x "$out"
        chmod -R u+w "$out"
        substituteInPlace "$out/gradio_demo_rgb2x.py" \
          --replace-fail \
            'current_directory = os.path.dirname(os.path.abspath(__file__))' \
            'current_directory = os.environ["RGBX_DATA_DIR"]'
      '';
    in
    {
      apps.${system}.default = {
        type = "app";
        meta.description = "Launch the RGB→X Gradio demo";
        program = "${pkgs.writeShellScript "rgbx-rgb2x" ''
          set -eu
          # nvidia-*-cu12 の wheel は共有ライブラリを site-packages/nvidia/*/lib に配置し、
          # 実行時に dlopen で読み込む。そのため、これらのディレクトリとホストのドライバを
          # ライブラリ検索パスに追加する。
          libdirs=""
          for d in ${venv}/lib/python*/site-packages/nvidia/*/lib; do
            [ -d "$d" ] && libdirs="$libdirs''${libdirs:+:}$d"
          done
          libdirs="$libdirs''${libdirs:+:}${pkgs.addDriverRunpath.driverLink}/lib"
          export LD_LIBRARY_PATH="$libdirs''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
          data_home="''${XDG_DATA_HOME:-$HOME/.local/share}"
          export RGBX_DATA_DIR="$data_home/rgbx/rgb2x"
          ${pkgs.coreutils}/bin/mkdir -p "$RGBX_DATA_DIR"
          exec ${venv}/bin/python ${demoSource}/gradio_demo_rgb2x.py
        ''}";
      };
    };
}
