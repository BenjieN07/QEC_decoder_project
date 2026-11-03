# Research progress and how to inspect it

## Status

M0 complete. M1 validated baseline available. M2–M4 have working preliminary
research checkpoints, with limited workload coverage and statistical power.
M5 now has a verified fixed-graph RTL prototype for d=3 X/Z and d=5 X, with
cocotb/Verilator checks and generic Yosys synthesis. See milestones/M5.md and
evidence/M5. M6's final controlled comparison and research write-up are not complete.
No physical FPGA measurements or timing closure results exist.

## What the project studies

Stim simulates storing a logical quantum state with a surface code. Detector
events describe unexpected measurement parities. PyMatching predicts logical
flips from those events. Our local heuristic removes selected valid pairs while
tracking the logical frame, then sends the residual to PyMatching. We test whether
this reduces traffic/work without unacceptable mistakes. Python overhead can
outweigh the savings; hardware is a hypothesis to test later.

## Run it on Windows

From the repository root:
```powershell
.\.venv\Scripts\python.exe -m qec_project demo --distance 3 --rounds 3 --p 0.005 --shots 1000 --seed 42
.\.venv\Scripts\python.exe -m qec_project sweep --config configs/smoke.json
```
Both print a results directory. For a single point, replace RUN below with that
directory; the demo's point is 0:
```powershell
.\.venv\Scripts\python.exe -m qec_project benchmark --replay RUN/0
.\.venv\Scripts\python.exe -m qec_project compare --replay RUN/0
.\.venv\Scripts\python.exe -m qec_project model --replay RUN/0
```
Open the resulting PNG files in any image viewer; CSV in Excel; JSON in an editor.
No GUI application is required. Existing evidence is under reports/evidence.
If Sinter --crosscheck hits temporary-directory restrictions in this app:
```powershell
$env:TMP = (Resolve-Path results).Path
$env:TEMP = $env:TMP
.\.venv\Scripts\python.exe -m pytest --basetemp=results/check-tests -q
```

## Observed results and their limits

- Demo X d=3, rounds=3, all four p=.005 channels, seed=42: 21/1000 logical
  failures, 2.1%, 95% Wilson interval 1.38–3.19%. This is per complete memory
  experiment, not per physical gate or round.
- The 18-point sweep varies basis X/Z, distance 3/5/7 and p=.001/.003/.005.
  Larger distances can help at low noise, but these small samples and overlapping
  intervals do not establish a threshold. Zero failures still has a nonzero upper bound.
- Predecoding on the X example removes 55.24% of firing events. Specified sparse
  bytes fall 22532->19476; dense encoding is 20000 bytes for either path. Thus the
  apparent gain depends on the baseline encoding and includes frame metadata.
- Both decoders fail on the same 21/1000 X shots and 17/1000 Z shots in this run.
  This does not establish equal accuracy. The high-noise stress case changes
  predictions (493 baseline vs 470 hybrid failures, including 33 hybrid-only
  failures); no general advantage is established from a single stress point.
- The Python hybrid loses on total CPU time in the tested runs. Timing needs
  repeated paired trials and broader platform/workload coverage before strong claims.
- Queue plots apply hypothetical arrivals/bandwidth and fixed batch-average CPU
  service. They are neither real quantum feedback measurements nor FPGA estimates.

## Remaining acceptance work

Expand statistical runs and independent Sinter sampling; make sweep/model ranges
configurable; add exhaustive single-fault/invariant and multi-observable tests,
broader paired benchmarks, tested byte serialization and paired uncertainty suited
to sparse disagreements. Add explicit CPU context, per-stage service distributions
and capacity analysis. Then verify RTL with Verilator/cocotb, synthesize with Yosys,
and produce M6's four-figure study across architectures. Existing M2–M4 reports
are checkpoints, not a claim that all research exit criteria are satisfied.
