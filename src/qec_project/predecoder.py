"""Conservative isolated pair heuristic on whole graphlike DEM mechanisms.

Correlated decompositions and hyperedges are excluded from local corrections.
They remain in the downstream MWPM model. Boundaries are deliberately deferred.
"""
import json
from pathlib import Path
from time import perf_counter_ns
import numpy as np
import stim
import pymatching
from .baseline import wilson
from .workload import encoded_bytes


def edges_from_dem(dem):
    candidates = {}
    for instruction in dem.flattened():
        if instruction.type != 'error':
            continue
        targets = instruction.targets_copy()
        if any(t.is_separator() for t in targets):
            continue
        detectors = tuple(sorted(t.val for t in targets if t.is_relative_detector_id()))
        mask = sum(1 << t.val for t in targets if t.is_logical_observable_id())
        if len(detectors) == 2:
            candidates.setdefault(detectors, set()).add(mask)
    return [(a,b,next(iter(masks))) for (a,b),masks in sorted(candidates.items()) if len(masks)==1]


def predecode(syndrome, edges, observables):
    residual = np.array(syndrome, dtype=np.bool_, copy=True)
    frame = np.zeros(observables, dtype=np.bool_)
    active = [(a,b,mask) for a,b,mask in edges if syndrome[a] and syndrome[b]]
    degree = {}
    for a,b,_ in active:
        degree[a] = degree.get(a,0)+1
        degree[b] = degree.get(b,0)+1
    decisions = []
    for a,b,mask in active:
        if degree[a] == degree[b] == 1:
            residual[a] ^= True; residual[b] ^= True
            for bit in range(observables):
                frame[bit] ^= bool(mask & (1 << bit))
            decisions.append((a,b,mask))
    return residual, frame, decisions


def predecode_batch(syndromes, edges, observables, event_limit=None, chunk_size=4096):
    """Vectorized execution of exactly the scalar rule; chunking bounds workspace.

event_limit is an optional conservative whole-window fallback, not a new edge rule.
"""
    syndromes = np.asarray(syndromes,dtype=bool)
    if syndromes.ndim != 2 or chunk_size < 1 or observables < 0:
        raise ValueError('invalid batch shape, chunk size or observable count')
    if event_limit is not None and event_limit < 0:
        raise ValueError('event_limit must be nonnegative')
    residual = syndromes.copy()
    frames = np.zeros((len(syndromes),observables),dtype=bool)
    for start in range(0,len(syndromes),chunk_size):
        stop = min(start+chunk_size,len(syndromes))
        original = syndromes[start:stop].T
        degree = np.zeros(original.shape,dtype=np.int32)
        active = np.empty((len(edges),stop-start),dtype=bool)
        eligible = np.ones(stop-start,dtype=bool) if event_limit is None else original.sum(axis=0)<=event_limit
        for index,(a,b,_) in enumerate(edges):
            active[index] = original[a] & original[b] & eligible
            degree[a] += active[index]; degree[b] += active[index]
        output = original.copy()
        frame = np.zeros((observables,stop-start),dtype=bool)
        for index,(a,b,mask) in enumerate(edges):
            chosen = active[index] & (degree[a]==1) & (degree[b]==1)
            output[a] ^= chosen; output[b] ^= chosen
            for bit in range(observables):
                if mask & (1<<bit):
                    frame[bit] ^= chosen
        residual[start:stop] = output.T
        frames[start:stop] = frame.T
    return residual,frames


def compare(directory):
    directory = Path(directory)
    data = np.load(directory/'samples.npz')
    original, actual = data['detectors'], data['actual']
    dem = stim.DetectorErrorModel.from_file(directory/'model.dem')
    matching = pymatching.Matching.from_detector_error_model(dem)
    edges = edges_from_dem(dem)
    matching.decode_batch(original[:100])
    start = perf_counter_ns(); baseline = matching.decode_batch(original)
    baseline_ns = perf_counter_ns()-start
    residual = np.empty_like(original)
    frames = np.zeros_like(actual)
    decisions = []
    start = perf_counter_ns()
    for index, shot in enumerate(original):
        residual[index],frames[index],chosen = predecode(shot,edges,dem.num_observables)
        decisions.append(chosen)
    pre_ns = perf_counter_ns()-start
    start = perf_counter_ns()
    hybrid = matching.decode_batch(residual) ^ frames
    downstream_ns = perf_counter_ns()-start
    fail_a = np.any(baseline != actual,axis=1)
    fail_b = np.any(hybrid != actual,axis=1)
    original_count, residual_count = int(original.sum()), int(residual.sum())
    dense, sparse_a = encoded_bytes(original.sum(axis=1),dem.num_detectors,dem.num_observables)
    _, sparse_b = encoded_bytes(residual.sum(axis=1),dem.num_detectors,dem.num_observables)
    delta = fail_b.astype(float)-fail_a.astype(float)
    se = float(delta.std(ddof=1)/np.sqrt(len(delta))) if len(delta)>1 else 0.
    result = dict(shots=len(original), admissible_edges=len(edges),
                  baseline_failures=int(fail_a.sum()), hybrid_failures=int(fail_b.sum()),
                  baseline_ci=wilson(int(fail_a.sum()),len(original)),
                  hybrid_ci=wilson(int(fail_b.sum()),len(original)),
                  paired_failure_rate_delta=float(delta.mean()),
                  paired_delta_normal_95=[float(delta.mean()-1.96*se),float(delta.mean()+1.96*se)],
                  paired_interval_warning='Normal approximation; unreliable for few disagreements',
                  disagreement_probability_ci=wilson(int((fail_a != fail_b).sum()),len(original)),
                  baseline_only_failures=int((fail_a & ~fail_b).sum()),
                  hybrid_only_failures=int((fail_b & ~fail_a).sum()),
                  original_events=original_count,residual_events=residual_count,
                  event_reduction=None if original_count==0 else 1-residual_count/original_count,
                  dense_bytes_total=dense*len(original),
                  sparse_baseline_bytes_total=int(sparse_a.sum()),
                  sparse_hybrid_bytes_total=int(sparse_b.sum()),
                  baseline_decode_ns=baseline_ns,predecode_ns=pre_ns,
                  residual_decode_ns=downstream_ns,total_hybrid_ns=pre_ns+downstream_ns,
                  scope='offline batch; setup/sampling/serialization excluded; preliminary one trial')
    np.savez_compressed(directory/'hybrid.npz', residual=residual,frames=frames,predicted=hybrid)
    (directory/'decisions.json').write_text(json.dumps(decisions),encoding='utf-8')
    (directory/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
    return result
