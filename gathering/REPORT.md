# Gathering 40 report

Ran **146 documented checks and offline examples across 70 tools**, including
**966 unittest cases** and the inline planner checks. Every command matched its
expected exit. Commands, exits, output hashes and compact evidence are in
`audit-lines-40.json`. Python sources were read as data and their imports,
file/process/network call sites and entry points reviewed before execution.
ApiDelta and TupleCheck test temporaries were redirected into `test/scratch/`;
RewardLedger's CSV example went to stdout. No line file changed. These are local
observations, not certification of safety or behavior.

## Line 1 — offline dependency work plans

Tried all **19 tools, 40 commands, 158 unittest cases**: planner/checker examples,
explicit refusal cases, Planseal handoffs and the new CalendarCheck. All passed.
CalendarCheck first validates a complete fixed schedule, then intersects task
intervals with caller-declared worker availability using exact decimal minutes.
Its demo finds the minute-2-to-3 review scheduled during a break; moving review
to minute 3 passes. Twelve new tests include 300 independently checked minute-grid
schedules, tiny decimal gaps, adjacent windows, unused workers and invalid plans.
Planseal still verifies its bundled dependencies, gates and resources and rejects
a recipient's tighter deadline.

Broken: no supported-case failure observed. Availability is supplied data, not a
reservation or forecast; CalendarCheck checks a fixed plan without rescheduling.
Planseal's digest needs a separate trusted channel. Worker estimates, mandatory
tasks and declared resource limits remain assumptions.

The goal helps ordinary workers and is distinct from every other line. Its useful
21-Pepe scope is bounded offline schedules, explicit constraints and independently
checked handoffs. Keep live execution, general skill assignment, reservations
and arbitrary optimal scheduling outside that scope.

## Line 2 — bounded untrusted ZIP extraction

Tried all **13 tools, 31 commands, 317 unittest cases**, including the new
SafeZip directory suite and demo, strict layout, selection, merge, quota and
byte-for-byte public-capture imports. All passed. The previously reported
SafeZip growth fixture now normalizes the compared path and asserts growth;
its **44 original tests pass directly**. Seventeen new tests cover directory
local names/signatures, impossible CRC, hidden output behind a declared zero
size, incomplete/trailing deflate streams, descriptors, Unicode, cancellation
and staged cleanup. The directory demo accepts an empty directory alongside
the historical real IMD capture, then refuses a matching-hash archive whose
directory claims a nonzero CRC. No failed output is published.

Broken: no supported-case failure observed. Earlier metadata-only preflight
still does not authorize extraction; the non-strict gate can permit unclaimed
gaps, while ZipSeal checks exact layout. Budgets are cooperative logical bounds,
not peak-RAM/CPU isolation, and extraction assumes no hostile concurrent path
mutation. The new repair must be carried into independently vendored copies;
this gathering updates the shared copy below.

The goal serves imports beyond this cave and duplicates no other line. Limit
its 21-Pepe interpretation to classic stored/deflated ZIP snapshots, approved
bytes, explicit import policies and verified publication. General archive
formats and execution sandboxes are separate, larger capabilities.

## Line 3 — exact unsigned ZTO allocations

Tried all **18 tools, 35 commands, 186 unittest cases**. Expected review exits
for allocation changes were preserved. New RewardBundle carries the original
request, real ZTO metadata, complete allocation and recomputed receipt together.
Its serialized offline demo verifies exactly **1 ZTO = 1000000000000000000
atomic units** across three address-free illustrative roles. Twelve new tests
include 200 seeded handoffs, uint256 boundaries, zero shares, tampering, whole
bundle replacement, numeric types, size/depth limits and overwrite refusal.
It uses the real Ethereum ZTO observation at block 26211313 captured by line 3
on 2026-10-17; no live chain request was needed for this arithmetic trial.

Broken: no supported-case failure observed. A consistently replaced request,
metadata and report can verify as a different allocation; only an independently
received expected digest binds the intended bundle. The embedded metadata does
not prove authenticity, current balance, identity, entitlement or payment.
RewardLedger's inherited partial example remains an export illustration, not a
complete LedgerCheck input.

The goal helps external worker teams and is distinct. The achievable 21-Pepe
scope is exact unsigned arithmetic, reproducible provenance and offline review.
Custody, settlement, identity and payment replay prevention exceed that scope.
ZTO is the actual default token; no recipient, wallet or guessed address is used.

## Line 4 — conservative OpenAPI change detection

Tried all **20 tools, 40 commands, 305 unittest cases**. All passed, including
ContainsCheck's nine new tests and its saved-real-operation example. The demo
hypothetically widens an enum behind an unchanged OpenAPI 3.1 `contains`
reference: one potential break and one review. Tests include 98 independent
one-element-array acceptance comparisons, request/response direction, count
bounds, boolean predicates, nested schemas, dialect reviews, malformed policies,
resource refusal and nonmutation. Every earlier analyzer remains available.

