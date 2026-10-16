"""Check the two local CSV inputs without requiring analysis dependencies."""
from pathlib import Path
import argparse
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "2026Data/Keep Data/sample_post_2022.csv": "74f2ed2878852f00618db3ae0b9f8c468a4f760e603dcb98c8a286a47919582c",
    "2026Data/Keep Data/sample_comment_2022.csv": "7a7a7e1f2462fc457ed7110266fbacbd2998f0f302f86eef7ca1202c9da53355",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-hashes", action="store_true", help="Verify the exact course input files recorded in DATA.md.")
    args = parser.parse_args()
    missing = [name for name in INPUTS if not (ROOT / name).is_file()]
    if missing:
        print("缺少本地输入文件：", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        print("请按 DATA.md 将两份课程CSV放入 2026Data/Keep Data/ 后重试。", file=sys.stderr)
        return 1
    for name, expected in INPUTS.items():
        if args.verify_hashes:
            actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            if actual != expected:
                print(f"校验值不符：{name}；请核对课程数据版本。", file=sys.stderr)
                return 1
        print(f"OK  {name}")
    print("输入检查通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
