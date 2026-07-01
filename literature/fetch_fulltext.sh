#!/usr/bin/env bash
# Fetch a full-text PDF via the UW Wiley Text-and-Data-Mining (TDM) token and
# extract its text, for filling the survey's paywalled measurement fields.
#
# Covers Wiley-published journals — which for this survey includes the AGU titles
# JGR: Solid Earth and Geophysical Research Letters (the bulk of the blocked set).
#
# Setup: the token lives in literature/.secrets.env (gitignored). Get one from
#   UW Libraries; see literature/ACCESS.md.
#
# Usage:
#   literature/fetch_fulltext.sh 10.1029/2019JB017803        # one DOI
#   literature/fetch_fulltext.sh -f dois.txt                 # one DOI per line
#
# Output: literature/pdfs/<doi-with-slash-as-underscore>.pdf and .txt
# PDFs are gitignored (copyright) — only the extracted parameters get committed.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$HERE/.secrets.env"
: "${WILEY_TDM_TOKEN:?set WILEY_TDM_TOKEN in literature/.secrets.env}"
mkdir -p "$HERE/pdfs"

fetch_one() {
  local doi="$1" safe pdf txt
  safe="${doi//\//_}"
  pdf="$HERE/pdfs/${safe}.pdf"
  txt="$HERE/pdfs/${safe}.txt"
  if [ -s "$txt" ]; then echo "skip ${doi} (already fetched)"; return 0; fi
  # Wiley TDM: DOI in the path; returns a 302 to the PDF — follow with -L.
  curl -sL --retry 2 --max-time 120 \
    -H "Wiley-TDM-Client-Token: ${WILEY_TDM_TOKEN}" \
    -H "Accept: application/pdf" \
    "https://api.wiley.com/onlinelibrary/tdm/v1/articles/${doi}" \
    -o "$pdf" || true
  if [ -s "$pdf" ] && head -c 4 "$pdf" | grep -q "%PDF"; then
    pdftotext -q "$pdf" "$txt" 2>/dev/null || true
    echo "OK   ${doi}  ($(wc -c <"$pdf" | tr -d ' ') bytes)"
  else
    echo "FAIL ${doi}  (not a PDF: non-Wiley, not subscribed, or rate-limited)"
    rm -f "$pdf"; return 1
  fi
  sleep 1   # Wiley TDM throttles at a few requests/second; be polite in a batch.
}

if [ "${1:-}" = "-f" ]; then
  n=0; ok=0
  while IFS= read -r doi; do
    [ -z "$doi" ] && continue
    n=$((n+1)); fetch_one "$doi" && ok=$((ok+1)) || true
  done < "$2"
  echo "---- $ok/$n fetched ----"
else
  fetch_one "$1"
fi
