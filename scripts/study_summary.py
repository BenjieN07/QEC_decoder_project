"""Inspect measured outcomes without interpreting equal counts as equivalence."""
import argparse
import json
from pathlib import Path
import numpy as np

parser=argparse.ArgumentParser();parser.add_argument('study',type=Path)
args=parser.parse_args()
rows=json.loads((args.study/'study.json').read_text())
for mode in sorted({r['mode'] for r in rows}):
    group=[r for r in rows if r['mode']==mode]
    ratio=[r['batch_per_window_ns']['total_hybrid_ns']['p50']/r['batch_per_window_ns']['baseline_ns']['p50'] for r in group]
    print(mode,'points',len(group),'A failures',sum(r['baseline_failures'] for r in group),
          'B failures',sum(r['hybrid_failures'] for r in group),
          'B-only',sum(r['hybrid_only'] for r in group),'A-only',sum(r['baseline_only'] for r in group),
          'batch B/A median range',min(ratio),float(np.median(ratio)),max(ratio),
          'pointwise positive paired CI',sum(r['paired_delta_ci'][0]>0 for r in group))
for r in rows:
    if r['basis']=='X' and r['rounds']==r['distance'] and r['p']==.005:
        print(json.dumps(r,indent=2))
