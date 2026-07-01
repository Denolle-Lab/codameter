# Filling the paywalled survey rows: institutional access

The literature survey's measurement fields (frequency band, coda window,
estimator, uncertainty) were re-checked against the full text for the 40
open-access studies reachable without a subscription. About 60 rows remain at
abstract level because the papers are paywalled. This note records the two ways to
reach them; both feed the same extraction workflow, and neither commits a PDF to
the repo (copyright — `literature/pdfs/` is gitignored).

## Option A — UW Husky OnNet VPN (IP-based access)

Puts this machine on a UW IP, so publishers that grant access by IP serve the
full text to a plain `curl`. Best-effort: some publishers still block automated
fetches behind Cloudflare even with a valid campus IP.

1. Download **Husky OnNet** (the client is F5 BIG-IP Edge Client) from
   <https://www.washington.edu/itconnect/connect/uw-networks/about-husky-onnet/>,
   or install **F5 Access** from the macOS App Store.
2. Open it and sign in with your **UW NetID** (with 2FA).
3. Choose the **"All Internet Traffic (Full Tunnel)"** profile, *not* "UW Campus
   Network Traffic Only". Publisher sites are off-campus, so a split tunnel would
   route their traffic outside the UW IP range and you'd get no access.
4. Connect. Verify with `curl -s https://api.ipify.org` — the IP should be in a
   UW block (`128.95.*`, `140.142.*`, etc.).
5. Tell me it's connected; I'll retry the blocked DOIs with Bash `curl`. (The
   WebFetch *tool* does not use your VPN — only Bash does — so this only helps the
   Bash path.)

Disconnect when done; a full tunnel routes all your traffic through UW.

## Option B — Wiley TDM token (programmatic, covers AGU/Wiley)

The robust path for scale. Wiley publishes the AGU journals **JGR: Solid Earth**
and **Geophysical Research Letters**, which are the bulk of the blocked set.

1. **Token obtained** (2026-07-01) — stored in `literature/.secrets.env`
   (gitignored) as `WILEY_TDM_TOKEN`. Get one at
   <https://onlinelibrary.wiley.com/library-info/resources/text-and-datamining>
   (institutional subscribers request a Client Token).
2. Fetch a single paper:
   ```bash
   literature/fetch_fulltext.sh 10.1029/2019JB017803
   ```
   or a batch (one DOI per line):
   ```bash
   literature/fetch_fulltext.sh -f dois.txt
   ```
   PDFs and extracted text land in `literature/pdfs/` (gitignored). The script
   throttles ~1 req/s (Wiley TDM rate-limits).
3. I then read the `.txt`, extract the four measurement fields **with a verbatim
   quote each**, append them to `literature/verified_fulltext.jsonl` with
   `"measurement_source":"full text (this work, 2026)"`, and re-run
   `merge_verified.py` → `build_table.py` → `build_survey.py`.

Non-Wiley paywalled papers (a few Elsevier landslide/Eng. Geol. titles, one
Springer) are not covered by the Wiley token; those need Option A, an Elsevier TDM
key, or a manual PDF drop into `literature/pdfs/`.

## Security

- The token is a live credential: it stays in `literature/.secrets.env`
  (gitignored, `chmod 600`) and is **never** committed or echoed into a doc.
- Do not paste NetID passwords or browser session cookies anywhere — they are
  brittle and a security risk. Tokens in env vars/gitignored files only.
- If the token leaks or is rotated, replace the value in `literature/.secrets.env`.
