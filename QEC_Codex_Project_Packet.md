# Real-Time Quantum Error Correction Decoder with Hardware–Software Co-Design
## Codex Foundation Context, Research Objectives, Roadmap, and Acceptance Tests

**Project status:** Planned, not yet implemented. Do not state that proposed features, benchmarks, FPGA performance, or research findings have been achieved.

## 0. Instructions to Codex (read before coding)

You are my research software engineering assistant for this undergraduate portfolio/research project. Build the project **incrementally, one milestone at a time**, with clear tests, saved outputs, and reproducible benchmarks. Start at Milestone 0, then Milestone 1. Do not build a complex GUI, machine-learning decoder, quantum LDPC system, or full FPGA prototype at the beginning.

For every milestone:
1. State its scientific/engineering purpose, architecture changes, and acceptance criteria before changing code.
2. Implement the smallest tested vertical slice.
3. Add unit/integration tests, a CLI entry point, and reproducible config(s).
4. Run the tests and a small smoke benchmark where possible; clearly report what actually ran, what did not run, and limitations.
5. Explain generated files, metrics, graphs, assumptions, and what the results do or do not prove.
6. Commit-ready code, readable README updates, and a concise milestone report. Do not invent measurements or performance claims.
7. Stop after the milestone and propose the next milestone; do not silently implement all future phases.

System: Windows laptop; prefer Python virtual environment initially and WSL2/Ubuntu for Verilator/Yosys/cocotb later. Keep the baseline usable without FPGA hardware or a quantum computer. Use compatible, documented package versions and record them. Prefer Python for first iterations; use C++ only if a profiled bottleneck justifies it.

## 1. Project thesis and boundaries

**Title:** Real-Time Quantum Error Correction Decoder with Hardware–Software Co-Design

**Research question:** Can a local, hardware-friendly surface-code predecoder reduce the data and compute burden on a downstream minimum-weight perfect matching (MWPM) decoder while preserving acceptable logical decoding accuracy?

**Subquestions:**
- How does baseline logical failure probability vary with noise probability, code distance, number of rounds, and memory basis?
- Can local syndrome preprocessing reduce residual detector counts and **actual transmitted bits**, including correction metadata?
- Does preprocessing improve downstream MWPM time after counting preprocessing and interface overhead?
- What latency, throughput, queue and buffer size are needed under an explicitly hypothetical syndrome arrival schedule?
- What registers, logic cells, cycles, and (when available) target-dependent timing would a synthesizable predecoder require?
- Under which noise/code regimes does the hybrid architecture help, and where does it make results worse?

**Not in scope initially:** inventing a new stabilizer code, physical cryogenics, microwave control hardware, actual quantum computation on a QPU, buying an FPGA, demonstrating fault-tolerant logical gates, or proving physical end-to-end latency. The work should be accurately called a *simulated QEC decoder and digital hardware prototype*.

**Terms:** Quantum error correction is the whole encoding, syndrome-extraction, decoding, and correction-frame process. Classical decoding is one necessary step that interprets classical detector data. A predecoder is a light local algorithm that may choose partial correction(s) before handing the *residual syndrome* to a global decoder. RTL is a description of digital circuitry; RTL simulation does not constitute an actual FPGA deployment.

## 2. Three architectures and fair comparison

**A: Reference software-only:** Stim surface-code memory circuit -> detector-event sampling -> full PyMatching MWPM -> predicted logical-observable flips -> compare with Stim sampled true observable flips.

**B: New preprocessing algorithm, entirely in software:** Same exact sampled detector-event data -> own Python local predecoder -> corrected/residual detector events -> PyMatching (constructed from the same compatible detector error model) -> combine the predecoder logical-frame contribution and MWPM prediction -> evaluate against the same true observable flips.

**C: Hardware/software split:** Same inputs as B -> functionally equivalent SystemVerilog predecoder simulated with Verilator/cocotb -> simulated output stream/interface -> same downstream PyMatching decoder. Use Yosys for preliminary synthesis statistics. Model the transfer path with explicit latency/clock/bandwidth assumptions. Never call simulated clock latency a measured real-world FPGA speedup.

