#!/usr/bin/env python3
"""Dispatch USPA extraction by changed source PDF, staging every set under /tmp/fsx_out for
install.py - the workflow's single entry point, twin of axis-extract/extract.py. argv =
changed source basenames (fs.pdf / collegiate.pdf); no args = both chapters. A chapter's
scripts run in order - any failure aborts (non-zero exit). Prints a 'recut-slug:' line naming
the cut chapters, which the workflow turns into the PR branch suffix."""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
# changed source PDF -> (scripts that cut its sets in order, branch slug)
CHAPTERS = {
    "fs.pdf":         (["driver_ch9.py"], "fs"),
    "collegiate.pdf": (["driver_ch7.py", "p16fix.py", "extract6.py --extract"], "collegiate"),
}

changed = [os.path.basename(a) for a in sys.argv[1:]] or list(CHAPTERS)
slugs = []
for pdf in changed:
    if pdf not in CHAPTERS:
        print(f"skip {pdf}: not an SCM source chapter", file=sys.stderr)
        continue
    scripts, slug = CHAPTERS[pdf]
    slugs.append(slug)
    for script in scripts:
        print(f"\n=== {script} ({pdf}) ===", flush=True)
        subprocess.run(["python3", *script.split()], cwd=HERE, check=True)
print("recut-slug:", " ".join(slugs) or "none")
