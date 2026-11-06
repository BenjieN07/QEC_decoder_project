import numpy as np
import pytest
import stim
pytest.importorskip('qiskit_aer')
from qiskit_aer import AerSimulator
from qec_project.qiskit_bridge import to_qiskit,measurements_from_bitstrings,detectors_from_measurements


def simulate(circuit):
    qc,metadata=to_qiskit(circuit)
    result=AerSimulator(method='stabilizer').run(qc,shots=32,memory=True,seed_simulator=101).result()
    return measurements_from_bitstrings(result.get_memory(),metadata['measurement_count'])


@pytest.mark.parametrize('basis',['x','z'])
def test_noiseless_roundtrip(basis):
    reference=stim.Circuit.generated('surface_code:rotated_memory_'+basis,distance=3,rounds=3)
    qc,meta=to_qiskit(reference)
    assert qc.num_qubits==17 and meta['measurement_count']==33 and len(meta['mid_measurement_indices'])==24
    detectors,actual=detectors_from_measurements(reference,simulate(reference))
    assert detectors.shape==(32,24) and actual.shape==(32,1)
    assert not detectors.any() and not actual.any()


@pytest.mark.parametrize('basis',['x','z'])
@pytest.mark.parametrize('pauli',['X','Y','Z'])
def test_injected_fault_matches_stim(basis,pauli):
    reference=stim.Circuit.generated('surface_code:rotated_memory_'+basis,distance=3,rounds=3)
    deterministic=stim.Circuit();stochastic=stim.Circuit();inserted=False
    qubit=1  # Active data-qubit index in this generated circuit.
    for instruction in reference.flattened():
        deterministic.append(instruction);stochastic.append(instruction)
        if instruction.name=='TICK' and not inserted:
            deterministic.append(pauli,[qubit]);stochastic.append(pauli+'_ERROR',[qubit],1.)
            inserted=True
    observed=detectors_from_measurements(reference,simulate(deterministic))
    expected=stochastic.compile_detector_sampler(seed=101).sample(32,separate_observables=True)
    assert np.array_equal(observed[0],expected[0]) and np.array_equal(observed[1],expected[1])


def test_noise_and_bad_bitstrings_rejected():
    with pytest.raises(ValueError):to_qiskit(stim.Circuit('X_ERROR(0.1) 0\nM 0'))
    with pytest.raises(ValueError):measurements_from_bitstrings(['01'],3)
