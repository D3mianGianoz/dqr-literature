#!/usr/bin/env python3
"""Regenerate the hand-crafted test PDFs used by the test_paths suite.

Uses pandoc (must be on PATH) to convert markdown → PDF. The source
markdown lives next to this file; the output PDFs are written to
the same directory so the tests can find them.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SPEC = {
    "test_abstract.md": """\
# Test Paper Title
Authors A. B. C.

## Abstract
This paper studies anomaly detection in streaming sensor data.
We propose a simple baseline and compare it against existing methods.
Our results show improvements over the state of the art.

## Introduction
Background and motivation for the study follow here.
""",
    "test_no_abstract.md": """\
# Test Paper No Abstract
Authors X. Y. Z.

Anomaly detection in streaming data is studied in this work.
We propose a simple baseline and compare it against existing methods.
Results show improvements over the state of the art.

Background and motivation follow here.
""",
}


def build(name: str, md: str) -> Path:
    mpath = HERE / name
    mpath.write_text(md, encoding="utf-8")
    out = mpath.with_suffix(".pdf")
    r = subprocess.run(
        ["pandoc", "-o", str(out), str(mpath)], capture_output=True, text=True
    )
    if r.returncode:
        sys.exit(f"pandoc failed for {name}:\n{r.stderr}")
    # Clean up: delete the markdown after PDF generation
    mpath.unlink()
    return out


if __name__ == "__main__":
    for name, content in SPEC.items():
        p = build(name, content)
        print("wrote", p)
