# Fixed-graph window predecoder

`scripts/prepare_rtl.py` generates `local_predecoder.sv` from an actual Stim DEM.
The generation config and DEM hash are saved alongside golden vectors. Supported
local corrections are the same isolated pair subset as Python; boundaries,
hyperedges and correlated decompositions are deferred to downstream matching.

The graph is specialized at generation time rather than loaded at runtime.
Distance, round count, basis or noise-model changes require regeneration.
Detector bit i is bit i of the packed syndrome/residual word; logical bit i is
bit i of the frame. A whole shot/window is presented in parallel.

## Interface

- Input transfer occurs at a rising edge with `in_valid && in_ready && !rst`.
- `residual` and `frame` become available after that edge with `out_valid=1`.
- Output transfer occurs at a rising edge with `out_valid && out_ready && !rst`.
- One output entry provides bounded storage. When full and stalled, input ready
  falls and output data remains stable. Upstream must retain unaccepted data.
- Simultaneous output removal and new input acceptance are supported.
- Synchronous active-high reset clears valid and data, discarding any pending
  window. The controller must replay discarded windows after reset if needed.
- Without stalls: one cycle input-to-output availability and one cycle initiation
  interval. A 10 ns test clock is only a simulator schedule, not timing closure.

Combinational selection computes active edges and rejects any edge sharing an
active endpoint with a competitor, using the original syndrome. Chosen edges
XOR their detector support and logical masks. The one-entry buffer is intentionally
minimal; there is no external FIFO, overflow/drop policy or serial link in this core.
There are no unsupported-mechanism error signals: unsupported local corrections
are excluded by the generator and left in the residual syndrome.

## Reproduce (Windows then Ubuntu)

From Windows project root:
```powershell
.\.venv\Scripts\python.exe scripts/prepare_rtl.py --basis X --distance 3 --output results/rtl-x3
```

Inside Ubuntu, from `/mnt/c/oned/QEC_decoder_project-1`:
```bash
python3 -m venv /tmp/qec-rtl-env
/tmp/qec-rtl-env/bin/python -m pip install -r requirements-rtl-lock.txt
/tmp/qec-rtl-env/bin/python scripts/verify_rtl.py results/rtl-x3 --build-dir /tmp/qec-rtl-x3-build
```

The runner compiles with Verilator, runs the cocotb scoreboard, and then invokes
Yosys generic synthesis. Check verification.xml, cycles.json and synthesis.log.
Generic cells are not FPGA LUTs, target area, power or achievable clock frequency.
The temporary environment/build directory may be removed at restart; recreate it
using the same commands. Keep permanent project results in the repository folder.
The generated wide combinational design may have unfavorable timing as distance grows.

Official references: [cocotb runner](https://docs.cocotb.org/en/stable/runner.html),
[Verilator options](https://verilator.org/guide/latest/exe_verilator.html),
[Yosys](https://yosyshq.readthedocs.io/).
