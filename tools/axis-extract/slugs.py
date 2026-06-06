"""Axis discipline -> source-PDF manifest and branch-slug derivation, kept stdlib-only.

The update-axis-sources watcher imports pdf_slug from here to name its PR branches
the same way the extract workflow does, without pulling extract.py's numpy/PIL/scipy
stack. extract.py re-imports JOBS/pdf_slug (install.py reads JOBS via that re-export).
"""
import os

# discipline -> [(pdf, restricted-key-set or None)]; None = source for every key
# not claimed by a restricted entry.
JOBS = {
    "4-way":        [("fs4.pdf", None)],
    "8-way":        [("fs8.pdf", None),
                     ("fs8_indoor.pdf", {"13_indoor", "17_indoor", "20_indoor", "starting-formation"})],
    "10-way-speed": [("fs10.pdf", None)],
    "16-way":       [("fs16.pdf", None)],
    "4-way-vfs":    [("vfs4.pdf", None)],
    "2-way-mfs":    [("mfs2.pdf", None)],
    "2-way":        [("fs2.pdf", None)],
    "2-way-vfs":    [("vfs2.pdf", None)],
    "2-way-cf":     [("cf2.pdf", None)],
    "4-way-cf":     [("cf4.pdf", None)],
}


def pdf_slug(pdf):
    """extract-axis-images branch-slug for a changed PDF: its discipline, plus the basename's
    distinguishing tail when the discipline has >1 source (8-way's fs8 vs
    fs8_indoor), so each source lands on its own branch. The source whose stem
    is the shared prefix (fs8) keeps the bare discipline name."""
    d = next((d for d, s in JOBS.items() if any(p == pdf for p, _ in s)), None)
    if d is None:
        return None
    stems = [p[:-4] for p, _ in JOBS[d]]
    if len(stems) < 2:
        return d
    tail = pdf[:-4][len(os.path.commonprefix(stems)):].strip("_-").replace("_", "-").lower()
    return f"{d}-{tail}" if tail else d
