"""Exact noiseless Stim Clifford/measurement conversion, with record-order metadata.

Noise channels belong to the decoder prior, not the submitted QPU circuit.
Annotations are retained in Stim for measurement-to-detector conversion.
"""
import numpy as np


def to_qiskit(circuit):
    from qiskit import QuantumCircuit,QuantumRegister,ClassicalRegister
    flat=circuit.flattened()
    annotations={'QUBIT_COORDS','SHIFT_COORDS','DETECTOR','OBSERVABLE_INCLUDE'}
    active=sorted({t.value for op in flat if op.name not in annotations|{'TICK'}
                   for t in op.targets_copy() if t.is_qubit_target})
    mapping={q:i for i,q in enumerate(active)}
    qc=QuantumCircuit(QuantumRegister(len(active),'q'),ClassicalRegister(circuit.num_measurements,'m'))
    record=0;mid=[]
    for op in flat:
        name=op.name;targets=op.targets_copy()
        if name in annotations:continue
        if name=='TICK':qc.barrier();continue
        if any(not t.is_qubit_target or t.is_inverted_result_target for t in targets):
            raise ValueError('Unsupported target form in circuit conversion')
        qubits=[mapping[t.value] for t in targets]
        if name=='CX':
            if len(qubits)%2:raise ValueError('CX needs control/target pairs')
            for a,b in zip(qubits[::2],qubits[1::2]):qc.cx(a,b)
        elif name in ('H','X','Y','Z'):
            for q in qubits:getattr(qc,name.lower())(q)
        elif name in ('R','RX'):
            for q in qubits:
                qc.reset(q)
                if name=='RX':qc.h(q)
        elif name in ('M','MX','MR','MRX'):
            for q in qubits:
                x_basis=name in ('MX','MRX')
                if x_basis:qc.h(q)
                qc.measure(q,record)
                if name.startswith('MR'):
                    mid.append(record);qc.reset(q)
                    if x_basis:qc.h(q)
                record+=1
        else:raise ValueError(f'Unsupported Stim operation: {name}')
    if record!=circuit.num_measurements:raise ValueError('Measurement count mismatch')
    return qc,dict(active_stim_qubits=active,measurement_count=record,mid_measurement_indices=mid,
                   detector_count=circuit.num_detectors,observable_count=circuit.num_observables)


def measurements_from_bitstrings(bitstrings,count):
    strings=[text.replace(' ','') for text in bitstrings]
    if not strings or any(len(text)!=count or set(text)-{'0','1'} for text in strings):
        raise ValueError('Unexpected measurement bit-string format or length')
    return np.array([[bit=='1' for bit in text[::-1]] for text in strings],dtype=bool)


def detectors_from_measurements(reference,measurements):
    return reference.compile_m2d_converter().convert(measurements=measurements,separate_observables=True)


def hardware_measurements(qc,indices):
    from qiskit_ibm_runtime.circuit import MidCircuitMeasure
    result=qc.copy_empty_like()
    for item in qc.data:
        operation=item.operation
        if operation.name=='measure' and qc.find_bit(item.clbits[0]).index in indices:
            operation=MidCircuitMeasure()
        result.append(operation,item.qubits,item.clbits)
    return result


def simulator_measurements(qc):
    """Map hardware mid-measurement instruction back to standard Aer measurement."""
    from qiskit.circuit import Measure
    result=qc.copy_empty_like()
    for item in qc.data:
        operation=Measure() if item.operation.name=='measure_2' else item.operation
        result.append(operation,item.qubits,item.clbits)
    return result
