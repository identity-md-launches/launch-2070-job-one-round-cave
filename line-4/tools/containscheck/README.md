# ContainsCheck

Detect potential breaking changes to OpenAPI 3.1 array `contains` rules before
updating an integration. This standard-library Python tool extends TupleCheck
and retains every earlier line 4 finding. Keep the sibling tool folders. It
reads descriptions only; it never invokes the operations they describe.

From the repository root, one offline command shows it working:

```sh
python3 -B line-4/tools/containscheck/containscheck.py demo
```

The demo starts with a saved real public IMD API operation and gives it a
**hypothetical** response array. Its unchanged `contains` reference points to
an enum that expands from `pending, done` to include `retry`. ContainsCheck
follows the reference and reports **one potential break and one review**.
The new array policy is illustrative, not an observed change to IMD.

Compare two local JSON descriptions inside the current workspace:

```sh
python3 -B line-4/tools/containscheck/containscheck.py compare old.json new.json
```

The JSON report includes exact input-byte hashes. Exit 0 means no detected
break in the supported subset; 1 means a potential break; 2 means invalid or
unsupported input or a resource refusal; 3 means unresolved review only.
`compare(old_dict, new_dict)` returns a report without byte hashes and without
mutating the dictionaries. `contains_pairs` lists each visited array region.

## Supported rule

OpenAPI 3.1 uses the JSON Schema 2020-12 `contains`, `minContains` and
`maxContains` rules ([OpenAPI Schema Object](https://spec.openapis.org/oas/v3.1.0.html#schema-object),
[JSON Schema validation](https://json-schema.org/draft/2020-12/json-schema-validation#section-6.4)).
With a positive matching-item minimum and no maximum on either side, the tool
compares both resolved item predicates using the inherited request/response
variance rules. It follows unchanged local references to changed targets.
When predicates resolve identically, it checks directional changes to the
matching-item minimum and maximum. Adding an effective `contains` count
constraint to requests, or removing one from responses, is flagged. A false predicate
always has zero matches, so changes between positive minima or nonnegative
maxima for that predicate do not create a false break finding.

Mixed predicate and count changes, changed predicates with an upper bound,
zero-minimum predicate changes, and OpenAPI 3.0 or cross-version pairs receive
review rather than a claimed break. Earlier generic reviews remain. Visited
count values must be nonnegative integers; `contains` must resolve to a schema.
Remote references, malformed local references, unsupported reference siblings,
and budget overruns refuse the comparison without a partial pass. At most
1,024 `contains` pairs are visited, in addition to inherited input, schema,
operation, finding and tuple limits.

A finding concerns one array region. Other array constraints, composition,
`unevaluatedItems`, schema reachability and actual server behavior may affect
whole-payload compatibility. A clean report is not a runtime guarantee.

## What happened when tried

```sh
python3 -B line-4/tools/containscheck/selftest.py
python3 -B line-4/check-40.py --live
```

On 2026-10-17, all **9 new tests** and **305 tests across 20 suites** passed.
The new tests include 98 independent one-element array acceptance comparisons,
unchanged reference targets, directional count changes, boolean predicates,
nested schemas, dialect review, malformed inputs, budgets and nonmutation.
The optional live step fetched only the public `https://api.imd.fun/openapi.json`
description with User-Agent `Pepeolithic-ContainsCheck/40.0`. Its 23,132 bytes
matched the bundled capture; five operations compared with zero findings.
That description has no visited `contains` pairs, so the live trial checks
integration and unchanged behavior. No described operation was called.
Evidence is in `line-4/check-results-40.json`.

Static description comparison needs no coin, wallet, key, payment or account.
