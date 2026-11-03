"""Paired study with persisted samples, actual byte serialization and timing scopes."""
import copy
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
from time import perf_counter_ns, process_time_ns

import numpy as np
import pymatching
from .__main__ import write_manifest
from .baseline import generate, wilson
from .config import load_config
from .encoding import encode
from .predecoder import edges_from_dem,predecode,predecode_batch
from .statistics import paired_interval,exact_interval


def timing(function):
    start = perf_counter_ns()
    result = function()
    return result,perf_counter_ns()-start


def load_study(path):
    spec = json.loads(Path(path).read_text())
    required = {'base_config','distances','bases','probabilities','round_multipliers',
                'shots','seed','timing_shots','timing_trials','single_shots','event_limits',
                'arrival_periods_ns','bandwidths_bits_per_second','deadline_ns',
                'queue_capacity_windows','rtl_clock_period_ns_assumed'}
    if set(spec) != required:
        raise ValueError('research config fields do not match schema')
    for key in ('shots','timing_shots','timing_trials','single_shots','deadline_ns','queue_capacity_windows','rtl_clock_period_ns_assumed'):
        if type(spec[key]) is not int or spec[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    for key in ('distances','bases','probabilities','round_multipliers','event_limits','arrival_periods_ns','bandwidths_bits_per_second'):
        if not isinstance(spec[key],list) or not spec[key]:
            raise ValueError(f'{key} must be a nonempty list')
    if any(type(d) is not int or d<3 or d%2!=1 for d in spec['distances']):
        raise ValueError('odd distance >=3 required')
    if any(b not in ('X','Z') for b in spec['bases']):
        raise ValueError('basis must be X or Z')
    if any(type(p) not in (int,float) or not 0<=p<=1 for p in spec['probabilities']):
        raise ValueError('invalid probability')
    for key in ('round_multipliers','arrival_periods_ns','bandwidths_bits_per_second'):
        if any(type(v) is not int or v<1 for v in spec[key]):
            raise ValueError(f'invalid {key}')
    if type(spec['seed']) is not int or not 0<=spec['seed']<2**63:
        raise ValueError('invalid study seed')
    if any(limit is not None and (type(limit) is not int or limit<0) for limit in spec['event_limits']):
        raise ValueError('invalid event limit')
    return spec


def describe_ns(values):
    return dict(zip(('p50','p95','p99'),np.percentile(values,[50,95,99]).tolist()))


def write_csv(rows,output):
    manifest=json.loads((output/'manifest.json').read_text())
    flattened=[]
    for row in rows:
        flat={key:value for key,value in row.items() if not isinstance(value,(dict,list,tuple))}
        for name in ('baseline_ci','hybrid_ci','paired_delta_ci'):
            flat[name+'_low'],flat[name+'_high']=row[name]
        for scope in ('batch_per_window_ns','single_window_ns'):
            for component,percentiles in row[scope].items():
                for quantile,value in percentiles.items():flat[f'{scope}_{component}_{quantile}']=value
        flat.update(python_version=manifest['python'],os=manifest['os'],cpu=manifest['cpu_identifier'],
                    source_commit=manifest['git']['commit'])
        for name,version in manifest['versions'].items():flat['version_'+name]=version
        flattened.append(flat)
    with (output/'study.csv').open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=flattened[0].keys());writer.writeheader();writer.writerows(flattened)


