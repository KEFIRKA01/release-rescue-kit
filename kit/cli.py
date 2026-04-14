from __future__ import annotations

import argparse
import json
from pathlib import Path

from .checks import build_release_report, load_targets, run_targets, smoke_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Release Rescue Kit demo CLI")
    parser.add_argument("--targets", help="Path to a JSON file with target definitions")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.targets:
        results = run_targets(load_targets(Path(args.targets)))
    else:
        results = smoke_catalog()

    report = build_release_report(results)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
