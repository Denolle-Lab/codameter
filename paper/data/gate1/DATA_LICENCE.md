# Terms for the data archived here

## What is archived

Derived data only. `dvv2y/` holds daily relative velocity change series
(one value per station, band and day, with its error columns and the
per-epoch coherence) computed from cross-correlations of continuous
ground motion. No waveform, no correlation function and no station
metadata from the upstream archive is redistributed here.
`legacy_cd2022/` holds the published 90-day composite product the
comparison is made against.

## Upstream terms, continuous ground motion

The correlations behind these products were computed from the public
Southern California Earthquake Data Center archive (`s3://scedc-pds`,
network CI), distributed through the AWS Open Data programme under this
grant, quoted verbatim from its registry entry:

> SCEDC herby grants the non-exclusive, royalty free, non-transferable,
> worldwide right and license to use, reproduce and publicly display in all
> media public data from the Southern California Seismic Network. Please cite
> the SCEDC (doi:10.7909/C3WD3xH1) and SCSN (doi:10.7914/SN/CI) for any
> research publications using this data.

Checked 2026-11-01 at <https://registry.opendata.aws/southern-california-earthquakes>.
The archive states a citation policy and no further restriction on reuse
(<https://scedc.caltech.edu/about/citation.html>).

Any publication using these products must therefore cite both:

- SCEDC (2013). Southern California Earthquake Center. Caltech. Dataset.
  doi:10.7909/C3WD3xH1
- California Institute of Technology (1926). Southern California Seismic
  Network. International Federation of Digital Seismograph Networks.
  Other/Seismic Network. doi:10.7914/SN/CI

The manuscript's data availability statement carries both citations.

## Upstream terms, the comparison product

`legacy_cd2022/CI.<STA>.arrow` is the 90-day composite relative velocity
change product of Clements and Denolle, as published with

- Clements, T., and Denolle, M. A. (2023). The seismic signature of
  California's earthquakes, droughts, and floods. *Journal of Geophysical
  Research: Solid Earth*, 128. doi:10.1029/2022JB025553

It is reproduced here by its authors, one of whom is an author of this
paper, restricted to the three stations and the two years the comparison
covers.

## Terms for the derived products

**To be confirmed by the author before the archive is deposited.** The
proposal is Creative Commons Attribution 4.0 (CC BY 4.0) for the contents
of `dvv2y/`, which is compatible with the upstream grant and with the
repository's software licence, and keeps the two citations above
mandatory in practice. Until that is confirmed, treat these files as
released for academic use with attribution to this paper.

## Integrity

`CHECKSUMS.sha256` and `MANIFEST.json` list a SHA-256 digest for every
file here. Verify a copy with

```
cd paper/data/gate1 && shasum -a 256 -c CHECKSUMS.sha256
```

or regenerate the manifest with `python scripts/gate1_manifest.py`
(`--check` verifies without writing).
