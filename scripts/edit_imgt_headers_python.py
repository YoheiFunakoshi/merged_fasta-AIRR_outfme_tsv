#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Alternative to edit_imgt_file.pl for IMGT FASTA header cleanup.

Note: record the exact transformation for reproducibility when sharing results.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Edit IMGT FASTA headers into IgBLAST-friendly deflines."
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing IMGT_IGHV/IGHD/IGHJ.fasta or IGHV/IGHD/IGHJ.fasta.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write *.imgt.fasta files.",
    )
    return parser.parse_args()


def find_input(input_dir: Path, stem: str) -> Path | None:
    candidates = [f"IMGT_{stem}.fasta", f"{stem}.fasta"]
    for name in candidates:
        path = input_dir / name
        if path.exists():
            return path
    return None


def normalize_header(header: str) -> str:
    parts = header.split("|")
    gene = parts[1].strip() if len(parts) >= 2 and parts[1].strip() else header.strip()
    return gene


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    stems = ["IGHV", "IGHD", "IGHJ"]
    for stem in stems:
        input_path = find_input(input_dir, stem)
        if input_path is None:
            print(
                f"Missing input for {stem}. Expected IMGT_{stem}.fasta or {stem}.fasta in {input_dir}",
                file=sys.stderr,
            )
            return 1
        output_path = output_dir / f"{input_path.stem}.imgt.fasta"

        with input_path.open("r", encoding="utf-8", errors="ignore") as fin, output_path.open(
            "w", encoding="ascii", errors="ignore", newline=""
        ) as fout:
            for line in fin:
                if line.startswith(">"):
                    gene = normalize_header(line[1:].strip())
                    fout.write(f">{gene}\n")
                else:
                    seq = line.strip().upper()
                    if seq:
                        fout.write(seq + "\n")

        print(f"Wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
