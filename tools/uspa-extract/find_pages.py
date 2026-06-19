#!/usr/bin/env python3
"""Locate each discipline's appendix diagram pages in an SCM chapter PDF by READING the
running headers, not by hardcoded page numbers. Front matter grows and shrinks between
editions (FS Ch.9 has run 34-41 pages, Collegiate Ch.7 19-26), so a fixed page map breaks
on the next revision. Every diagram page instead carries a header naming its discipline and
section - "Appendix C: FS 4-Way Block Sequences", "Appendix F: VFS 2-Way Random Formations"
- and that text is stable across every edition 2015-2026 (only the CASE and the appendix
LETTER drift: a symbols appendix inserted in 2026 pushed MFS from L/M to M/N, and Collegiate
swapped its 4-way/MFS pages for 6-way-speed/VFS-2 between 2017 and 2026). So we key on
style+width+section, never the letter or page number.

Used by the drivers: each asks for its (style, width) and gets back the randoms page(s) and
block page(s) for whichever edition is loaded. A discipline absent from an edition (no VFS-2
in 2015) simply returns empty - you can't cut what isn't printed."""
import functools, re, subprocess

# A header is an appendix diagram title iff it carries the literal "Appendix" - that one word
# separates a real diagram page from a rules-body mention ("...2-way Vertical Formation
# Skydiving...") and, via the dot-leader test, from the table of contents.
WAY = re.compile(r'(?<![A-Za-z])(VFS|MFS|FS)?\s*(\d+)\s*-?\s*way', re.I)
LETTER = re.compile(r'appendix\s+([A-Z])\b', re.I)

def header_lines(pdf):
    """Top text region of each page, 1-based: page n -> list of its first non-empty lines."""
    txt = subprocess.run(["pdftotext", "-layout", pdf, "-"], capture_output=True, text=True, check=True).stdout
    return {i: [l.strip() for l in pg.splitlines() if l.strip()][:6]
            for i, pg in enumerate(txt.split("\f"), 1)}

def parse_header(line):
    """(letter, style, width, section) for an appendix diagram header, else None.
    section: 'random' | 'block' | 'single' (a plain "...Formations" page - 10-way, 6-way
    speed, VFS-2 blocks). style is None when the header omits it (Collegiate FS 2-way is
    bare "2-Way", and 2026 drops the style word on '(continued)' pages)."""
    low = line.lower()
    if 'appendix' not in low or '..' in low:   # '..' = a table-of-contents dot leader
        return None
    way = WAY.search(line)
    if not way:                                # "Appendix B: Definition of Symbols" - no pool
        return None
    let = LETTER.search(line)
    style = (way.group(1) or '').upper() or None
    section = 'random' if 'random' in low else 'block' if 'block' in low else 'single'
    return (let.group(1).upper() if let else None, style, int(way.group(2)), section)

@functools.lru_cache(maxsize=None)   # drivers call pages_for once per discipline against one PDF
def locate(pdf):
    """page -> (style, width, section) for every appendix diagram page, with the style
    forward-filled along each appendix's letter so a style-less '(continued)' page inherits
    the style of its appendix's first page."""
    raw = {}
    for n, lines in header_lines(pdf).items():
        for l in lines:
            h = parse_header(l)
            if h:
                raw[n] = h
                break
    letter_style = {}                          # appendix letter -> its first named style
    for letter, style, *_ in raw.values():
        if letter and style:
            letter_style.setdefault(letter, style)
    return {n: (style or letter_style.get(letter), width, section)
            for n, (letter, style, width, section) in raw.items()}

def pages_for(pdf, styles, width):
    """(randoms_pages, other_pages) for a discipline. `styles` is the set of accepted style
    tokens (e.g. {'FS'}, or {None, 'FS'} for bare Collegiate 2-way). other_pages are the
    non-random pages - block pages for most disciplines, the lone formations page for 10-way
    / 6-way speed / VFS-2 blocks."""
    loc = locate(pdf)
    mine = sorted(n for n, (s, w, _) in loc.items() if w == width and s in styles)
    randoms = [n for n in mine if loc[n][2] == 'random']
    others = [n for n in mine if loc[n][2] != 'random']
    return randoms, others

if __name__ == "__main__":
    import sys
    for n, info in sorted(locate(sys.argv[1]).items()):
        print(f"  p{n:2d}: {info}")