Establish A before creating B; establish B as a correct reference before creating C. The comparison must use identical input samples and comparable decoding models, hardware platform, and data format wherever possible.

## 3. Technical approach and tools

- **Stim:** generate noisy rotated surface-code quantum memory circuits and sample detection events alongside logical-observable flips. Start with code tasks `surface_code:rotated_memory_x` and `surface_code:rotated_memory_z`; support code distances d=3,5,7 (d=9 later), and choose rounds=d for the first reference experiments. This is a memory experiment, not proof of arbitrary universal FTQC.
- **PyMatching:** construct MWPM decoder from the circuit's decomposed detector error model; decode detector arrays in batches; compare predicted observable flips with actual sampled flips.
- **Sinter:** independently reproduce/reference baseline Monte Carlo logical-error estimates; retain a custom harness for the new predecoder because custom decoding statistics need careful bookkeeping.
- **NumPy/Pandas/Matplotlib (or similar):** samples, results, plots, uncertainty and reporting. `pytest`: correctness/regression tests.
- **SystemVerilog + Verilator + cocotb:** design and verify a small streaming digital predecoder after the Python algorithm is tested.
- **Yosys:** synthesize supported RTL, generate estimated cell/register statistics; optionally add a target technology flow much later.
- **Git/GitHub:** version-controlled source, configs, scripts, references, research notes, reproducibility information.

Official starting references:
- Stim: https://github.com/quantumlib/Stim
- Stim sample/benchmark tool (Sinter): https://github.com/quantumlib/Stim/tree/main/glue/sample
- PyMatching: https://github.com/oscarhiggott/PyMatching
- Stim detector error model format: https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md
- Verilator: https://veripool.org/guide/latest/overview.html
- cocotb: https://docs.cocotb.org/
- Yosys: https://yosyshq.readthedocs.io/
- Paper: Smith, Brown, Bartlett (2023), *Local Predecoder to Reduce the Bandwidth and Latency of Quantum Error Correction*, https://doi.org/10.1103/PhysRevApplied.19.034050

### Important correctness conditions

1. Use **detector events**, not unprocessed raw measurement bits, as PyMatching inputs. Stim's detector annotations include appropriate reference parities and boundaries; do not naively apply XOR to all raw measurements.
2. A local predecoder cannot just discard two firing detector bits. If it chooses a correction/error-model edge `e`, update the syndrome as `s_residual = s_original XOR syndrome(e)` and record any logical-observable frame bit(s) `L_pre`. Combine predictions as `L_total = L_pre XOR L_MWPM(s_residual)`. Work over GF(2). Account for graph boundaries and multiple logical observables.
3. Choose corrections only from valid graphlike mechanisms in the **actual detector error model** (DEM). A short geometric distance alone does not prove that a correction edge exists or that it is safe. Handle correlated/hypergraph terms and unsupported error mechanisms explicitly; start with graphlike-compatible settings.
4. Begin conservatively: e.g., only pair non-overlapping, unambiguous detector pairs linked by a unique admissible local DEM edge, and fall back to global MWPM for uncertain cases. Tests must verify combined correction consistency. A predecoder can decrease speed/accuracy; no improvements are guaranteed.
5. Do not claim that classical logical failure rate will remain identical after heuristic predecoding. Validate statistically and on deterministic fault cases.
6. Separate offline decoding of a complete memory-experiment shot/window from truly online round-by-round decoding. Phase 1 works offline. Introduce streaming windows, buffering, and deadlines explicitly in a later phase.
7. Do not interpret PyMatching's *predicted logical observable flip* as a fully specified set of physical corrective gates. For memory experiments, compare frame/observable predictions correctly.

## 4. Milestones (working sequence; part-time estimates)

### M0. Repository scaffolding and reproducibility (1–2 sessions)
**Purpose:** make experiments easy to repeat and interpret.
- Initialize repo, license, README, `pyproject.toml` or documented requirements, pinned/recorded dependencies, `pytest`, `.gitignore`.
- Define config fields: code type, memory basis X/Z, distance, rounds, circuit noise parameters, shots, seed, output directory, decoder.
- Minimal CLI with `--help`, config file loading, `--smoke`, and a run manifest containing OS, Python/tool versions, config, seed and git commit hash if available.
- Create output directories as needed. No untested architecture claims.
**Exit criteria:** clean install instructions, `pytest` works, CLI help prints, one config parses, manifest is generated.

