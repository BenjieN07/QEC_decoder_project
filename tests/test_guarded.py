import itertools
import numpy as np
import stim
from qec_project.guarded import compile_guarded,guarded_scalar,guarded_batch
from qec_project.statistics import paired_interval


def model():
    return stim.DetectorErrorModel('error(0.1) D0 D1 L0 L1\nerror(0.01) D1 D2\nerror(0.0001) D0\nerror(0.0001) D2')


def test_guard_blocks_nearby_event_and_preserves_frame():
    edges,_=compile_guarded(model())
    r,f,chosen=guarded_scalar(np.array([1,1,0],dtype=bool),edges,2)
    assert r.tolist()==[False,False,False] and f.tolist()==[True,True]
    assert chosen==[(0,1,3)]
    assert not guarded_scalar(np.ones(3),edges,2)[2]


def test_boundary_competition_is_rejected():
    dem=stim.DetectorErrorModel('error(0.01) D0 D1\nerror(0.2) D0\nerror(0.2) D1')
    assert compile_guarded(dem)[0]==[]


def test_all_syndromes_batch_scalar_and_reconstruction():
    edges,_=compile_guarded(model())
    samples=np.array(list(itertools.product([False,True],repeat=3)))
    residual,frames=guarded_batch(samples,edges,2,chunk_size=3)
    for i,s in enumerate(samples):
        r,f,decisions=guarded_scalar(s,edges,2)
        assert np.array_equal(r,residual[i]) and np.array_equal(f,frames[i])
        rebuilt=r.copy()
        for a,b,_ in decisions:rebuilt[a]^=True;rebuilt[b]^=True
        assert np.array_equal(rebuilt,s)


def test_simultaneous_interval_is_wider():
    narrow=paired_interval(0,0,100000)
    wide=paired_interval(0,0,100000,alpha=.05/12)
    assert wide[0]<narrow[0]<0<narrow[1]<wide[1]


def test_negative_weight_fallback_and_disjoint_logical_xor():
    edges,metadata=compile_guarded(stim.DetectorErrorModel('error(0.6) D0 D1'))
    assert not edges and metadata['fallback']=='negative_or_nonfinite_matching_weight'
    dem=stim.DetectorErrorModel('error(0.1) D0 D1 L0 L1\nerror(0.1) D2 D3 L1')
    edges,_=compile_guarded(dem)
    residual,frame,decisions=guarded_scalar(np.ones(4,dtype=bool),edges,2)
    assert not residual.any() and frame.tolist()==[True,False] and len(decisions)==2