def study_point(config,spec,directory):
    directory.mkdir(parents=True)
    begin, cpu_begin = perf_counter_ns(),process_time_ns()
    circuit = generate(config)
    dem = circuit.detector_error_model(decompose_errors=True)
    matching, setup_ns = timing(lambda:pymatching.Matching.from_detector_error_model(dem))
    edges,graph_ns = timing(lambda:edges_from_dem(dem))
    (detectors,actual),sample_ns = timing(lambda:circuit.compile_detector_sampler(seed=config['seed']).sample(config['shots'],separate_observables=True))
    baseline = matching.decode_batch(detectors)
    failed_a = np.any(baseline!=actual,axis=1)
    n = len(detectors)
    zeros = np.zeros(circuit.num_observables,dtype=bool)
    for name,content in [('circuit.stim',str(circuit)),('model.dem',str(dem)),('config.json',json.dumps(config,indent=2))]:
        (directory/name).write_text(content,encoding='utf-8')
    np.savez_compressed(directory/'samples.npz',detectors=detectors,actual=actual,predicted=baseline)
    # Actual byte objects are constructed, not inferred from residual event counts.
    dense_a = np.empty(n,dtype=np.int64); sparse_a = np.empty(n,dtype=np.int64)
    serialization_start = perf_counter_ns()
    for i,shot in enumerate(detectors):
        dense_a[i] = len(encode(shot,zeros,i,config['rounds']-1,False))
        sparse_a[i] = len(encode(shot,zeros,i,config['rounds']-1,True))
    serialization_a_ns = perf_counter_ns()-serialization_start
    results = []
    for limit in spec['event_limits']:
        label = 'isolated' if limit is None else f'max{limit}'
        residual,frames = predecode_batch(detectors,edges,circuit.num_observables,limit)
        hybrid = matching.decode_batch(residual)^frames
        failed_b = np.any(hybrid!=actual,axis=1)
        # Production batch kernel must agree with scalar golden reference on real data.
        for index in range(min(100,n)):
            s = detectors[index]
            r,f,_ = predecode(s,edges,circuit.num_observables) if limit is None or s.sum()<=limit else (s,zeros,[])
            if not np.array_equal(r,residual[index]) or not np.array_equal(f,frames[index]):
                raise RuntimeError('batch/scalar mismatch')
        sparse_b = np.empty(n,dtype=np.int64)
        serialization_start = perf_counter_ns()
        for i,shot in enumerate(residual):
            sparse_b[i] = len(encode(shot,frames[i],i,config['rounds']-1,True))
        serialization_b_ns = perf_counter_ns()-serialization_start
        count = min(spec['timing_shots'],n)
        small = detectors[:count]
        matching.decode_batch(small)
        warm_r,_ = predecode_batch(small,edges,circuit.num_observables,limit)
        matching.decode_batch(warm_r)
        trials = []
        for trial in range(spec['timing_trials']):
            # Alternate A/B order to reduce systematic order/thermal bias.
            if trial%2==0:
                _,a_ns = timing(lambda:matching.decode_batch(small))
            (r,f),pre_ns = timing(lambda:predecode_batch(small,edges,circuit.num_observables,limit))
            _,mwpm_ns = timing(lambda:matching.decode_batch(r)^f)
            if trial%2:
                _,a_ns = timing(lambda:matching.decode_batch(small))
            trials.append(dict(baseline_ns=a_ns/count,predecode_ns=pre_ns/count,residual_decode_ns=mwpm_ns/count,total_hybrid_ns=(pre_ns+mwpm_ns)/count))
        single = []
        for i,s in enumerate(detectors[:min(n,spec['single_shots'])]):
            def execute_a():
                payload = encode(s,zeros,i,config['rounds']-1,True)
                prediction = matching.decode(s)
                return payload,prediction
            def execute_b():
                r,f,_ = predecode(s,edges,circuit.num_observables) if limit is None or s.sum()<=limit else (s,zeros,[])
                payload = encode(r,f,i,config['rounds']-1,True)
                prediction = matching.decode(r)^f
                return payload,prediction
            if i%2==0:
                _,a_ns = timing(execute_a); _,b_ns = timing(execute_b)
            else:
                _,b_ns = timing(execute_b); _,a_ns = timing(execute_a)
            single.append([a_ns,b_ns])
        a_only = int((failed_a & ~failed_b).sum()); b_only = int((failed_b & ~failed_a).sum())
        row = dict(basis=config['basis'],distance=config['distance'],rounds=config['rounds'],
            p=config['noise']['after_clifford_depolarization'],seed=config['seed'],shots=n,mode=label,
            detectors=circuit.num_detectors,edges=len(edges),baseline_failures=int(failed_a.sum()),
            hybrid_failures=int(failed_b.sum()),baseline_ci=wilson(int(failed_a.sum()),n),hybrid_ci=wilson(int(failed_b.sum()),n),
            baseline_only=a_only,hybrid_only=b_only,paired_delta=(b_only-a_only)/n,
            paired_delta_ci=paired_interval(a_only,b_only,n),
            zero_failure_upper_bound_a=exact_interval(0,n)[1] if not failed_a.any() else None,
            zero_failure_upper_bound_b=exact_interval(0,n)[1] if not failed_b.any() else None,
            original_events=int(detectors.sum()),residual_events=int(residual.sum()),
            dense_bytes=int(dense_a.sum()),sparse_baseline_bytes=int(sparse_a.sum()),sparse_hybrid_bytes=int(sparse_b.sum()),
            adaptive_baseline_bytes=int(np.minimum(dense_a,sparse_a).sum()+n),
            adaptive_hybrid_bytes=int(np.minimum(dense_a,sparse_b).sum()+n),
            adaptive_encoding_note='One format tag byte plus shorter of the two actually serialized records',
            serialize_baseline_dense_and_sparse_ns=serialization_a_ns,serialize_hybrid_sparse_ns=serialization_b_ns,
            setup_ns=setup_ns,graph_ns=graph_ns,sampling_ns=sample_ns,batch_timing_shots=count,trials=trials,
            batch_per_window_ns={key:describe_ns([t[key] for t in trials]) for key in trials[0]},
            single_window_ns={'A':describe_ns(np.array(single)[:,0]),'B_scalar':describe_ns(np.array(single)[:,1])},
            single_window_samples=len(single),
            timing_scope='Batch amortized: excludes sampling/setup/serialization. Individual windows: scalar predecode+serialize+decode; excludes sampling/transport/queue.',
            circuit_sha256=hashlib.sha256(str(circuit).encode()).hexdigest(),dem_sha256=hashlib.sha256(str(dem).encode()).hexdigest())
        wrong = np.flatnonzero(failed_b & ~failed_a)[:5]
        np.savez_compressed(directory/f'{label}.npz',residual=residual,frames=frames,predicted=hybrid,
                            sparse_bytes=sparse_b,single_timing_ns=np.array(single),failure_indices=wrong)
        (directory/f'{label}.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
        results.append(row)
    (directory/'resources.json').write_text(json.dumps(dict(elapsed_ns=perf_counter_ns()-begin,process_cpu_ns=process_time_ns()-cpu_begin,
        input_array_bytes=int(detectors.nbytes+actual.nbytes),note='Array size is not total process memory'),indent=2))
    return results


def run_study(config_path):
    spec = load_study(config_path)
    base = load_config(spec['base_config'])
    manifest = write_manifest(base)
    output = manifest.parent
    data = json.loads(manifest.read_text())
    data.update(mode='research_study',simulation_performed=True,study=spec,status='running',
                cpu_identifier=os.environ.get('PROCESSOR_IDENTIFIER',platform.processor()),logical_cpus=os.cpu_count(),
                timing_environment='Windows CPU; shared laptop; not pinned or isolated')
    manifest.write_text(json.dumps(data,indent=2),encoding='utf-8')
    grid = list(itertools.product(spec['bases'],spec['distances'],spec['round_multipliers'],spec['probabilities']))
    rows = []
    for index,(basis,distance,multiplier,p) in enumerate(grid):
        config = copy.deepcopy(base)
        config.update(basis=basis,distance=distance,rounds=distance*multiplier,
                      shots=spec['shots'],seed=spec['seed']+index*104729)
        config['noise'] = dict.fromkeys(base['noise'],p)
        rows.extend(study_point(config,spec,output/f'point-{index:02}'))
        (output/'study.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        print(f'{index+1}/{len(grid)} {basis} d={distance} rounds={config["rounds"]} p={p} A/B failures: '+
              ', '.join(f'{r["mode"]} {r["baseline_failures"]}/{r["hybrid_failures"]}' for r in rows[-len(spec['event_limits']):]),flush=True)
    write_csv(rows,output)
    from .research_plots import plots
    hardware = Path('reports/evidence/M5/summary.json')
    if hardware.exists():
        (output/'hardware_summary.json').write_text(hardware.read_text(),encoding='utf-8')
    plots(output)
    data['status'] = 'complete'
    manifest.write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(f'Study outputs: {output}',flush=True)
    return output
