"""Export whitelisted pilot evidence, never credentials, job IDs or SDK objects."""
import argparse
import json
from pathlib import Path
import shutil
import hashlib
import numpy as np
from qec_project.ibm_access import credentials,public_json


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,default=Path('reports/evidence/H1'))
    args=parser.parse_args();source=args.run;output=args.output
    manifest=json.loads((source/'manifest.json').read_text())
    summary=json.loads((source/'summary.json').read_text())
    if manifest['stage']!='completed' or summary['stage']!='completed':raise ValueError('Actual hardware results are required')
    summary['reported_runtime_usage']={k:v for k,v in summary['reported_runtime_usage'].items() if k.endswith('_seconds')}
    output.mkdir(parents=True,exist_ok=True)
    (output/'summary.json').write_text(public_json(summary,credentials()),encoding='utf-8')
    (output/'preparation.json').write_text(public_json(manifest,credentials()),encoding='utf-8')
    private_job=json.loads((source/'job.json').read_text())
    provenance=dict(submitted_utc=private_job['submitted_utc'],backend=private_job['backend'],
                    job_id_sha256=hashlib.sha256(private_job['job_id'].encode()).hexdigest(),
                    note='Full job identifier remains private; digest links this report to the local job record')
    (output/'provenance.json').write_text(public_json(provenance,credentials()),encoding='utf-8')
    for basis in manifest['spec']['bases']:
        for suffix in ('.stim','.dem','-measurements.npz'):
            shutil.copy2(source/(basis+suffix),output/(basis+suffix))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,4.5))
    positions=np.arange(len(summary['results']))
    for label,offset in [('baseline',-.27),('isolated',-.09),('max2',.09),('guarded',.27)]:
        records=[row['decoders'][label] for row in summary['results']]
        y=np.array([r['failure_probability'] for r in records])
        low=np.array([r['ci'][0] for r in records]);high=np.array([r['ci'][1] for r in records])
        ax.errorbar(positions+offset,y,yerr=[y-low,high-y],fmt='o',capsize=3,label=label)
    ax.set(xticks=positions,xticklabels=[r['basis']+' memory' for r in summary['results']],
           ylabel='Logical memory failure fraction (95% Wilson interval)',
           title='IBM '+summary['backend']+': routed d=3, 3 rounds, 512 real shots/basis')
    ax.set_ylim(0,.6);ax.legend(ncol=2);ax.grid(axis='y',alpha=.2)
    fig.text(.5,.01,'Uncalibrated synthetic decoder prior; offline CPU decoding; no FPGA execution',ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(output/'real_qpu_pilot.png',dpi=160);plt.close(fig)
    print('Sanitized physical quantum measurements and summary archived; no job ID or account fields exported.')


if __name__=='__main__':main()
