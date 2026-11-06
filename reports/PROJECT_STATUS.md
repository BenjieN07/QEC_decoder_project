# Project status

The first M0–M6 study is implemented, tested and reported in
[final_report.md](final_report.md). It is a simulated QEC decoder and verified
digital prototype, not a deployed FPGA system or a publication claim. Earlier
milestone reports preserve the history of smaller preliminary runs.

[H1](milestones/H1.md) now adds **actual IBM quantum-processor measurements**:
512 X and 512 Z d=3/three-round memory shots on ibm_marrakesh, using the free plan.
Offline MWPM failed on 242/512 X and 165/512 Z shots; predecoders matched baseline
predictions. The decoder prior is uncalibrated and routing overhead is substantial.
No error-correction advantage, real-time feedback or physical FPGA execution was
demonstrated. [Evidence](evidence/H1/summary.json) and
[figure](evidence/H1/real_qpu_pilot.png) are available without another cloud job.
Local keys/CRN are ignored and never part of the public evidence.

The latest extension is [F1](milestones/F1.md): a preregistered guarded rule tested
on 1.2 million fresh primary shots plus 220,000 control/stress shots. It has no
observed baseline prediction disagreements and passes the provisional simultaneous
accuracy bounds, but its best adaptive saving is 4.00%, below its fixed 5% target.
It remains slower on CPU and is **not promoted to RTL**. See the
[verdict](evidence/F1/verdict.json), [figures](evidence/F1/F1_bytes.png) and
[data](evidence/F1/results.csv). The M6 findings below describe the earlier study.

## Evidence

- 36 configurations, 30,000 shots each: **1,080,000 main-study windows**, identical
  samples for both decoder policies and baseline comparisons.
- 40,000 control shots and 30,000 independent Sinter replication shots.
- 120,000 existing shots replayed through RTL on X d=3/5/7 and Z d=3, matching
  Python residuals, frames and downstream observable predictions.
- Repeated batch timings plus individual-window timing including serialization.
- Tested dense/sparse/adaptive serialization, paired uncertainty, graph audits,
  failure traces, four headline figures and queue sensitivity plots.

## Findings and limits

Unrestricted preprocessing reduced sparse bytes 9.2–47.7%; adaptive savings were
0–28.3%. It was slower on CPU (median slowdown 2.38x across point medians) and
worsened logical accuracy at some points. The strict policy had no observed
prediction disagreements, but smaller traffic gains and no CPU speedup.
This does not prove equivalence or generalize to other noise models/platforms.

Generic synthesis grew from 602 cells for X d=3 to 25,869 for X d=7. No physical
FPGA speed, power, target-mapped resources or clock closure was measured.
C_assumed queue scenarios are hypothetical sensitivity calculations. Full-window
lookahead and CPU serialization/downstream costs remain explicit.

## Run and inspect

```powershell
.\.venv\Scripts\python.exe -m qec_project demo --distance 3 --rounds 3 --p 0.005 --shots 1000 --seed 42
.\.venv\Scripts\python.exe scripts/reproduce.py --smoke --software-only
.\.venv\Scripts\python.exe scripts/reproduce.py
```

Open the [figures](evidence/M6/figures/communication.png),
[CSV](evidence/M6/study.csv), [failure table](evidence/M6/failure_cases.csv)
and [findings](evidence/M6/findings.json) without rerunning anything.
Hardware reproduction needs WSL Ubuntu and its installed tools. See the
[methods](../docs/research_methods.md) and [hardware instructions](../rtl/README.md).

## Follow-on research

Improve the confidence rule using saved failures and a prespecified accuracy
tolerance; validate on held-out settings; formally verify the protocol; share
or pipeline graph logic; implement a measured serializer and bounded feedback
interface; perform target timing closure or optional physical FPGA measurements.
These are future work, not results already demonstrated.
