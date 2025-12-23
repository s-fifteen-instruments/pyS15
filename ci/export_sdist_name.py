#!/usr/bin/env python3
# From: https://github.com/matplotlib/matplotlib/blob/main/ci/export_sdist_name.py
"""
Determine the name of the sdist and export to GitHub output named SDIST_NAME.

To run:
    $ python3 -m build --sdist
    $ ./ci/determine_sdist_name.py
"""
import os
import sys
from pathlib import Path

paths = [p.name for p in Path("dist").glob("*.tar.gz")]
if len(paths) != 1:
    sys.exit(f"Only a single sdist is supported, but found: {paths}")

print("Exporting:", paths[0])
with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"SDIST_NAME={paths[0]}\n")
