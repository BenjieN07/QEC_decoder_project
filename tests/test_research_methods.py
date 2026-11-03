import numpy as np
import pytest
from qec_project.encoding import encode,decode,encode_adaptive,decode_adaptive
from qec_project.workload import encoded_bytes
from qec_project.predecoder import predecode,predecode_batch
from qec_project.statistics import paired_interval


@pytest.mark.parametrize('sparse',[True,False])
def test_wire_roundtrip_and_byte_count(sparse):
    rng = np.random.default_rng(51)
    for detectors,observables in [(0,0),(24,1),(25,9),(336,2)]:
        s = rng.integers(0,2,detectors).astype(bool)
        f = rng.integers(0,2,observables).astype(bool)
        record = encode(s,f,123,7,sparse)
        w,r,received,frame = decode(record,detectors,observables,sparse)
        assert (w,r)==(123,7)
        assert np.array_equal(s,received) and np.array_equal(f,frame)
        dense,sparse_bytes = encoded_bytes(int(s.sum()),detectors,observables)
        assert len(record)==(sparse_bytes if sparse else dense)
        adaptive=encode_adaptive(s,f,123,7)
        assert len(adaptive)==1+min(dense,sparse_bytes)
        assert np.array_equal(decode_adaptive(adaptive,detectors,observables)[2],s)
        with pytest.raises(ValueError):
            decode(record+b'x',detectors,observables,sparse)


def test_batched_matches_scalar_and_fallback():
    rng = np.random.default_rng(12)
    edges = [(0,1,3),(1,2,1),(3,4,2),(5,6,1)]
    samples = rng.integers(0,2,(300,8)).astype(bool)
    for limit in (None,2):
        residual,frames = predecode_batch(samples,edges,2,limit,chunk_size=13)
        for i,s in enumerate(samples):
            r,f,_ = predecode(s,edges,2) if limit is None or s.sum()<=limit else (s,np.zeros(2,dtype=bool),[])
            assert np.array_equal(residual[i],r) and np.array_equal(frames[i],f)


def test_paired_zero_disagreement_is_not_zero_uncertainty():
    low,high = paired_interval(0,0,1000)
    assert low < 0 < high
    assert low == pytest.approx(-high)
    assert paired_interval(20,0,1000)[1] < 0


def test_research_config_rejects_bad_probabilities(tmp_path):
    import json
    from qec_project.research import load_study
    spec=load_study('configs/research-smoke.json')
    spec['probabilities']=[float('nan')]
    path=tmp_path/'bad.json';path.write_text(json.dumps(spec))
    with pytest.raises(ValueError):load_study(path)