### M1. Verified standard QEC baseline (approximately week 1–2)
**Purpose:** answer: does the baseline surface-code QEC memory experiment work?
- Use `stim.Circuit.generated` for rotated X and Z memory tasks; begin d=3, rounds=3, a small nonzero noise level; then d=3,5,7 and several noise levels.
- Use `compile_detector_sampler().sample(..., separate_observables=True)` and `pymatching.Matching.from_detector_error_model(circuit.detector_error_model(decompose_errors=True))`.
- Decode and calculate `failure_i = any(predicted_observables_i != actual_observables_i)` and `P_L = failures/shots`.
- Cross-check selected curves or experiment points using Sinter.
- Save `.stim`/`.dem` files (or content hashes), config JSON, CSV results, and `logical_error_vs_physical_error.png` with uncertainty intervals. Baseline numbers must come from actual simulations.
- Report how rate definitions depend on noise model, rounds and experiment type; never call every plot a threshold plot without appropriate crossings and evidence.
**Exit criteria:** tests for noiseless behavior, sample shape, decoded logical predictions, repeatability/manifest; validated baseline run and one real plot.

### M2. Decoder workload and baseline systems measurements (approximately week 3)
**Purpose:** establish measurement methodology before algorithm development.
- Record detector count, nonzero detection-event count distribution per shot/window, bytes for raw vs sparse encoding, PyMatching setup vs decoding time, wall-clock elapsed, CPU/memory usage where reasonably measurable.
- Benchmark `decode_batch` separately from single-shot end-to-end Python pipeline; warm up first; report p50/p95/p99 (enough samples), throughput, and hardware context.
- Use fixed seeds, repeated trials, same shot sets. Define interface format before claiming any bandwidth benefit.
- Add an optional offline *replay* mode for deterministic comparisons.
**Exit criteria:** baseline latency/throughput and detector-density report with documented timing scope and at least one plot/table.

### M3. Conservative software predecoder (approximately weeks 4–5)
**Purpose:** test our own local algorithm against the baseline.
- Build a parser/adapter from graphlike DEM mechanisms into a detector adjacency/edge list with weights, boundary information, and logical masks.
- Design simple local rules with tunable scope or confidence. Prefer deterministic, exclusive, disjoint pair selection; ambiguous cases fall back to MWPM.
- Maintain residual syndrome and accumulated logical mask; run residual syndrome through the appropriate PyMatching graph. Combine logical predictions correctly (XOR).
- Benchmark the same saved sample set across A and B.
- Save predecoder decisions, residual event count, logical failure count, and full timing breakdown for debugging.
- Validate single-fault synthetic cases, boundary edges, multi-fault collisions, X/Z memory circuits, no-error cases, and high-noise fallback. Compare with unmodified MWPM.
**Exit criteria:** all tests pass; complete A-vs-B experiment with measured logical failure rates, residual event fractions, *actual encoded outgoing bytes*, predecoder overhead, MWPM runtime and total runtime. If it loses, report it honestly and analyze why.

### M4. Streaming architecture and resource model (approximately week 6)
**Purpose:** evaluate whether a classical decoder pipeline can keep pace with a simulated input stream.
- Introduce records with `round_id`, `shot/window_id`, detector payload, interface metadata, and timing metadata.
- Implement conceptual ingest -> predecode -> queue -> MWPM stages. Use fixed-size windows first and document required lookahead/measurement boundaries; do not imply instant per-round final corrections.
- Model a configurable syndrome arrival period (e.g. a **hypothetical** 1 microsecond per round), backlog, queue capacity, drop policy (ideally none), deadline misses and throughput.
- Distinguish queueing delay, preprocessing latency, downstream decoding latency and full feedback latency. Clearly mark estimated/model quantities versus measured CPU time.
- Compare software-only and hybrid architectures using the same workload and an explicit data-transfer cost model.
**Exit criteria:** reproducible throughput/queue charts identifying bottlenecks and workload regimes; honest accounting of buffering and future-syndrome context.

