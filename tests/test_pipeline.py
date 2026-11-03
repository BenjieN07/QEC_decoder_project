import pytest
from qec_project.pipeline import queue_model


def test_stable_pipeline():
    result = queue_model([2,3],10,1,windows=5,deadline_ns=15)
    assert result['deadline_misses'] == 0
    assert result['max_inflight_before_arrival'] == 0
    assert all(r['feedback_from_window_start_ns']==15 for r in result['records'])


def test_backlog_and_context():
    result = queue_model([20],10,1,windows=5,deadline_ns=30)
    assert result['deadline_misses'] == 4
    assert result['records'][-1]['queue_wait_ns']==40
    assert result['backlog_at_last_arrival'] > 0
    with pytest.raises(ValueError):
        queue_model([1],0,1)
