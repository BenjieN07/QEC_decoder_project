"""Deterministic two-stage FIFO model, with no dropped windows."""
import json
from pathlib import Path
import numpy as np


def queue_model(service_ns, period_ns, rounds, windows=1000, deadline_ns=1000000):
    if period_ns <= 0 or rounds < 1 or windows < 1 or any(s < 0 for s in service_ns):
        raise ValueError('invalid schedule')
    stage_ready = [0.] * len(service_ns)
    records = []
    completions = []
    backlog = []
    interval = period_ns * rounds
    for window in range(windows):
        arrival = (window+1)*interval
        time = arrival
        queue_wait = 0.
        for stage, service in enumerate(service_ns):
            start = max(time, stage_ready[stage])
            queue_wait += start-time
            time = start+service
            stage_ready[stage] = time
        queued = sum(c > arrival for c in completions)
        backlog.append(queued)
        completions.append(time)
        records.append(dict(window_id=window,round_id=(window+1)*rounds-1,
                            arrival_ns=arrival,finish_ns=time,queue_wait_ns=queue_wait,
                            feedback_from_window_start_ns=time-window*interval))
    latency = [r['feedback_from_window_start_ns'] for r in records]
    return dict(records=records,max_inflight_before_arrival=max(backlog),
                deadline_misses=sum(t>deadline_ns for t in latency),
                latency_p50_p95_p99_ns=np.percentile(latency,[50,95,99]).tolist(),
                backlog_at_last_arrival=sum(c > windows*interval for c in completions),
                drops=0,capacity_policy='unbounded FIFO; reported occupancy guides future capacity')


def model(directory):
    directory = Path(directory)
    comparison = json.loads((directory/'comparison.json').read_text())
    config = json.loads((directory/'config.json').read_text())
    rows = []
    for period in (1000,10000,100000):
        for bandwidth in (1e8,1e9):
            for architecture in ('A','B'):
                shots = comparison['shots']
                byte_count = comparison['sparse_baseline_bytes_total' if architecture=='A' else 'sparse_hybrid_bytes_total']/shots
                transfer_ns = byte_count*8/bandwidth*1e9
                if architecture == 'A':
                    services = [transfer_ns,comparison['baseline_decode_ns']/shots]
                else:
                    services = [comparison['predecode_ns']/shots,transfer_ns,
                                comparison['residual_decode_ns']/shots]
                result = queue_model(services,period,config['rounds'])
                result.update(architecture=architecture,round_period_ns=period,
                              bandwidth_bits_per_second=bandwidth,service_ns=services)
                rows.append(result)
    (directory/'queue_model.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    for row in rows:
        if row['round_period_ns']==1000 and row['bandwidth_bits_per_second']==1e9:
            ax.plot([r['window_id'] for r in row['records']],
                    [r['feedback_from_window_start_ns']/1000 for r in row['records']],
                    label=row['architecture'])
    ax.set(xlabel='Complete memory window',ylabel='Modeled feedback latency (us)',
           title='Hypothetical 1 us/round, 1 Gbit/s; fixed CPU batch-average service')
    ax.legend(); fig.tight_layout(); fig.savefig(directory/'queue_model.png'); plt.close(fig)
    for row in rows:
        print(row['architecture'],row['round_period_ns'],row['bandwidth_bits_per_second'],
              'deadline misses:',row['deadline_misses'],'max inflight:',row['max_inflight_before_arrival'])
    return rows