### M5. RTL design and verification (approximately weeks 7–8)
**Purpose:** test what the candidate predecoder would look like as real digital logic.
- Translate the supported Python predecoder subset into synthesizable SystemVerilog with parameterized dimensions where practical.
- Define input/output handshake (`valid/ready` or equivalent), cycle-level behavior, reset, pipeline stages, bounded FIFO and error signals.
- Use Verilator+cocotb to compare RTL outputs against Python golden vectors, including edge cases, backpressure, multiple detector events and resets.
- Synthesize RTL using Yosys; export cell and register counts, circuit state, and simulated cycles/event or cycles/window. Report target/clock assumptions. No physical FPGA performance or power claims without implementation measurements.
**Exit criteria:** verified RTL, documented interface, simulation results, synthesis reports, and correspondence to software algorithm.

### M6. End-to-end comparison and research write-up (approximately weeks 9–10)
**Purpose:** answer the main research question with evidence.
- Compare A/B/C where appropriate. Separate measured software performance, RTL simulated cycles, synthesis statistics and estimated hypothetical hybrid performance.
- Vary distance d=3,5,7 (possibly 9), noise levels, number of rounds, predecoding aggressiveness, arrival periods, and interface bandwidth assumptions.
- Use enough failures for meaningful confidence intervals; for no failures, explicitly report an upper bound rather than 0 absolute error probability. Record environment/config/seed/revision.
- Produce four headline figures: (1) logical error probability vs physical error probability, (2) total and component latency vs distance, (3) data volume/bandwidth vs noise and distance, (4) RTL area/throughput or clock-cycle tradeoff. Add a table of failure cases.
- Write short paper-style report: abstract, hypothesis, code/noise model, methods, validity checks, controlled comparisons, uncertainty, findings, limitations, next steps.
**Exit criteria:** end-to-end reproduce command, unit/integration tests, clean README, public-friendly figures, and honest summary of which hypotheses were supported or not.

**Optional later:** C++ hotspot optimization after profiling; physical FPGA deployment if access exists; noise drift/adaptive weights; separate quantum LDPC experiments; actual streaming windowed decoder; real syndrome datasets. Do not make these prerequisites.

## 5. Metrics, formulas, and scientific standards

- **Logical failure probability** for a defined memory experiment: `P_L = (# shots with >=1 incorrectly predicted logical observables)/(# evaluated shots)`; include Wilson/binomial 95% confidence interval, sufficient error events, sample counts and exact circuit/noise assumptions.
- **Paired comparison:** use identical detector samples and actual logical observables for A vs B. Measure failure disagreements and paired uncertainty when possible; don't compare incompatible random samples or code sizes as an algorithm-only win.
- **Detected-event density:** fraction of 1s per detector vector and distribution of number of activated detectors.
- **Residual detector reduction:** `1 - residual_detector_count/original_detector_count` (define handling of zero denominator). This is **not** the same as bandwidth savings.
- **True communication reduction:** count all transmitted bit fields, framing, indices, predecoder correction masks, queue/control fields and update messages; compare a specific documented encoding (e.g. dense bits vs sparse indices) fairly, with same features and assumptions. Avoid comparing sparse hybrid data with inefficient dense baseline without an explicit reason.
- **Processing time:** p50, p95, p99, setup excluded or separately counted, and throughput (shots/windows/rounds per second); show software and RTL metrics separately.
- **Real-time service:** if arrival period is `T_round`, model service/window rate versus arrival rate; track max queue depth, deadline misses and unprocessed backlog. A decoder can keep up in throughput without meeting a given end-to-end feedback deadline.
- **Hardware resources:** Yosys synthesis cell/register estimates, FIFO depth, architecture parameters and clock cycles; target-specific timing, power, and physical FPGA metrics are unavailable until a target implementation is actually performed.
- **Controls:** test both X- and Z-basis memory experiments; same code/noise model/rounds/seed/shot samples, no-error case, intentionally difficult high-noise case and clearly scoped unsupported cases.
- **Success threshold:** do not assert fixed performance gains in advance. Aim for statistically comparable logical failure rates alongside quantifiable compute/bandwidth reductions. Even negative results are informative if rigorously explained.

