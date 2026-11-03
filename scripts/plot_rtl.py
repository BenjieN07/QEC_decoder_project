import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

directory = Path('reports/evidence/M5')
rows = json.loads((directory/'summary.json').read_text())
fig, ax = plt.subplots()
labels = [f"{r['basis']}, d={r['distance']}\n{r['detectors']} detectors" for r in rows]
ax.bar(labels,[r['cells'] for r in rows])
ax.set(ylabel='Generic Yosys cells (includes registers)',
       title='Synthesized parallel predecoder — no target timing or FPGA mapping')
fig.tight_layout(); fig.savefig(directory/'generic_cells.png'); plt.close(fig)
