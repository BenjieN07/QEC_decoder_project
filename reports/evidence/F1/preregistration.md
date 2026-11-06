# F1 — guarded local decisions: frozen evaluation plan

This follow-up uses M6 and its saved failures for development only. The new
held-out samples below have not been generated or inspected at registration.
Only this one candidate is evaluated; no threshold tuning or rerun selection is
permitted on the held-out results. Smoke samples are separate pipeline checks.

## Fixed rule and rationale

Start with the existing unambiguous whole two-detector DEM mechanisms. Require
agreement with the merged matching graph's logical mask. Retain an edge (a,b)
only when the sum of weighted shortest distances a->boundary and b->boundary,
minus the direct edge weight, is at least ln(10). Distances use nonnegative
PyMatching graph weights. Any graph containing negative or nonfinite weights
falls back entirely to MWPM. Unreachable boundary distances give an unbounded
margin, not a missing-data probability estimate.

For each firing candidate, require no other firing detector within two graph
hops of either endpoint. The shared abstract boundary participates in this
neighborhood and is excluded from the detector bit vector. This is deliberately
conservative; paths through that boundary can enlarge the guard substantially.
All guards use the original syndrome and include competing endpoints, so choices
are disjoint. XOR detector support and logical masks exactly as in M6.

The boundary margin is a graph cost comparison, NOT a calibrated 90% posterior
confidence: other paths, degeneracy and correlated mechanisms still matter.
No guarantee of matching optimality is claimed. No new RTL is part of F1.

## Primary held-out grid and engineering criteria

X/Z, d=3/5/7, rounds=d, p=.004/.007 in all four noise channels: 12 points,
100,000 shots each. Seed origin 202611060001, increment 104729 per point.
Samples are paired across A, M6 unrestricted, M6 strict and the new guarded rule.
The held-out probabilities differ from the M6 development grid.

Accuracy criterion: for every primary point, the upper bound on guarded minus A
failure probability must be <=0.0002 (0.02 percentage points). Use the existing
conservative paired exact interval, with alpha=.05/12 to give >=95% simultaneous
coverage over the 12 primary comparisons by Bonferroni. This is a provisional
engineering tolerance for this study, not a fault-tolerant-computing requirement.

Communication criterion: >=5% adaptive-encoding byte reduction at at least one
primary point, while satisfying the accuracy criterion at ALL primary points.
Both paths include the same header/frame and explicit adaptive format tag.
This identifies whether any useful regime exists, not an average universal gain.
Timing is descriptive, not a promotion criterion. Warm five alternating batch
trials on up to 4096 saved shots; sampling/setup/serialization excluded and stated.

Promotion requires both criteria. A failure or inconclusive interval is reported
honestly. No rule revision, margin relaxation or extra favorable seeds after
seeing held-out results. A revised candidate would require a new registered study.

## Controls and saved evidence

Stress: X/Z d=5/7, rounds=2d, p=.007, 50,000 shots each; descriptive only.
Noiseless X/Z d=3, rounds=3, 10,000 shots each. All sampled observables preserved.
Development failure replay checks whether old decisions would be rejected; it
cannot establish held-out safety. Synthetic tests cover guard collisions, a
nearby boundary, multi-observable masks and XOR reconstruction.

Save configs, source/config hashes, versions, Git state, circuits/DEMs, actual
samples and A/B predictions, paired intervals, bytes, raw timing trials, candidate
metadata, three comparison figures and an F1 report. Commit this registration
before running the held-out grid. Stop after this follow-up and recommend the
next experiment based on its results.
