"""Save decoding-graph weights, boundaries and explicit local eligibility."""
import argparse
import json
from pathlib import Path
import pymatching
import stim
from qec_project.predecoder import edges_from_dem

parser=argparse.ArgumentParser();parser.add_argument('study',type=Path)
args=parser.parse_args()
for point in sorted(args.study.glob('point-*')):
    dem=stim.DetectorErrorModel.from_file(point/'model.dem')
    admissible=edges_from_dem(dem)
    rows=[]
    for a,b,attributes in pymatching.Matching.from_detector_error_model(dem).edges():
        rows.append(dict(a=a,b=b,boundary=b is None,weight=attributes['weight'],
                         error_probability=attributes['error_probability'],logical_fault_ids=sorted(attributes['fault_ids'])))
    (point/'graph.json').write_text(json.dumps(dict(matching_edges=rows,admissible_local_edges=admissible,
        note='Matching graph includes decomposed mechanisms; local eligibility uses only unambiguous whole two-detector mechanisms'),indent=2),encoding='utf-8')
print('Graph audits saved')
