# Real-Time QEC Decoder — Codex Repository Instructions

## Mission
Build and scientifically benchmark a hybrid quantum error correction decoder architecture: Stim surface-code memory experiments, a standard PyMatching MWPM reference, our conservative local predecoder, a streaming classical resource model, and (later) a simulated SystemVerilog predecoder verified against the Python golden implementation.

**Read `QEC_Codex_Project_Packet.md` before making any project changes.** It defines scientific assumptions, milestones M0–M6, interfaces, research results, tests, and limitations. That packet is the project specification. Keep this `AGENTS.md` short and update its rules only when needed.

## Work one milestone at a time
- Start with **M0 (repository scaffolding)** only. Do not implement M1+ until the user requests it.
- Before each milestone, state goals, changed files and tests. After implementation, report exact commands run, test results, data files, assumptions and next recommended milestone.
- Implement a minimal working CLI with reproducible configs, unit tests and honest documentation. Do not fake results or claim unfinished work is complete.
- Keep initial pipeline Python-only and runnable without special hardware. Use WSL2/Ubuntu later for SystemVerilog/Verilator/cocotb/Yosys. No FPGA purchase is needed.
- Use official API docs for Stim, PyMatching, and Sinter; validate versions at install.

## Scientific correctness
- Detector events are not necessarily raw stabilizer measurement bits; use Stim detector definitions.
- For a predecoder choosing an error-model edge `e`, update the syndrome with XOR of its detector support, record its logical-observable bitmask, then combine `L_pre XOR L_MWPM(s_residual)`.
- Use only valid DEM-supported edges, handle boundaries, and fall back on unresolved/ambiguous cases. Preserve actual observable values for scoring and use the same sampled shots to compare decoders.
- Report uncertainty and sample counts, not just percentages. Define the noise channels, code distance, round count, logical basis, and metrics precisely.
- Distinguish offline window decoding, pipeline throughput, classical latency, RTL simulated cycles, synthesized resource estimates, and actual physical hardware latency. Do not claim physical FPGA speed or power results from RTL simulation alone.

## User expectation
The user wants a research-quality, understandable undergraduate portfolio project with measurable improvements *or informative negative results*. Teach as you implement: explain what quantum error correction, classical decoding, predecoding and digital hardware each do. Clearly mark target outcomes versus measurements. Keep checkpoints reviewable and the project suitable for GitHub and a technical poster/report.
