"""Bounded IBM Open Plan QEC pilot. Credentials and job IDs stay private.

The QPU supplies physical measurement noise; decoding is offline CPU software.
The Stim DEM is an approximate synthetic prior, not a calibrated hardware model.
"""
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import uuid
import numpy as np
import pymatching
import stim
from .ibm_access import ROOT,credentials,connect,quiet_sdk,public_json,probe
from .qiskit_bridge import to_qiskit,hardware_measurements,simulator_measurements,measurements_from_bitstrings,detectors_from_measurements
from .baseline import wilson
from .predecoder import edges_from_dem,predecode_batch
from .guarded import compile_guarded,guarded_batch
from .statistics import paired_interval


def write(path,data):
    path.write_text(public_json(data,credentials()),encoding='utf-8')


def model(basis,spec,noisy=False):
    p=spec['decoder_prior_probability'] if noisy else 0.
    return stim.Circuit.generated('surface_code:rotated_memory_'+basis.lower(),distance=spec['distance'],rounds=spec['rounds'],
        after_clifford_depolarization=p,before_round_data_depolarization=p,
        before_measure_flip_probability=p,after_reset_flip_probability=p)


def assert_free(service,spec):
    token,instance=credentials()
    selected=next((row for row in service.instances() if row.get('crn')==instance),None)
    if selected is None or selected.get('plan')!='open' or service.active_instance()!=instance:
        raise ValueError('This pilot is restricted to the explicitly supplied Open/free instance')
    usage=service.usage();remaining=usage.get('usage_remaining_seconds')
    if not isinstance(remaining,(int,float)) or remaining<spec['minimum_free_remaining_seconds']:
        raise ValueError('Insufficient confirmed free allocation for the bounded pilot')
    return remaining


def prepare():
    from qiskit import qpy
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_aer import AerSimulator
    spec=json.loads((ROOT/'configs/ibm_pilot.json').read_text())
    if spec['shots_per_basis']>512 or spec['max_execution_time_seconds']>60 or spec['distance']!=3 or spec['rounds']!=3 or spec['bases']!=['X','Z']:
        raise ValueError('Pilot caps are 512 shots/basis, d=3, rounds=3, X/Z and 60 seconds')
    capability=probe()
    available=[b for b in capability['backends'] if b['operational'] and not b['simulator']]
    if not available:raise ValueError('No operational quantum backend is accessible')
    directory=ROOT/'private'/('ibm-pilot-'+uuid.uuid4().hex);directory.mkdir(parents=True)
    summaries=[];compiled=[]
    with quiet_sdk():
        service=connect();remaining=assert_free(service,spec)
        backend=service.backend(available[0]['name'])
        manager=generate_preset_pass_manager(backend=backend,optimization_level=1,seed_transpiler=spec['transpiler_seed'])
        for basis in spec['bases']:
            reference=model(basis,spec);qc,metadata=to_qiskit(reference)
            uses_measure2='measure_2' in backend.operation_names
            if uses_measure2:qc=hardware_measurements(qc,metadata['mid_measurement_indices'])
            isa=manager.run(qc);isa.name='surface_code_memory_'+basis
            local=simulator_measurements(isa)
            result=AerSimulator(method='stabilizer').run(local,shots=64,memory=True,seed_simulator=6106).result()
            if not result.success:raise RuntimeError('Transpiled ideal simulator rejected the circuit')
            measurements=measurements_from_bitstrings(result.get_memory(),metadata['measurement_count'])
            detectors,actual=detectors_from_measurements(reference,measurements)
            if detectors.any() or actual.any():raise RuntimeError('Transpiled ideal detector/observable validation failed')
            (directory/(basis+'.stim')).write_text(str(reference),encoding='utf-8')
            prior=model(basis,spec,True).detector_error_model(decompose_errors=True)
            (directory/(basis+'.dem')).write_text(str(prior),encoding='utf-8')
            active={isa.find_bit(q).index for item in isa.data if item.operation.name not in ('barrier','delay') for q in item.qubits}
            summaries.append(dict(basis=basis,logical_experiment_qubits=qc.num_qubits,
                device_register_qubits=isa.num_qubits,active_physical_qubits=len(active),depth=isa.depth(),
                operations=dict(isa.count_ops()),bridge=metadata,uses_measure_2=uses_measure2,
                noiseless_transpiled_validation_shots=64,noiseless_detectors_and_observables_all_zero=True))
            compiled.append(isa)
    with (directory/'circuits.qpy').open('wb') as stream:qpy.dump(compiled,stream)
    digest=hashlib.sha256((directory/'circuits.qpy').read_bytes()).hexdigest()
    manifest=dict(stage='prepared',created_utc=datetime.now(timezone.utc).isoformat(),backend=available[0]['name'],
        spec=spec,circuits=summaries,qpy_sha256=digest,free_remaining_seconds_at_prepare=remaining,
        versions={name:importlib.metadata.version(name) for name in ('qiskit','qiskit-ibm-runtime','qiskit-aer','stim','pymatching')},
        scope='Real-QPU pilot preparation only; no job submitted. CPU offline decoding, not FPGA execution.')
    write(directory/'manifest.json',manifest)
    return directory,manifest


