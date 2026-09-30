"""連番の画像から一部を選び、作業用ディレクトリにシンボリックリンクを張る。

batch_rgb2x.py は入力ディレクトリ内の画像をすべて処理するので、間引きや分割は
このスクリプトで先に済ませ、その出力ディレクトリを batch_rgb2x.py に渡す。
リンクなので元の画像は複製されず、何が選ばれたかは ls で確認できる。
"""

import argparse
import re
from pathlib import Path

SUFFIXES = (".png", ".jpg", ".jpeg", ".exr")
SEQUENCE = re.compile(r"(\d+)(?:\.(\d+))?$")


def collect(input_dir):
    """画像を (パス, 連番) の組で集め、連番の昇順に並べる。

    連番は小数でもよい。小数部の桁数をディレクトリ全体の最大に揃えたうえで整数に
    直すので、1234567890.123456 のような名前ならマイクロ秒単位の整数として扱われ、
    桁が揃っていない名前が混ざっても順序は壊れない。
    """
    raw = []
    for path in input_dir.iterdir():
        if path.suffix.lower() not in SUFFIXES:
            continue
        match = SEQUENCE.search(path.stem)
        if match is None:
            raise SystemExit(f"ファイル名の末尾に連番がない: {path.name}")
        raw.append((path, match.group(1), match.group(2) or ""))
    if not raw:
        raise SystemExit(f"no images under {input_dir}")

    width = max(len(fraction) for _, _, fraction in raw)
    entries = [
        (path, int(integer) * 10**width + int(fraction.ljust(width, "0") or "0"))
        for path, integer, fraction in raw
    ]
    entries.sort(key=lambda entry: entry[1])
    return entries


def pick_truncated(entries, digits):
    """連番の下 digits 桁を切り捨ててまとめ、各グループの最小番号を選ぶ。

    整数の連番なら digits=2 で 100 番ごとに 1 枚。小数の連番では小数部の桁も
    数えるので、小数部が 6 桁なら digits=6 で整数部が変わるたびに 1 枚になる。
    番号が飛んでいてもグループ内の最小が選ばれる。
    """
    step = 10**digits
    groups = {}
    for path, number in entries:
        key = number // step
        if key not in groups or number < groups[key][1]:
            groups[key] = (path, number)
    return [groups[key][0] for key in sorted(groups)]


def pick_every(entries, step, index):
    """連番順に step 枚ごとに 1 枚を選ぶ。index は数え始めの位置（0 始まり）。

    連番の値ではなく枚数で数えるので、番号が等間隔でなくても枚数は step 分の 1 になる。
    """
    if index >= step:
        raise SystemExit(f"--index {index} は --every {step} 未満にする。")
    return [path for path, _ in entries[index::step]]


def link_into(selected, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    # 前回の選別結果は消す。実体のファイルがあるディレクトリは出力先として扱わない。
    for entry in output_dir.iterdir():
        if entry.is_symlink():
            entry.unlink()
        else:
            raise SystemExit(
                f"{output_dir} に実体のファイルがある: {entry.name}。"
                "選別結果の置き場所には空のディレクトリを使う。"
            )
    for path in selected:
        (output_dir / path.name).symlink_to(path.resolve())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--truncate",
        type=int,
        metavar="DIGITS",
        help="連番の下 DIGITS 桁を切り捨て、各グループの先頭だけを選ぶ"
        "（小数の連番では小数部の桁も数える）",
    )
    mode.add_argument(
        "--every",
        type=int,
        metavar="N",
        help="連番順に N 枚ごとに 1 枚を選ぶ",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=0,
        help="--every と併用し、数え始めの位置を指定する。0 始まり。",
    )
    args = parser.parse_args()

    entries = collect(args.input)
    if args.truncate is not None:
        selected = pick_truncated(entries, args.truncate)
    else:
        selected = pick_every(entries, args.every, args.index)

    link_into(selected, args.output)
    print(f"{len(selected)}/{len(entries)} 枚を {args.output} に link した")


if __name__ == "__main__":
    main()
