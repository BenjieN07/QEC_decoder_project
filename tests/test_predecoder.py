import numpy as np
import stim
from qec_project.predecoder import edges_from_dem, predecode


def test_logical_frame_and_boundary_fallback():
    edges = edges_from_dem(stim.DetectorErrorModel('error(0.1) D0 D1 L0\nerror(0.1) D2 L0'))
    residual, frame, decisions = predecode(np.array([1,1,1]),edges,1)
    assert residual.tolist() == [False,False,True]
    assert frame.tolist() == [True]
    assert decisions == [(0,1,1)]


def test_collision_and_conflicting_masks():
    dem = stim.DetectorErrorModel('error(0.1) D0 D1\nerror(0.1) D1 D2')
    residual,frame,chosen = predecode(np.ones(3),edges_from_dem(dem),1)
    assert residual.all() and not frame.any() and not chosen
    dem = stim.DetectorErrorModel('error(0.1) D0 D1\nerror(0.1) D0 D1 L0')
    assert edges_from_dem(dem) == []


def test_correlations_and_no_error():
    dem = stim.DetectorErrorModel('error(0.1) D0 D1 ^ D2 D3')
    assert edges_from_dem(dem) == []
    assert not predecode(np.zeros(4),[(0,1,1)],1)[0].any()