def submit(directory):
    from qiskit import qpy
    from qiskit_ibm_runtime import SamplerV2
    directory=directory.resolve()
    manifest=json.loads((directory/'manifest.json').read_text())
    if (directory/'job.json').exists():raise ValueError('A job already exists for this prepared pilot; refusing duplicate submission')
    if hashlib.sha256((directory/'circuits.qpy').read_bytes()).hexdigest()!=manifest['qpy_sha256']:
        raise ValueError('Prepared circuits changed')
    with (directory/'circuits.qpy').open('rb') as stream:circuits=qpy.load(stream)
    with quiet_sdk():
        service=connect();remaining=assert_free(service,manifest['spec'])
        backend=service.backend(manifest['backend'])
        if not backend.status().operational or backend.configuration().simulator:
            raise ValueError('Selected real backend is unavailable')
        sampler=SamplerV2(mode=backend,options={
            'max_execution_time':manifest['spec']['max_execution_time_seconds'],
            'dynamical_decoupling':{'enable':False},'twirling':{'enable_gates':False,'enable_measure':False}})
        job=sampler.run(circuits,shots=manifest['spec']['shots_per_basis'])
        # Identifier is local provenance; never export the client/service/account.
        (directory/'job.json').write_text(json.dumps(dict(job_id=job.job_id(),backend=backend.name,
            submitted_utc=datetime.now(timezone.utc).isoformat(),free_remaining_seconds_before=remaining)),encoding='utf-8')
    manifest['stage']='submitted';write(directory/'manifest.json',manifest)
    return dict(stage='submitted',backend=manifest['backend'],shots_per_basis=manifest['spec']['shots_per_basis'],
                circuit_count=len(circuits),max_execution_time_seconds=manifest['spec']['max_execution_time_seconds'],
                job_identifier_saved_privately=True,scope='Quantum processor job; no FPGA execution')


def fetch(directory):
    directory=directory.resolve();manifest=json.loads((directory/'manifest.json').read_text())
    record=json.loads((directory/'job.json').read_text())
    with quiet_sdk():
        service=connect();job=service.job(record['job_id']);status=str(job.status())
        if status not in ('DONE','JobStatus.DONE'):
            return dict(stage='waiting' if status not in ('ERROR','CANCELLED','JobStatus.ERROR','JobStatus.CANCELLED') else 'failed',status=status,backend=manifest['backend'])
        result=job.result()
    rows=[]
    for index,entry in enumerate(manifest['circuits']):
        basis=entry['basis'];reference=stim.Circuit.from_file(directory/(basis+'.stim'))
        bitstrings=result[index].data.m.get_bitstrings()
        raw=measurements_from_bitstrings(bitstrings,entry['bridge']['measurement_count'])
        detectors,actual=detectors_from_measurements(reference,raw)
        dem=stim.DetectorErrorModel.from_file(directory/(basis+'.dem'))
        matching=pymatching.Matching.from_detector_error_model(dem)
        predictions={'baseline':matching.decode_batch(detectors)};frames={};residuals={}
        for label,preprocess in (
            ('isolated',lambda:predecode_batch(detectors,edges_from_dem(dem),dem.num_observables)),
            ('max2',lambda:predecode_batch(detectors,edges_from_dem(dem),dem.num_observables,event_limit=2)),
            ('guarded',lambda:guarded_batch(detectors,compile_guarded(dem)[0],dem.num_observables))):
            residual,frame=preprocess();predictions[label]=matching.decode_batch(residual)^frame
            frames[label]=frame;residuals[label]=residual
        np.savez_compressed(directory/(basis+'-measurements.npz'),raw_measurements=raw,detectors=detectors,actual=actual,**predictions)
        failures={label:np.any(predicted!=actual,axis=1) for label,predicted in predictions.items()}
        n=len(raw)
        rows.append(dict(basis=basis,shots=n,detectors=detectors.shape[1],mean_events=float(detectors.sum(axis=1).mean()),
            raw_observable_flip_count=int(np.any(actual,axis=1).sum()),
            decoders={label:dict(failures=int(wrong.sum()),failure_probability=float(wrong.mean()),ci=wilson(int(wrong.sum()),n),
                A_only=int((failures['baseline'] & ~wrong).sum()),B_only=int((wrong & ~failures['baseline']).sum()),
                paired_delta_ci=paired_interval(int((failures['baseline'] & ~wrong).sum()),int((wrong & ~failures['baseline']).sum()),n))
                for label,wrong in failures.items()}))
    report=dict(stage='completed',backend=manifest['backend'],experiment=manifest['spec'],results=rows,
        measurements_from_real_QPU=True,decoder_prior='Uncalibrated synthetic Stim prior; does not model all routing, device drift, leakage or readout correlations',
        scope='Offline decoding of routed physical surface-code memory circuits, not real-time feedback or FPGA performance')
    write(directory/'summary.json',report);manifest['stage']='completed';write(directory/'manifest.json',manifest)
    return report


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','submit','fetch'])
    parser.add_argument('--run',type=Path)
    args=parser.parse_args(argv)
    try:
        if args.action=='prepare':
            directory,manifest=prepare();print(public_json(manifest,credentials()));print(f'Private run: {directory}')
        else:
            if args.run is None:parser.error('--run is required')
            report=submit(args.run) if args.action=='submit' else fetch(args.run)
            print(public_json(report,credentials()))
    except Exception as error:
        print(f'IBM pilot stopped ({type(error).__name__}). No credential or raw SDK exception was printed.');raise SystemExit(1)


if __name__=='__main__':main()
