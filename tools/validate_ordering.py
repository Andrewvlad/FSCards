#!/usr/bin/env python3
"""Validate the shipped diagram sets against the fixed pool-ordering invariant - a cross-check
no single extraction pipeline's missing/extra set-diff can make, applied across ALL of them
(Axis, FAI, USPA, Rhythm, CF, ...). Every dive-pool set, whatever its source PDF, lists its
randoms and blocks in one consistent order:

  - randoms run contiguously from A - FS disciplines skip I (never used, easily misread), CF
    disciplines (`*-cf`) DO use I, so the expected letter run forks on the family
  - blocks / numbered formations run contiguously from 1

A gap, a stray letter, or a non-contiguous run means a mis-cut key or a reordered edition.
This validates the key SET, not physical order, so the CISM split-out M never trips it, and
CISM's extra R needs no special case - in the skip-I alphabet R is simply the letter after Q,
so 4-way's A..R is contiguous on its own. CISM block sub-selection (non-contiguous) would warn,
but no CISM set ships - the shipped pools are always the full run.

Non-pool files are ignored: 8-way's `*_indoor` variants and `starting-formation*` reference
cards, and the `solo` base-figure pool (a single `fs`, not randoms/blocks). Scans the repo
(post-install in each extract workflow, so it sees exactly what the PR proposes - also standalone
for the manual FAI/CF re-cuts and ad-hoc audits). `validate_ordering.py` checks every set,
`validate_ordering.py 4-way 8-way` only the named disciplines. Warnings print as `[ordering]`
lines and never block - the extract PR is for eyeballing anyway."""
import glob, os, re, sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REPO = f"{ROOT}/assets/diagrams"
ALPHABET_NOI = "ABCDEFGHJKLMNOPQRSTUVWXYZ"   # FS random order, "I" never used
ALPHABET_I = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"    # CF random order, "I" used
IGNORE = re.compile(r"_indoor$|^starting-formation")   # legit non-pool cards
SKIP_DISCIPLINES = {"solo"}   # single base-figure master, not a random/block pool


def check(disc, keys):
    """Ordering violations for one set's key list (human-readable strings), with the
    pool-key count (non-pool cards filtered) for the caller's OK line."""
    pool = [k for k in keys if not IGNORE.search(k)]
    junk = [k for k in pool if not re.fullmatch(r"\d{1,2}|[A-Z]", k)]
    randoms = sorted(k for k in pool if re.fullmatch(r"[A-Z]", k))
    blocks = sorted((k for k in pool if k.isdigit()), key=int)
    cf = disc.endswith("-cf")
    warns = []
    if junk:
        warns.append(f"unexpected key(s) {sorted(junk)} - neither a single letter nor a number")
    if not cf and "I" in randoms:
        warns.append("'I' present in an FS pool - never used, likely a J/1 misread")
    seq = ALPHABET_I if cf else ALPHABET_NOI
    expect_r = list(seq[:len(randoms)])
    if randoms != expect_r:
        warns.append(f"randoms {randoms} not contiguous A.. ({'with' if cf else 'skip'} I), expected {expect_r}")
    expect_b = [str(i) for i in range(1, len(blocks) + 1)]
    if blocks != expect_b:
        warns.append(f"blocks {blocks} not contiguous 1..N, expected {expect_b}")
    return warns, len(pool)


def gather_repo(only=None):
    """`<disc>/<set>` -> (discipline, key list) for every shipped set, webp + svg."""
    sets = {}
    for setdir in sorted(glob.glob(f"{REPO}/*/*")):
        disc, setname = os.path.basename(os.path.dirname(setdir)), os.path.basename(setdir)
        if not os.path.isdir(setdir) or setname == "figures" or disc in SKIP_DISCIPLINES:
            continue
        if only and disc not in only:
            continue
        keys = [os.path.splitext(os.path.basename(f))[0]
                for f in glob.glob(f"{setdir}/*.webp") + glob.glob(f"{setdir}/*.svg")]
        if keys:
            sets[f"{disc}/{setname}"] = (disc, keys)
    return sets


def run(sets):
    """Print an OK/WARN line per set, return the total warning count."""
    total = 0
    for label in sorted(sets):
        disc, keys = sets[label]
        warns, npool = check(disc, keys)
        if warns:
            total += len(warns)
            for w in warns:
                print(f"[ordering] {label}: WARN {w}")
        else:
            print(f"[ordering] {label}: OK ({npool} keys)")
    print(f"[ordering] {total} warning(s) across {len(sets)} set(s)")
    return total


if __name__ == "__main__":
    run(gather_repo(set(sys.argv[1:]) or None))   # warnings print but never block (see module docstring)
