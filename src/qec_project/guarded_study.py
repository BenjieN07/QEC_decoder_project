"""F1 fixed candidate, fresh paired samples and predeclared decision criteria."""
import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import numpy as np
import pymatching
from .__main__ import write_manifest
from .baseline import generate,wilson
from .config import load_config
from .encoding import encode_adaptive
from .guarded import compile_guarded,guarded_batch,guarded_scalar
from .predecoder import edges_from_dem,predecode_batch
from .research import timing
from .statistics import paired_interval


def load_plan(path):
    spec=json.loads(Path(path).read_text())
    # F1 is a registered experiment, not an open hyperparameter sweep.
    frozen=json.loads((Path(__file__).resolve().parents[2]/'configs/guarded.json').read_text())
    if spec!=frozen:raise ValueError('F1 requires the frozen configs/guarded.json plan; register a new study for changes')
    return spec


def audit_development(output,spec):
    cases=json.loads(Path('reports/evidence/M6/failure_cases.json').read_text())
    cache={};rows=[]
    for case in cases:
        key=case['point']
        if key not in cache:
            config=json.loads((Path('reports/evidence/M6/point-configs')/(key+'.json')).read_text())
            circuit=generate(config);dem=circuit.detector_error_model(decompose_errors=True)
            cache[key]=(dem,compile_guarded(dem,spec['guard_hops'],spec['boundary_odds_margin'])[0])
        dem,edges=cache[key]
        syndrome=np.zeros(dem.num_detectors,dtype=bool);syndrome[case['fired_detectors']]=True
        _,_,chosen=guarded_scalar(syndrome,edges,dem.num_observables)
        old={tuple(e) for e in case['chosen_edges']};new=set(chosen)
        rows.append(dict(point=key,shot=case['shot'],old_pairs=len(old),retained_old_pairs=len(old&new),
                         guarded_pairs=len(chosen)))
    result=dict(cases=len(rows),old_pairs=sum(r['old_pairs'] for r in rows),
                retained_old_pairs=sum(r['retained_old_pairs'] for r in rows),
                cases_no_guarded_decision=sum(r['guarded_pairs']==0 for r in rows),records=rows,
                scope='Selected M6 B-only failures used for development; not an unbiased safety estimate')
    (output/'development_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result


def run_plan(path,smoke=False):
    spec=load_plan(path);base=load_config(spec['base_config'])
    manifest=write_manifest(base);output=manifest.parent
    meta=json.loads(manifest.read_text());registration=Path('docs/F1_preregistration.md')
    meta.update(mode='F1_smoke' if smoke else 'F1_heldout',simulation_performed=True,status='running',plan=spec,
                preregistration_sha256=hashlib.sha256(registration.read_bytes()).hexdigest(),
                config_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                new_rule_has_no_RTL=True)
    manifest.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    audit=audit_development(output,spec)
    if smoke:
        grid=[('smoke',b,3,3,.005,500,991100+i) for i,b in enumerate(('X','Z'))]
    else:
        grid=[]
        for index,(basis,distance,p) in enumerate(itertools.product(spec['primary_bases'],spec['primary_distances'],spec['primary_probabilities'])):
            grid.append(('primary',basis,distance,distance,p,spec['primary_shots'],spec['seed']+index*104729))
        for index,(basis,distance) in enumerate(itertools.product(('X','Z'),(5,7))):
            grid.append(('stress',basis,distance,2*distance,.007,spec['stress_shots'],spec['seed']+10000000+index*104729))
        for index,basis in enumerate(('X','Z')):
            grid.append(('noiseless',basis,3,3,0.,spec['control_shots'],spec['seed']+20000000+index*104729))
    results=[]
    primary_count=len(spec['primary_bases'])*len(spec['primary_distances'])*len(spec['primary_probabilities'])
    for index,(role,basis,distance,rounds,p,shots,seed) in enumerate(grid):
        point=output/f'point-{index:02}';point.mkdir()
        config=copy.deepcopy(base);config.update(basis=basis,distance=distance,rounds=rounds,shots=shots,seed=seed)
        config['noise']=dict.fromkeys(config['noise'],p)
        circuit=generate(config);dem=circuit.detector_error_model(decompose_errors=True)
        matching=pymatching.Matching.from_detector_error_model(dem)
        (compiled,diagnostics),compile_ns=timing(lambda:compile_guarded(dem,spec['guard_hops'],spec['boundary_odds_margin']))
        old_edges=edges_from_dem(dem)
        syndrome,actual=circuit.compile_detector_sampler(seed=seed).sample(shots,separate_observables=True)
        baseline=matching.decode_batch(syndrome);a_wrong=np.any(baseline!=actual,axis=1)
        zeros=np.zeros(dem.num_observables,dtype=bool)
        base_bytes=sum(len(encode_adaptive(s,zeros,i,rounds-1)) for i,s in enumerate(syndrome))
        np.savez_compressed(point/'samples.npz',detectors=syndrome,actual=actual,predicted=baseline)
        for filename,content in [('config.json',json.dumps(config,indent=2)),('circuit.stim',str(circuit)),('model.dem',str(dem))]:
            (point/filename).write_text(content,encoding='utf-8')
        edge_info=[dict(a=e.a,b=e.b,mask=e.mask,guard=e.guard,
                        boundary_margin=e.boundary_margin if math.isfinite(e.boundary_margin) else None) for e in compiled]
        (point/'guarded_edges.json').write_text(json.dumps(dict(diagnostics=diagnostics,edges=edge_info),indent=2),encoding='utf-8')
        variants={
            'isolated':lambda data:predecode_batch(data,old_edges,dem.num_observables),
            'max2':lambda data:predecode_batch(data,old_edges,dem.num_observables,event_limit=2),
            'guarded':lambda data:guarded_batch(data,compiled,dem.num_observables)}
        point_rows=[]
        for name,preprocess in variants.items():
            residual,frame=preprocess(syndrome)
            predicted=matching.decode_batch(residual)^frame
            if name=='guarded':
                for i in range(min(100,shots)):
                    r,f,_=guarded_scalar(syndrome[i],compiled,dem.num_observables)
                    if not np.array_equal(r,residual[i]) or not np.array_equal(f,frame[i]):raise RuntimeError('guarded batch/scalar mismatch')
            wrong=np.any(predicted!=actual,axis=1)
            a_only=int((a_wrong & ~wrong).sum());b_only=int((wrong & ~a_wrong).sum())
            alpha=spec['family_alpha']/primary_count if role=='primary' else .05
            interval=paired_interval(a_only,b_only,shots,alpha)
            outgoing=sum(len(encode_adaptive(s,frame[i],i,rounds-1)) for i,s in enumerate(residual))
            small=syndrome[:min(shots,spec['timing_shots'])]
            r,f=preprocess(small);matching.decode_batch(small);matching.decode_batch(r)
            trials=[]
            for trial in range(3 if smoke else spec['timing_trials']):
                if trial%2==0:_,a_ns=timing(lambda:matching.decode_batch(small))
                (r,f),pre_ns=timing(lambda:preprocess(small))
                _,residual_ns=timing(lambda:matching.decode_batch(r)^f)
                if trial%2:_,a_ns=timing(lambda:matching.decode_batch(small))
                trials.append(dict(baseline_ns=a_ns,predecode_ns=pre_ns,residual_decode_ns=residual_ns,
                                   total_hybrid_ns=pre_ns+residual_ns))
            medians={key:float(np.median([t[key] for t in trials]))/len(small) for key in trials[0]}
            row=dict(point=point.name,role=role,basis=basis,distance=distance,rounds=rounds,p=p,shots=shots,seed=seed,
                decoder=name,baseline_failures=int(a_wrong.sum()),hybrid_failures=int(wrong.sum()),
                baseline_ci=wilson(int(a_wrong.sum()),shots),hybrid_ci=wilson(int(wrong.sum()),shots),
                A_only=a_only,B_only=b_only,paired_delta=(b_only-a_only)/shots,paired_ci=interval,interval_alpha=alpha,
                accuracy_margin=spec['accuracy_margin'],accuracy_pass=bool(interval[1]<=spec['accuracy_margin']),
                adaptive_baseline_bytes=base_bytes,adaptive_hybrid_bytes=outgoing,adaptive_reduction=1-outgoing/base_bytes,
                original_events=int(syndrome.sum()),residual_events=int(residual.sum()),compile_guard_ns=compile_ns,
                compile_diagnostics=diagnostics if name=='guarded' else None,timing_trials=trials,timing_shots=len(small),
                median_batch_ns_per_shot=medians,timing_scope='Warm alternating batches; sampling/graph compile/serialization excluded',
                circuit_sha256=hashlib.sha256(str(circuit).encode()).hexdigest(),dem_sha256=hashlib.sha256(str(dem).encode()).hexdigest())
            np.savez_compressed(point/f'{name}.npz',residual=residual,frames=frame,predicted=predicted,
                                B_only_indices=np.flatnonzero(wrong & ~a_wrong))
            results.append(row);point_rows.append(row)
        (point/'summary.json').write_text(json.dumps(point_rows,indent=2),encoding='utf-8')
        (output/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(f'{index+1}/{len(grid)} {role} {basis} d={distance} rounds={rounds} p={p} A={int(a_wrong.sum())}: '+
              ', '.join(f'{r["decoder"]} B={r["hybrid_failures"]} bytes={100*r["adaptive_reduction"]:.2f}%' for r in point_rows),flush=True)
    primary=[r for r in results if r['role']=='primary' and r['decoder']=='guarded']
    accuracy=bool(primary) and all(r['accuracy_pass'] for r in primary)
    communication=bool(primary) and any(r['adaptive_reduction']>=spec['minimum_adaptive_reduction'] for r in primary)
    verdict=dict(smoke=smoke,primary_points=len(primary),accuracy_all_primary_pass=accuracy,
                 communication_any_primary_pass=communication,promote=accuracy and communication,
                 tolerance=spec['accuracy_margin'],minimum_adaptive_reduction=spec['minimum_adaptive_reduction'],
                 development_audit={k:v for k,v in audit.items() if k!='records'},
                 interpretation='Smoke is pipeline validation only' if smoke else 'Frozen F1 rule; no post-evaluation threshold tuning')
    (output/'verdict.json').write_text(json.dumps(verdict,indent=2),encoding='utf-8')
    from .guarded_plots import plot_results
    plot_results(output)
    meta['status']='complete';manifest.write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps(verdict,indent=2),flush=True);print(f'F1 outputs: {output}',flush=True)
    return output
