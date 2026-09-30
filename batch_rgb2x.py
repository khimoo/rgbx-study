"""ディレクトリ内の画像に RGB→X を順に適用する。

Gradio デモ (gradio_demo_rgb2x.py) の callback と同じ前処理・同じ推論を行い、
結果を PNG として書き出す。パイプラインの読み込みは 1 回だけ。
"""

import argparse
import os
from pathlib import Path

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import torch
import torchvision
from diffusers import DDIMScheduler
from load_image import load_exr_image, load_ldr_image
from pipeline_rgb2x import StableDiffusionAOVMatEstPipeline

AOV_PROMPTS = {
    "albedo": "Albedo (diffuse basecolor)",
    "normal": "Camera-space Normal",
    "roughness": "Roughness",
    "metallic": "Metallicness",
    "irradiance": "Irradiance (diffuse lighting)",
}

SUFFIXES = (".png", ".jpg", ".jpeg", ".exr")


def load_photo(path):
    if path.suffix.lower() == ".exr":
        return load_exr_image(str(path), tonemapping=True, clamp=True).to("cuda")
    return load_ldr_image(str(path), from_srgb=True).to("cuda")


def fit_to_model(photo, max_side):
    """デモでcallback内で書かれてる処理と同じ処理です．"""
    old_height, old_width = photo.shape[1], photo.shape[2]
    ratio = old_height / old_width
    if old_height > old_width:
        new_height = max_side
        new_width = int(new_height / ratio)
    else:
        new_width = max_side
        new_height = int(new_width * ratio)
    new_height = new_height // 8 * 8
    new_width = new_width // 8 * 8
    resized = torchvision.transforms.Resize((new_height, new_width))(photo)
    return resized, (old_height, old_width), (new_height, new_width)


def build_pipeline():
    pipe = StableDiffusionAOVMatEstPipeline.from_pretrained(
        "zheng95z/rgb-to-x",
        torch_dtype=torch.float16,
        cache_dir=os.path.join(os.environ["RGBX_DATA_DIR"], "model_cache"),
    ).to("cuda")
    pipe.scheduler = DDIMScheduler.from_config(
        pipe.scheduler.config, rescale_betas_zero_snr=True, timestep_spacing="trailing"
    )
    pipe.set_progress_bar_config(disable=True)
    return pipe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="乱数のシードを固定できる．大量の画像の処理を途中からやりなおしたいときなど",
    )
    parser.add_argument("--max-side", type=int, default=1000)
    parser.add_argument(
        "--aov",
        nargs="+",
        choices=list(AOV_PROMPTS),
        default=["albedo"],
        help="生成する AOV。既定は albedo のみ。",
    )
    args = parser.parse_args()

    images = sorted(p for p in args.input.iterdir() if p.suffix.lower() in SUFFIXES)
    if not images:
        raise SystemExit(f"no images under {args.input}")
    args.output.mkdir(parents=True, exist_ok=True)

    pipe = build_pipeline()

    aov_offsets = {name: offset for offset, name in enumerate(AOV_PROMPTS)}

    for index, path in enumerate(images, 1):
        targets = {aov: args.output / f"{path.stem}_{aov}.png" for aov in args.aov}
        if all(target.exists() for target in targets.values()):
            print(f"[{index}/{len(images)}] skip {path.name}", flush=True)
            continue

        photo, old_size, new_size = fit_to_model(load_photo(path), args.max_side)
        for aov in args.aov:
            if targets[aov].exists():
                continue
            prompt = AOV_PROMPTS[aov]
            generator = None
            if args.seed is not None:
                generator = torch.Generator(device="cuda").manual_seed(
                    args.seed + aov_offsets[aov]
                )
            generated = pipe(
                prompt=prompt,
                photo=photo,
                num_inference_steps=args.steps,
                height=new_size[0],
                width=new_size[1],
                generator=generator,
                required_aovs=[aov],
            ).images[0][0]
            torchvision.transforms.Resize(old_size)(generated).save(targets[aov])
        print(f"[{index}/{len(images)}] {path.name}", flush=True)


if __name__ == "__main__":
    main()
