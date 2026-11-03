# Real-Time Quantum Error Correction Decoder

Research question: can a hardware-friendly local predecoder reduce downstream
MWPM work and communication while retaining acceptable logical accuracy?

**Current scope: M1 baseline implemented.** Offline Stim/PyMatching memory experiments
are available; predecoding and RTL are not yet implemented. The packet defines M0–M6.

## See actual simulation results

```powershell
.\.venv\Scripts\python.exe -m qec_project demo --distance 3 --rounds 3 --p 0.005 --shots 1000 --seed 42
.\.venv\Scripts\python.exe -m qec_project sweep --config configs/smoke.json
```

The program prints a results folder containing stats.csv, a plot, a manifest and
per-point circuit/DEM/config/sample files. The sweep currently fixes X/Z,
d=3/5/7, rounds=d and p=.001/.003/.005; shots/seed/output come from the config.
The demo's --p applies to each of the four noise channels. Logical failure rate
means the fraction of whole memory experiments whose observable was predicted
incorrectly. Error bars show 95% Wilson intervals; zero failures is still uncertain.
`--crosscheck` compares the same samples through Sinter's PyMatching adapter.
See reports/milestones/M1.md for evidence and limitations. These plots are not
threshold claims or hardware performance results.

## Install and run

Use Python 3.11 or newer. On Windows, create a virtual environment using an
installed Python executable (`py -3` or its full path if `python` is unavailable):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev,research]'
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m qec_project --help
.\.venv\Scripts\python.exe -m qec_project --smoke --config configs/smoke.json
```

If the execution environment restricts the system temporary directory, use
`python -m pytest --basetemp=results/pytest-temp -q` (pytest clears this test-only
directory on subsequent runs).

After activation, `qec-project` is the equivalent console command. On Linux use
`.venv/bin/python`. Run the example from the repository root. Config and output
paths are relative to the current working directory. `research` installs the M1
tools; M0 itself uses only Python's standard library. `dev` installs pytest.

`requirements-lock.txt` records the validated environment; install it before
`pip install --no-deps -e .` to reproduce those dependency versions on a compatible
Python/platform. Package ranges in pyproject describe supported candidates;
the lock records one tested resolution, not all possible environments.

## Why these choices

- A small `src` package keeps reusable research code separate from outputs/tests.
- JSON gives explicit, version-controlled configuration without a YAML parser.
  Validation rejects unknown fields, invalid probabilities and unsupported modes.
- Basis X/Z selects the future logical memory experiment; distance controls code
  size and rounds controls the time extent. They are independent settings.
- Noise fields match Stim's circuit generator names. Equal numeric values do not
  imply a single aggregate physical error probability. See the
  [Stim documentation](https://github.com/quantumlib/Stim) and
  [PyMatching documentation](https://github.com/oscarhiggott/PyMatching).
- The seed is stored for future sampling. Exact random samples may depend on
  Stim version, execution environment and sampling calls; a seed alone is insufficient.
- Each smoke run creates a unique `results/<id>/manifest.json`, preserving earlier
  runs. It records OS, Python/package versions, config, seed, UTC time, Git commit
  and working-tree status. Missing packages/Git are represented by null values.
- Git commit plus dirty status distinguishes committed code from local edits.
  Installed wheels outside a source checkout may have no Git provenance.
- Results and virtual environments are ignored to keep commits reviewable.
- No simulation is run by `--smoke`. Its manifest explicitly says so; it cannot
  establish logical accuracy, decoding throughput, or hardware latency.

## Layout and next milestone

`configs/` holds settings, `src/qec_project/` holds configuration/CLI code,
`tests/` checks infrastructure, and `reports/milestones/` records acceptance evidence.
MIT licensing permits reuse while retaining attribution.

M1 will generate rotated surface-code X/Z memory circuits, sample detector events
and actual observables, and compare PyMatching predictions with those observables.
Planned experiments begin at d=3, rounds=3, seed=42, including noiseless controls
and a small noisy run, followed by a Sinter cross-check and uncertainty intervals.
The proposed `demo` and `sweep` commands are intentionally deferred until tested.
The existing smoke command above remains the only experiment-facing command.
M1 requires the user's go-ahead.
