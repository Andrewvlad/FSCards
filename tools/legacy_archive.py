#!/usr/bin/env python3
"""Shared legacy-archiving helpers for the source-PDF watchers and the install.py installers.

Edition label = the fetch date. The day a watcher pulls a PDF from the source site is its
revision date (the watchers run at month end, so the fetch month is the revision month), so the
archive is dated by `date.today()` - no PDF CreationDate is read, that stamp is the producer's
export day, not the revision. Two uses:

  PDF archive (watchers): every fetched PDF is copied into assets/sources/<src>/legacy/<year>/ as
  the working source is replaced, so the archive keeps one copy per edition including the current
  one. The year's first edition sits flat at <year>/ - a later same-year edition (different bytes)
  lands in a fetch-month subdir <year>/<Month>/ beside it, so no edition is ever overwritten.

  Deprecated images (install.py): when a re-cut replaces or drops a diagram, the OLD diagram is
  copied to assets/sources/<src>/legacy/deprecated/<disc>/<key>_dep-<year>.webp, labeled by the
  re-cut year (the fetch year of the edition that replaced it). Only the named diagram is kept -
  the figures/ sibling is a name-erased derivation, re-creatable from it - matching legacy.py's.

CLI (for the watcher bash):
  python3 tools/legacy_archive.py archive-pdf <pdf> <legacy-dir>  -> places a dated copy and
       prints the repo path it wrote (relative to the repo root)
"""
import filecmp, os, shutil, sys
from datetime import date

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_MONTHS = ["", "January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"]


def edition_year():
    """Current year ('YYYY') - the fetch/re-cut day is the edition's revision date."""
    return str(date.today().year)


def _month_name():
    """Current English month name, for nesting a same-year re-revision."""
    return _MONTHS[date.today().month]


def _unique_dest(dest, src):
    """dest, or a `-N` suffixed sibling, that does not collide with a DIFFERENT existing file.
    A same-year same-month re-revision resolves to one path - disambiguate by a counter rather
    than overwrite (the no-overwrite invariant). Returns dest unchanged when it is absent or
    already holds identical bytes (no-op-safe)."""
    if not os.path.exists(dest) or filecmp.cmp(src, dest, shallow=False):
        return dest
    stem, ext = os.path.splitext(dest)
    n = 2
    while os.path.exists(f"{stem}-{n}{ext}") and not filecmp.cmp(src, f"{stem}-{n}{ext}", shallow=False):
        n += 1
    return f"{stem}-{n}{ext}"


def archive_pdf(pdf_path, legacy_dir):
    """Copy pdf_path into legacy_dir/<year>/, one copy per edition, dated by the fetch day (today).
    The year's first edition sits flat at <year>/ - a later same-year edition (different bytes than
    that flat copy) lands in <year>/<fetch-month>/ beside it, so no edition is ever overwritten.
    Returns the written path. No-op-safe: re-archiving identical bytes keeps the existing copy."""
    base = os.path.basename(pdf_path)
    year_dir = os.path.join(legacy_dir, edition_year())
    flat = os.path.join(year_dir, base)
    if not os.path.exists(flat) or filecmp.cmp(pdf_path, flat, shallow=False):
        dest_dir = year_dir
    else:                                          # a different edition already sits flat this year
        dest_dir = os.path.join(year_dir, _month_name())
    os.makedirs(dest_dir, exist_ok=True)
    dest = _unique_dest(os.path.join(dest_dir, base), pdf_path)   # same-month re-revision: -N, never overwrite
    shutil.copyfile(pdf_path, dest)
    return dest


def archive_image(dep_root, disc, rel, old_path):
    """Copy old_path (a diagram, rel like 'X.webp') to dep_root/<disc>/<key>_dep-<year>.webp, dated
    by the re-cut day (today). Returns the dep-root-relative path written. Diagrams only, not figures."""
    stem, ext = os.path.splitext(rel)
    dest = os.path.join(dep_root, disc, f"{stem}_dep-{edition_year()}{ext}")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    dest = _unique_dest(dest, old_path)   # same-year re-cut of one key: -N, never overwrite the prior dep
    shutil.copyfile(old_path, dest)
    return os.path.relpath(dest, dep_root)


def orphan_guard(staged_rels, repo_rels, min_ratio=0.5, guard_categories=True):
    """Split repo orphans (installed files with no staged counterpart) into (deletable, refused).
    Refuses ALL orphans when staging covers under min_ratio of the installed set (a botched run),
    and - when guard_categories - refuses orphans of a key category (random letters vs numbered
    blocks) the staging produced NONE of while the repo has some: a contiguous A..Q / 1..N pool
    never loses a whole category at once, and validate_ordering passes vacuously on an emptied
    category, so a mislocated randoms/blocks page would otherwise auto-delete every valid card of
    it. guard_categories=False for non-contiguous subsets (the FAI indoor-variant merge), where an
    empty staging is a legitimate state."""
    orphans = sorted(repo_rels - staged_rels)
    if not orphans or len(staged_rels) < min_ratio * len(repo_rels):
        return [], orphans
    if not guard_categories:
        return orphans, []
    is_block = lambda rel: os.path.splitext(os.path.basename(rel))[0][:1].isdigit()
    staged_blocks = any(is_block(r) for r in staged_rels)
    staged_randoms = any(not is_block(r) for r in staged_rels)
    deletable, refused = [], []
    for rel in orphans:
        wipes_category = (is_block(rel) and not staged_blocks) or (not is_block(rel) and not staged_randoms)
        (refused if wipes_category else deletable).append(rel)
    return deletable, refused


def main(argv):
    if len(argv) >= 3 and argv[0] == "archive-pdf":
        print(os.path.relpath(archive_pdf(argv[1], argv[2]), ROOT))
        return 0
    print("usage: legacy_archive.py archive-pdf <pdf> <legacy-dir>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
