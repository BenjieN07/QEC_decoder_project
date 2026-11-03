import itertools
import numpy as np
import stim
from qec_project.baseline import generate
from qec_project.config import load_config
from qec_project.predecoder import edges_from_dem, predecode


def check(syndrome, edges, observables):
    residual, frame, decisions = predecode(syndrome, edges, observables)
    reconstructed = residual.copy()
    mask = 0
    used = set()
    for a, b, logical in decisions:
        assert (a,b,logical) in edges
        assert a not in used and b not in used
        used.update([a,b])
        reconstructed[a] ^= True
        reconstructed[b] ^= True
        mask ^= logical
    assert np.array_equal(reconstructed, syndrome)
    assert frame.tolist() == [bool(mask & (1 << bit)) for bit in range(observables)]


def test_all_pairs_and_triples():
    for basis in ('X','Z'):
        config = load_config('configs/smoke.json')
        config['basis'] = basis
        circuit = generate(config)
        edges = edges_from_dem(circuit.detector_error_model(decompose_errors=True))
        for count in (0,1,2,3):
            for indices in itertools.combinations(range(circuit.num_detectors),count):
                syndrome = np.zeros(circuit.num_detectors,dtype=bool)
                syndrome[list(indices)] = True
                check(syndrome,edges,1)


def test_multiple_observable_xor():
    edges = edges_from_dem(stim.DetectorErrorModel(
        'error(0.1) D0 D1 L0 L1\nerror(0.1) D2 D3 L1'))
    syndrome = np.ones(4,dtype=bool)
    check(syndrome,edges,2)
    assert predecode(syndrome,edges,2)[1].tolist() == [True,False]
