"""Private in-memory IBM credentials and a read-only capability probe.

Never saves an SDK account, prints raw exceptions, or exports account identifiers.
"""
import contextlib
from datetime import datetime,timezone
import io
import json
import logging
from pathlib import Path
from urllib.parse import quote,quote_plus

ROOT=Path(__file__).resolve().parents[2]


def credentials(root=ROOT):
    token=(root/'api.txt').read_text(encoding='utf-8-sig').strip()
    instance=(root/'crn.txt').read_text(encoding='utf-8-sig').strip()
    if len(token)<16 or not instance.startswith('crn:') or ':quantum-computing:' not in instance:
        raise ValueError('Invalid local IBM credential file format')
    return token,instance


def public_json(value,secrets):
    text=json.dumps(value,indent=2)
    for secret in secrets:
        if any(pattern in text for pattern in (secret,quote(secret,safe=''),quote_plus(secret,safe=''))):
            raise ValueError('Refusing to export private account data')
    return text


@contextlib.contextmanager
def quiet_sdk():
    previous=logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):yield
    finally:logging.disable(previous)


def connect(root=ROOT):
    from qiskit_ibm_runtime import QiskitRuntimeService
    token,instance=credentials(root)
    return QiskitRuntimeService(channel='ibm_quantum_platform',token=token,instance=instance)


def probe(root=ROOT):
    secrets=credentials(root)
    with quiet_sdk():
        service=connect(root)
        instances=service.instances()
        selected=next((entry for entry in instances if entry.get('crn')==secrets[1]),None)
        plan=selected.get('plan') if selected else None
        usage=service.usage()
        backends=service.backends(min_num_qubits=17,dynamic_circuits=True)
        summaries=[]
        for backend in backends:
            status=backend.status()
            summaries.append(dict(name=backend.name,qubits=backend.num_qubits,
                operational=bool(status.operational),pending_jobs=status.pending_jobs,
                simulator=bool(getattr(backend.configuration(),'simulator',False))))
    summary=dict(checked_utc=datetime.now(timezone.utc).isoformat(),authenticated=True,
        instance_plan=plan,selected_instance_found=selected is not None,
        free_plan_confirmed=plan=='open',job_submitted=False,
        usage={key:value for key,value in usage.items() if key in (
            'usage_limit_seconds','usage_allocation_seconds','usage_consumed_seconds','usage_remaining_seconds')
            and (value is None or isinstance(value,(int,float)))},
        backends=sorted(summaries,key=lambda b:(not b['operational'],b['pending_jobs'])),
        scope='Read-only IBM quantum processor access; no FPGA board access is implied')
    text=public_json(summary,secrets)
    directory=root/'private';directory.mkdir(exist_ok=True)
    (directory/'ibm_probe.json').write_text(text,encoding='utf-8')
    return summary


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='Private IBM Quantum access; probe is read-only')
    parser.add_argument('action',choices=['probe'])
    args=parser.parse_args(argv)
    try:
        if args.action=='probe':print(public_json(probe(),credentials()))
    except Exception as error:
        # SDK messages/tracebacks can embed URLs or instance identifiers.
        print(f'IBM access failed ({type(error).__name__}). No credentials or raw exception were printed.')
        raise SystemExit(1)


if __name__=='__main__':main()