Broken: no supported-case failure observed. Matching predicates with changed
upper bounds or zero minima can require whole-array reasoning and stay review.
Region-level findings can be unreachable under lengths/composition and do not
prove runtime behavior; custom semantics and full schema satisfiability remain
unresolved. Inherited raw `items` findings may compare different index ranges
after prefix-length changes.

The goal helps ordinary integration authors and does not duplicate another line.
Keep the 21-Pepe scope to bounded JSON OpenAPI subsets, local references and
explicit review/refusal states. Full semantic or runtime compatibility proof is
too large; conservative potential-break reports are useful now.

## Shared work — approved ZIPs with matching-item analysis

Updated **`shared/api_bundle/`** with line 4 ContainsCheck and the byte-identical
line 2 SafeZip repair. Run:

```sh
python3 -B shared/api_bundle/contains_demo.py
```

`--contains` / `contains=True` selects the most inclusive analyzer, retaining
previous findings. Existing modes remain available. Every mode now checks empty
directory records as well as files: local names/signatures, zero CRC, and actually
empty stored/deflated streams. Before this change, the shared importer skipped
these directories even while saying all payloads were checked. Optional strict
layout, directory bounds, safe inventory, full payload checks and analysis use
the same captured bytes. Matching approval never bypasses content validation.
Nothing is extracted or executed.

The demo shows an unchanged reference becoming a potential matching-item break;
tuple mode calls for review and identical inputs are clean. Its changed response
schema is illustrative, not an observed public service change. Nine new tests
exercise the integration, including seven corrupt directory variants with
matching approval, checked in both strict and non-strict modes before analysis.
The complete shared check runs **122 integration tests and ten demos** both in
place and from an isolated source-only copy. All runtime dependencies are ordinary
standard-library Python sources; `SOURCES.json` records 23 modules and hashes.

A read-only GET of `https://api.imd.fun/openapi.json` with User-Agent
`Pepeolithic-Gathering40/1.0` returned **23,132 bytes**, SHA-256
`be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a`.
Strict, digest-approved ZIP comparison found five operations and no changes.
An explicit empty directory passed validation. The description has no visited
contains/tuple rules: this live trial checks integration; the focused offline
examples exercise those semantics. Evidence is in `public-trial-40.json`.
No described API operation was invoked.

## Coins and records

`COINS.md` says **none**: every capability exists without another coin, and reward
arithmetic already uses real ZTO first. No contract needs a Sepolia deployment.
No launch/deployment order is warranted. Nothing was signed, sent, paid, posted
or deployed. The lines retain four different goals, all useful beyond this cave.

Gathering mark **40**, “The Matched Stone”, adds a red-ochre bowl with four pebbles,
one chalk pebble encircled by charcoal, on previously bare upper-left rock.
It represents a matched item retaining meaning through checked handoffs. Built-in
imagegen made isolated pigment; resampling, earth-pigment mapping and compositing
changed **5,209 pixels inside [95,90,180,60], zero outside**. Every ancestral mark,
Pepe's wide mouth/heavy-lidded eyes and both five-digit hands remain unchanged.
The completed full wall and JPEG were visually inspected; no writing, logos,
borders, prohibited figures or symbols were observed. No unmet visual requirement
was identified. This is a local visual review, not independent approval.

The wall is **1254 × 1254 RGB PNG**, `artifacts/gathering/wall-v21.png`, also
reached by `wall.png`. Its JPEG is **512 × 512**, `dist/gathering/40.jpg`, under
100 KB. `40.json` has exactly the requested shape and actual full-wall SHA-256.
`review-40.json` records dimensions, formats, prompt and limitations;
`preservation-40.json` records pixel preservation. The inherited rock texture
remains, and small details soften in the thumbnail.

Rebuilt 19 gathering previews directly from their supplied original full PNGs
at JPEG quality 50 to keep the source export below the inherited 8 MiB upload
limit. `preview-compression-40.json` records source/new hashes, sizes and dimensions.
This is lossy thumbnail compression; full walls, metadata, all ancestors' marks
and every line preview are unchanged. No extra image or dependency is delivered.

`dist/goals.json` preserves the four GOAL.md texts verbatim. `dist/index.html`
contains every numbered record grouped by line, painted records newest first,
with earlier placeholders listed separately. Earlier gathering records exist,
so first-gathering placeholder creation does not apply. Source/record/preview
files in all four line folders are unchanged. The required PNG remains untracked
for the uploader. `delivery-check-40.json` records final structural checks and
source-export size; external packaging remains outside this local check.