## 6. User experience: what I want to see when running it

Provide three CLI modes (names are proposed interface designs, not pre-existing commands):

**Quick demo** (runs in seconds or modest time on an ordinary laptop):
```
python -m qec_project demo --distance 3 --rounds 3 --p 0.005 --shots 1000 --seed 42
```
Expected displayed **fields, not fabricated values**:
```
QEC memory experiment | rotated surface code | basis=X | d=3 | rounds=3
noise configuration: [explicit gate/reset/measurement/data probabilities]
shots: 1000; detector_count: [computed]
reference: PyMatching MWPM
logical_failures: [measured]
logical_failure_rate: [measured] (95% CI: [calculated])
mean_detected_events: [measured]
outputs: results/<run_id>/summary.json, stats.csv, demo.png
```
If you include a detector lattice/space-time visualization, distinguish detector bits from raw stabilizer measurement bits.

**Research sweep:**
```
python -m qec_project sweep --config configs/baseline.yaml
```
Expected: actual progress log, CSV rows containing d,p,rounds,basis,shots,failures,CI, decoder, seed, versions and elapsed; generated error-rate curves saved as PNG/SVG. Extend later to predecoder and baseline comparison.

**Architecture benchmark:**
```
python -m qec_project benchmark --config configs/architecture.yaml
```
Expected: table comparing A vs B (and C after RTL exists), residual events, encoded bytes, decoded logical failures, software stage times, throughput and modeled queue/deadline results. Show separate RTL verification/synthesis report after M5.

Provide meaningful error messages when packages/RTL tools are missing and graceful fallbacks (e.g. Python-only benchmark works without Verilator).

## 7. Suggested repository structure

```
real-time-qec-decoder/
  README.md
  AGENTS.md                    # Codex rules; can point to this project packet
  pyproject.toml
  configs/
    smoke.yaml
    baseline.yaml
    predecoder.yaml
    architecture.yaml
  src/qec_project/
    __main__.py
    config.py
    circuits.py              # Stim experiment definitions
    sample.py                # detector samples + actual logical observables
    baseline.py              # PyMatching MWPM adapter
    dem_graph.py             # detector graph and edge/logical bookkeeping
    predecoder.py            # reference local predecoder
    pipeline.py              # buffers, queues, stages, arrival model
    metrics.py               # failure, timing, bytes, uncertainty
    experiments.py
    plots.py
  rtl/
    local_predecoder.sv
    syndrome_fifo.sv
    tb/                      # cocotb verification
  tests/
  scripts/
  results/                   # generated, possibly gitignored
  reports/
    milestones/
    final_report.md
  docs/
    research_notes.md
    assumptions.md
```

Adjust layout only when needed and record decisions in the README. Don't expose a command before its functionality and tests exist.

## 8. Research-result expectations

**Baseline result:** reproducible logical memory failure probability vs physical error parameter, d and basis. It should be physically reasonable; precise trends/thresholds depend on noise model and shots.

**Algorithm result:** conditions where the predecoder reduces detector traffic or MWPM work, and how much it changes logical failure probability; compare confidence intervals and note cases where heuristic guesses hurt.

**Systems result:** a credible latency/throughput/bandwidth model showing under what assumed arrival and interface conditions a processing bottleneck appears; quantify queue pressure and end-to-end processing time.

**Hardware result:** RTL equivalence to reference logic, counts of logic/register resources and simulated cycles, and explicit assumptions for any estimated advantage. Never present a real speedup or power improvement without physical measurement.

**Scholarly result:** a reproducible study (poster/technical report/GitHub) with conclusions even if no performance benefit is observed. Novelty is likely to require deeper algorithmic insights, new hardware tradeoffs, or stronger realistic tests before publication.

## 9. First task for Codex

Start with **Milestone 0 only**, then provide the proposed Milestone 1 experiment and commands. Create a minimal, well-structured project with Python packaging, a working CLI help and smoke-config interface, `pytest` tests, a reproducible environment spec, and README. If Milestone 0 succeeds, ask me before implementing Milestone 1. Explain each technical decision so I can understand the physics and software architecture, not just copy code.
