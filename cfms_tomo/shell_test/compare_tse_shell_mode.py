import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_tse(shell_mesh, cut_options, theta_yp, shell_thickness, use_cuda):
    env = os.environ.copy()
    env["TOMO_NO_SHOW"] = "1"
    env["TOMO_SHELL_MESH"] = "1" if shell_mesh else "0"
    env["TOMO_CUT_OPTIONS"] = cut_options
    env["TOMO_THETA_YP"] = str(theta_yp)
    env["TOMO_SHELL_THICKNESS"] = str(shell_thickness)
    env["TOMO_RENDER_SHELL_THICKNESS"] = "0"
    env["TOMO_USE_CUDA"] = "1" if use_cuda else "0"

    proc = subprocess.run(
        [sys.executable, "TSE_TomoSh2.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    return parse_mss_table(proc.stdout), proc.stdout


def parse_mss_table(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    rows = {}
    for i, line in enumerate(lines):
        if not line.endswith("_tomo_rotated"):
            continue
        if i + 4 >= len(lines):
            continue
        try:
            rows[line] = {
                "n_segment": int(float(lines[i + 1])),
                "length_average": float(lines[i + 2]),
                "length_stdev": float(lines[i + 3]),
                "Mss": float(lines[i + 4]),
            }
        except ValueError:
            continue
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Run TSE_TomoSh2.py with bShellMesh on/off and compare final Mss."
    )
    parser.add_argument("--cut-options", default="all")
    parser.add_argument("--theta-yp", type=int, default=90)
    parser.add_argument("--shell-thickness", type=float, default=0.0)
    parser.add_argument("--use-cuda", action="store_true")
    args = parser.parse_args()

    on_rows, _ = run_tse(
        True, args.cut_options, args.theta_yp, args.shell_thickness, args.use_cuda
    )
    off_rows, _ = run_tse(
        False, args.cut_options, args.theta_yp, args.shell_thickness, args.use_cuda
    )

    keys = sorted(set(on_rows) | set(off_rows))
    print(
        f"cut_options={args.cut_options} theta_YP={args.theta_yp} "
        f"shell_thickness={args.shell_thickness:g} use_cuda={args.use_cuda}"
    )
    print("name,shell_on,shell_off,ratio,on_minus_off")
    for key in keys:
        on = on_rows.get(key, {}).get("Mss", float("nan"))
        off = off_rows.get(key, {}).get("Mss", float("nan"))
        ratio = on / off if off else float("inf")
        print(f"{key},{on:.9f},{off:.9f},{ratio:.3f},{on - off:.9f}")


if __name__ == "__main__":
    main()
