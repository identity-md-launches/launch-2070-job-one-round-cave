# RewardBundle

Carry one complete exact ZTO allocation to another worker in one bounded JSON
file. The bundle includes the original request, token metadata, full report and
recomputed receipt. Verification recomputes the allocation from those inputs,
including every rounding unit. Python standard library only; no installation,
network, wallet or transaction is needed to run it. Keep the sibling RewardSplit
and RewardReceipt source folders when copying this tool.

From the repository root:

```sh
python3 -B line-3/tools/rewardbundle/rewardbundle.py demo
```

Tried locally: a serialized round trip preserves exactly **1 ZTO**, or
1,000,000,000,000,000,000 atomic units, across three illustrative address-free
roles. The demo uses the included real Ethereum observation at block
**26211313**, captured on 2026-10-17. Read-only calls checked the chain, block,
symbol, name, decimals and total supply, then checked the block hash again.
Public provenance: https://ethereum-rpc.publicnode.com. This single RPC capture
is neither an independent chain proof nor a fresh balance observation.

To carry your own allocation, use the same metadata for allocation and packing:

```sh
python3 -B line-3/tools/rewardsplit/rewardsplit.py allocate --input REQUEST.json --metadata line-3/tools/rewardbundle/zto-observation.json --output REPORT.json
python3 -B line-3/tools/rewardbundle/rewardbundle.py pack --request REQUEST.json --report REPORT.json --output BUNDLE.json
python3 -B line-3/tools/rewardbundle/rewardbundle.py verify --bundle BUNDLE.json
```

`pack --metadata PATH` selects a different capture; its default is this tool's
`zto-observation.json`. The receiving worker needs only BUNDLE.json as data and
these tool sources. No input path or executable is taken from the bundle; it
does not extract files. Exit 0 means verified arithmetic; exit 2 means refusal.
The output includes a canonical `bundle_sha256`. To check a digest received
through a separate trusted channel, add `--sha256 DIGEST` to `verify`. It must
be 64 lowercase hexadecimal characters. The digest is of compact, sorted-key,
ASCII JSON without a trailing newline; whitespace and object-key order do not
matter, while JSON value types and array order do.

A consistent replacement of the request, metadata and report can pass arithmetic
verification. Only a separately obtained expected digest detects replacement of
the whole bundle. A digest inside the same untrusted message establishes no
authority. The demo's expected digest is calculated locally to demonstrate the
comparison, not to authenticate a sender. Keep source metadata you trust;
untrusted metadata can misstate token decimals. No work, identity, entitlement,
available funds, signature or payment is verified.

Inputs and outputs must resolve inside the current workspace. JSON inputs and
the serialized bundle are limited to **96,000 bytes**, nesting to 64 levels and
values to 20,000 nodes. Duplicate keys, non-finite constants, unknown bundle
fields, altered receipts/reports, mismatched expected digests and existing
output files are refused. Large otherwise-valid rosters may exceed this tighter
handoff limit; reduce them rather than silently omitting contributors. Paths
assume no hostile concurrent filesystem mutation. Python JSON parsing itself
precedes the nesting check; this is bounded input handling, not OS isolation.

```sh
python3 -B line-3/tools/rewardbundle/selftest.py
```

All 12 tests passed, including 200 seeded exact handoffs, one-unit and uint256
budgets, zero shares, complete bundle replacement, tampered components and
numeric types, duplicate/deep JSON, byte limits, file round trips, workspace
escape and overwrite refusal. Eight inherited RewardReceipt tests passed too.
