"""Replay nonnegative stage services with unlimited storage; audit finite capacity.

Capacity violations mark the assumed schedule infeasible. Nothing is dropped.
"""
from collections import deque
import numpy as np


def replay(service_ns,period_ns,rounds,deadline_ns,capacity):
    services=np.asarray(service_ns,dtype=float)
    if services.ndim!=2 or not services.shape[0] or not services.shape[1] or not np.isfinite(services).all() or np.any(services<0):
        raise ValueError('finite nonnegative service matrix required')
    if period_ns<=0 or rounds<1 or deadline_ns<0 or capacity<1:
        raise ValueError('invalid arrival/deadline/capacity')
    ready=np.zeros(services.shape[1]);pending=[deque() for _ in ready]
    max_occupancy=np.zeros(len(ready),dtype=int);violations=0
    records=[];interval=period_ns*rounds
    for index,stages in enumerate(services):
        arrival=(index+1)*interval;time=arrival;wait=0.
        for stage,duration in enumerate(stages):
            while pending[stage] and pending[stage][0]<=time:pending[stage].popleft()
            occupancy=len(pending[stage])+1
            max_occupancy[stage]=max(max_occupancy[stage],occupancy)
            violations+=int(occupancy>capacity)
            start=max(time,ready[stage]);wait+=start-time
            time=start+duration;ready[stage]=time;pending[stage].append(time)
        records.append(dict(window_id=index,round_id=(index+1)*rounds-1,arrival_ns=arrival,
                            finish_ns=time,queue_wait_ns=wait,feedback_ns=time-index*interval))
    feedback=np.array([r['feedback_ns'] for r in records])
    return dict(records=records,deadline_misses=int((feedback>deadline_ns).sum()),
                latency_ns=np.percentile(feedback,[50,95,99]).tolist(),
                required_including_service_per_stage=max_occupancy.tolist(),
                capacity_violation_events=violations,assumed_capacity=capacity,drops=0,
                backlog_at_last_arrival=sum(r['finish_ns']>len(services)*interval for r in records))
