"""Archive compact evidence and generate auditable failure traces and findings."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import hashlib
import numpy as np
import stim
from qec_project.predecoder import edges_from_dem,predecode


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('study',type=Path);parser.add_argument('controls',type=Path)
    parser.add_argument('--output',type=Path,default=Path('reports/evidence/M6'))
    args=parser.parse_args();source=args.study;target=args.output
    target.mkdir(parents=True,exist_ok=True)
    rows=json.loads((source/'study.json').read_text())
    controls=json.loads((args.controls/'study.json').read_text())
    for filename in ('study.json','study.csv','manifest.json','hardware_summary.json','queue_summary.json'):
        shutil.copy2(source/filename,target/filename)
    shutil.copytree(source/'figures',target/'figures',dirs_exist_ok=True)
    if (source/'rtl-evidence').exists():
        shutil.copytree(source/'rtl-evidence',target/'rtl',dirs_exist_ok=True)
    (target/'controls').mkdir(exist_ok=True)
    for filename in ('study.json','study.csv','manifest.json'):
        shutil.copy2(args.controls/filename,target/'controls'/filename)
    cases=[]
    for point in sorted(source.glob('point-*')):
        config=json.loads((point/'config.json').read_text())
        (target/'point-configs').mkdir(exist_ok=True)
        shutil.copy2(point/'config.json',target/'point-configs'/f'{point.name}.json')
        independent=point/'sinter_independent.json'
        if independent.exists():shutil.copy2(independent,target/f'{point.name}-sinter.json')
        samples=np.load(point/'samples.npz');hybrid=np.load(point/'isolated.npz')
        dem=stim.DetectorErrorModel.from_file(point/'model.dem');edges=edges_from_dem(dem)
        for index in hybrid['failure_indices'][:3]:
            s=samples['detectors'][index]
            residual,frame,decisions=predecode(s,edges,dem.num_observables)
            cases.append(dict(point=point.name,shot=int(index),basis=config['basis'],distance=config['distance'],
                rounds=config['rounds'],p=config['noise']['after_clifford_depolarization'],
                fired_detectors=np.flatnonzero(s).tolist(),residual_detectors=np.flatnonzero(residual).tolist(),
                chosen_edges=decisions,frame=frame.tolist(),true_observable=samples['actual'][index].tolist(),
                A_prediction=samples['predicted'][index].tolist(),B_prediction=hybrid['predicted'][index].tolist()))
    (target/'failure_cases.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    with (target/'failure_cases.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=list(cases[0]) if cases else ['point'])
        writer.writeheader();writer.writerows(cases)
    modes=sorted({r['mode'] for r in rows})
    findings=dict(study_source=str(source),controls_source=str(args.controls),main_points=len(rows)//len(modes),
                  main_shots=sum(r['shots'] for r in rows if r['mode']=='isolated'),
                  controls_shots=sum(r['shots'] for r in controls if r['mode']=='isolated'),modes={})
    for mode in modes:
        selected=[r for r in rows if r['mode']==mode]
        ratios=[r['batch_per_window_ns']['total_hybrid_ns']['p50']/r['batch_per_window_ns']['baseline_ns']['p50'] for r in selected]
        findings['modes'][mode]=dict(baseline_failures=sum(r['baseline_failures'] for r in selected),
            hybrid_failures=sum(r['hybrid_failures'] for r in selected),A_only=sum(r['baseline_only'] for r in selected),
            B_only=sum(r['hybrid_only'] for r in selected),points_positive_paired_interval=sum(r['paired_delta_ci'][0]>0 for r in selected),
            batch_slowdown_median=float(np.median(ratios)),batch_slowdown_range=[min(ratios),max(ratios)],
            sparse_reduction_range=[min(1-r['sparse_hybrid_bytes']/r['sparse_baseline_bytes'] for r in selected),max(1-r['sparse_hybrid_bytes']/r['sparse_baseline_bytes'] for r in selected)],
            adaptive_reduction_range=[min(1-r['adaptive_hybrid_bytes']/r['adaptive_baseline_bytes'] for r in selected),max(1-r['adaptive_hybrid_bytes']/r['adaptive_baseline_bytes'] for r in selected)])
    examples=[]
    for row in rows:
        if row['basis']=='X' and row['rounds']==row['distance'] and row['p']==.005:
            examples.append({key:row[key] for key in ('distance','mode','shots','baseline_failures','hybrid_failures',
                'baseline_ci','hybrid_ci','paired_delta','paired_delta_ci','baseline_only','hybrid_only',
                'original_events','residual_events','dense_bytes','sparse_baseline_bytes','sparse_hybrid_bytes',
                'adaptive_baseline_bytes','adaptive_hybrid_bytes','batch_per_window_ns','single_window_ns')})
    findings['examples']=examples
    (target/'findings.json').write_text(json.dumps(findings,indent=2),encoding='utf-8')
    sources=list(Path('src/qec_project').glob('*.py'))+list(Path('scripts').glob('*.py'))+[Path('rtl/tb/verify_predecoder.py')]
    (target/'analysis_source_hashes.json').write_text(json.dumps({str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},indent=2))
    print(json.dumps({k:v for k,v in findings.items() if k!='examples'},indent=2))


if __name__=='__main__':main()
