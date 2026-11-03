"""Measured CPU workload on saved M1 shots; no hardware timing inference."""
import json
from pathlib import Path
from time import perf_counter_ns
import numpy as np
import pymatching
import stim


def encoded_bytes(events, detector_count, observables=1):
    # Both formats: uint64 window id, uint32 round id, uint32 payload count,
    # then payload and byte-rounded logical frame. Sparse indices are uint32.
    common = 16 + (observables+7)//8
    return common + (detector_count+7)//8, common + 4*events


def benchmark(directory):
    directory = Path(directory)
    data = np.load(directory/'samples.npz')
    detectors = data['detectors']
    start = perf_counter_ns()
    matching = pymatching.Matching.from_detector_error_model(
        stim.DetectorErrorModel.from_file(directory/'model.dem'))
    setup = perf_counter_ns()-start
    matching.decode_batch(detectors[:min(100, len(detectors))])
    batch = []
    for _ in range(10):
        start = perf_counter_ns()
        prediction = matching.decode_batch(detectors)
        batch.append(perf_counter_ns()-start)
    if not np.array_equal(prediction, data['predicted']):
        raise ValueError('replay predictions differ')
    single = []
    for shot in detectors:
        start = perf_counter_ns()
        matching.decode(shot)
        single.append(perf_counter_ns()-start)
    counts = detectors.sum(axis=1)
    dense, sparse = encoded_bytes(counts, detectors.shape[1], prediction.shape[1])
    result = dict(setup_ns=setup, batch_trials=10, shots=len(detectors),
                  batch_ns=batch, batch_shots_per_second=len(detectors)*1e9/np.median(batch),
                  single_decode_ns=dict(zip(['p50','p95','p99'], np.percentile(single,[50,95,99]).tolist())),
                  detector_count=detectors.shape[1], mean_events=float(counts.mean()),
                  event_count_percentiles=np.percentile(counts,[50,95,99]).tolist(),
                  dense_bytes_per_window=int(dense), mean_sparse_bytes=float(np.mean(sparse)),
                  numpy_payload_bytes=int(detectors.nbytes+data['actual'].nbytes),
                  timing_scope='CPU decode only; sampling, setup, I/O excluded; not feedback latency')
    (directory/'workload.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.hist(counts, bins=range(int(counts.max())+2), align='left')
    ax.set(xlabel='Firing detector events per complete window', ylabel='Shots')
    fig.tight_layout(); fig.savefig(directory/'event_density.png'); plt.close(fig)
    print(json.dumps(result,indent=2))
    return result
