#!/usr/bin/env bash
# Fetch a source PDF and verify it is a real PDF, not an HTML bot-wall challenge.
# Usage: fetch_pdf.sh <url> <outpath>. Nonzero exit on download or validation failure.
set -eo pipefail

url=$1
out=$2
# Spoof a browser past a possible bot wall
ua='Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0'

curl -fsSL --retry 3 --retry-delay 5 -A "$ua" "$url" -o "$out"
# AXIS PDFs lead with \r\n, spec allows header anywhere in first 1024B
head -c 1024 "$out" | grep -aq '%PDF'
