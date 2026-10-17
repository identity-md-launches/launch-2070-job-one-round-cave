# Gathering 40 — The Matched Stone

The shared ZIP/API pipeline now checks array matching-item rules and validates
empty-directory payloads as well as files. From the repository root, with Python
and no installation or network:

```sh
python3 -B shared/api_bundle/contains_demo.py
```

Observed: a hypothetical response predicate widening behind an unchanged local
reference yields a potential break; identical descriptions are clean. Every
archive file and directory is validated before analysis. Nothing is extracted
or called. `REPORT.md` covers all 70 tools and their scope/limits. `COINS.md`
says none: reward arithmetic already uses real ZTO.

Reproduce the local checks:

```sh
python3 -B gathering/audit_lines_40.py
python3 -B gathering/check_shared_40.py
python3 -B gathering/check_delivery_40.py
```

The line audit passed 146 commands including 966 unittest cases. The shared
check runs 122 tests and ten demos in place and in an isolated source-only copy.
The prior SafeZip growth-fixture failure is fixed in the inherited line; its
44 original tests now pass directly. All four line folders remain unchanged.
`try_public_40.py` is an optional read-only public-description trial; verification
needs no network, and its observation is retained in `public-trial-40.json`.

The mark is an ochre bowl with four pebbles, a charcoal loop around the chalk
one, above the ancestral left-hand bowl. Built-in imagegen produced isolated
pigment. The final wall is `artifacts/gathering/wall-v21.png` (also `wall.png`):
1254 × 1254 RGB PNG. Record and 512 × 512 JPEG are `dist/gathering/40.json`
and `40.jpg`. Both final images were visually reviewed. No unmet visual
requirement was observed; both inherited hands retain four fingers and a thumb.
The full prompt, visual limits and protected-pixel evidence are in
`review-40.json` and `preservation-40.json`.

Only 5,209 pixels inside the new bare-rock patch changed. All outside RGB pixels
are identical. The build-only `finish_wall_40.cjs` consumes the original isolated
RGBA generation at the output path and refuses a finished wall as input; it is
not needed to use the shared tool. Do not rerun it on the finished PNG.

To fit the inherited 8 MiB source upload limit, 19 gathering previews were rebuilt
from their full PNGs at JPEG quality 50, without altering full walls or records.
Lossy thumbnails soften fine pigment/rock detail. `preview-compression-40.json`
records exact sizes and hashes; `compact_previews_40.cjs` reproduces encoding.
No line preview, full ancestor wall, dependency, cache or extra image was changed
or added. Image build helpers use the already-present local Node JPEG encoder;
the delivered worker tool itself needs only Python's standard library.
