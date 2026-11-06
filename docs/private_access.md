# Private IBM Quantum access

Keep api.txt and crn.txt local in the repository root. Do not paste their contents
into source, reports, issue messages, terminal commands, notebooks or chat.
The IBM client reads them into memory and never calls save_account. SDK output
and raw exceptions are suppressed; public JSON uses a strict account-data check.
Private job identifiers and full prepared circuits remain under ignored private/.

Protected paths include api.txt, crn.txt, .env files, credentials/, secrets/,
private/ and .qiskit/. The version-controlled pre-commit hook checks protected
tracked paths, the staged tree and normal local/remote branch history for exact
credential values and common URL encodings. Activate it on another checkout with:

```text
git config --local core.hooksPath .githooks
python scripts/check_secrets.py --history
```

The hook was enabled on this checkout. It blocks commits when it finds local
credential contents. If local credential files are absent, it can check protected
paths but cannot know unknown secret values. It is a practical safeguard, not a
universal detector for encrypted/compressed or unrelated credentials.

Initial audit also found credential blobs in a local Codex capture reference
created before the ignore rules were added. Normal branch histories and
origin/main passed the exact-value scan, and credential paths were not tracked.
Those app snapshot refs are not part of the explicitly pushed main branch.
Do not use git push --mirror or push app-managed refs. The optional --all-local
scanner includes those private local refs and therefore reports their copies.
No history rewrite or app snapshot deletion was performed.

## Hardware meaning and commands

These credentials access IBM quantum processors, not FPGA boards. Physical board
ownership is not needed. FPGA work remains local RTL simulation/synthesis; the
remote QPU provides actual circuit measurements for offline decoder evaluation.

Install the optional client in the project environment:
```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,research,ibm]'
.\.venv\Scripts\python.exe -m qec_project.ibm_access probe
.\.venv\Scripts\python.exe -m qec_project.ibm_experiment prepare
```

Probe and prepare submit no jobs. Preparation prints a private run directory.
It validates compact 17-qubit d=3, three-round X/Z memory circuits and the fully
routed ideal circuits. It preserves all 33 chronological measurement bits and
uses Stim's own measurement-to-detector/observable converter. The QPU itself
supplies physical noise; synthetic noise gates are not sent to it.

Explicit submission and result retrieval:
```powershell
.\.venv\Scripts\python.exe -m qec_project.ibm_experiment submit --run PRIVATE_RUN_DIRECTORY
.\.venv\Scripts\python.exe -m qec_project.ibm_experiment fetch --run PRIVATE_RUN_DIRECTORY
```

Submission is restricted to the explicitly supplied Open/free instance, confirmed
allocation, d=3/three rounds, two bases, at most 512 shots each and at most 60
execution seconds, with a quota reserve. Paid-plan fallback is refused. Existing
job records block duplicate submission; fetch does not submit another job.
The job may queue for external scheduling. Runtime execution caps do not bound
queue waiting time. No account plans or billing settings are changed.

The routed circuit adds gates and idle exposure, and the starting decoder prior
is synthetic and uncalibrated. Poor logical accuracy is plausible. Results must
not be described as demonstrating real-time correction, FPGA execution, a
threshold, or a hardware speedup. A short pilot validates access and the data
path before deciding whether to spend more allocation.

Official references: [IBM service setup](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/qiskit-runtime-service),
[dynamic circuits](https://quantum.cloud.ibm.com/docs/en/guides/execute-dynamic-circuits),
[SamplerV2](https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/sampler-v2),
[plan allocation](https://quantum.cloud.ibm.com/docs/en/guides/plans-overview).
