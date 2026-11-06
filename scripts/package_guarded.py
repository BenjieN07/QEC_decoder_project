"""Archive F1 outcomes without modifying the frozen rule or promotion criteria."""
import argparse
import hashlib
import gzip
import importlib.metadata
import json
from pathlib import Path
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path)
    parser.add_argument('--output',type=Path,default=Path('reports/evidence/F1'))
    args=parser.parse_args();source=args.run;output=args.output;output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((source/'manifest.json').read_text())
    if manifest['status']!='complete':raise ValueError('Only completed runs can be archived')
    rows=json.loads((source/'results.json').read_text())
    for filename in ('manifest.json','results.json','results.csv','verdict.json','development_audit.json','F1_comparison.png'):
        shutil.copy2(source/filename,output/filename)
    shutil.copy2('docs/F1_preregistration.md',output/'preregistration.md')
    shutil.copy2('configs/guarded.json',output/'plan.json')
    primary=[r for r in rows if r['role']=='primary']
    if not primary:raise ValueError('Archive command requires the held-out run, not smoke')
    summary={}
    for name in ('isolated','max2','guarded'):
        points=[r for r in primary if r['decoder']==name]
        ratios=[r['median_batch_ns_per_shot']['total_hybrid_ns']/r['median_batch_ns_per_shot']['baseline_ns'] for r in points]
        summary[name]=dict(points=len(points),shots=sum(r['shots'] for r in points),
            A_failures=sum(r['baseline_failures'] for r in points),B_failures=sum(r['hybrid_failures'] for r in points),
            A_only=sum(r['A_only'] for r in points),B_only=sum(r['B_only'] for r in points),
            adaptive_reduction_range=[min(r['adaptive_reduction'] for r in points),max(r['adaptive_reduction'] for r in points)],
            adaptive_reduction_median=float(np.median([r['adaptive_reduction'] for r in points])),
            batch_slowdown_median=float(np.median(ratios)),batch_slowdown_range=[min(ratios),max(ratios)],
            points_accuracy_pass=sum(r['accuracy_pass'] for r in points),
            worst_paired_upper=max(r['paired_ci'][1] for r in points))
    (output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    (output/'environment.json').write_text(json.dumps({name:importlib.metadata.version(name) for name in
        ('numpy','scipy','networkx','stim','pymatching','matplotlib','pytest')},indent=2),encoding='utf-8')
    files=[Path('src/qec_project/guarded.py'),Path('src/qec_project/guarded_study.py'),Path('src/qec_project/statistics.py'),Path(__file__)]
    (output/'source_hashes.json').write_text(json.dumps(dict(
        scope='Archive-time files; frozen execution revision is recorded in manifest.git',
        files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}),indent=2))
    configs=output/'point-configs';configs.mkdir(exist_ok=True)
    candidates=output/'point-candidates';candidates.mkdir(exist_ok=True)
    failures=[];prediction_checks=[]
    for point in sorted(source.glob('point-*')):
        shutil.copy2(point/'config.json',configs/(point.name+'.json'))
        with gzip.open(candidates/(point.name+'.json.gz'),'wb') as stream:
            stream.write((point/'guarded_edges.json').read_bytes())
        # Remove only a prior uncompressed copy made by this archive command.
        prior=candidates/(point.name+'.json')
        if prior.exists():prior.unlink()
        data=np.load(point/'samples.npz')
        baseline=data['predicted']
        for name in ('isolated','guarded'):
            processed=np.load(point/f'{name}.npz')
            different=int(np.any(processed['predicted']!=baseline,axis=1).sum())
            row=next(r for r in rows if r['point']==point.name and r['decoder']==name)
            prediction_checks.append(dict(point=point.name,role=row['role'],decoder=name,
                                          shots=len(baseline),prediction_disagreements=different))
            if baseline.shape[1]==1 and different!=row['A_only']+row['B_only']:
                raise RuntimeError('Stored predictions disagree with recorded discordance counts')
            for index in processed['B_only_indices'][:3]:
                failures.append(dict(point=point.name,decoder=name,shot=int(index),
                    detectors=np.flatnonzero(data['detectors'][index]).tolist(),
                    residual=np.flatnonzero(processed['residual'][index]).tolist(),
                    frame=processed['frames'][index].tolist(),actual=data['actual'][index].tolist(),
                    A=data['predicted'][index].tolist(),B=processed['predicted'][index].tolist()))
    (output/'failure_examples.json').write_text(json.dumps(failures,indent=2),encoding='utf-8')
    (output/'prediction_check.json').write_text(json.dumps(prediction_checks,indent=2),encoding='utf-8')
    guarded=[r for r in primary if r['decoder']=='guarded']
    labels=[f"{r['basis']} d{r['distance']}\np={r['p']}" for r in guarded];x=np.arange(len(guarded))
    for metric in ('accuracy','bytes','timing'):
        fig,ax=plt.subplots(figsize=(11,4.5))
        if metric=='accuracy':
            y=np.array([r['paired_delta'] for r in guarded])*100
            low=np.array([r['paired_ci'][0] for r in guarded])*100;high=np.array([r['paired_ci'][1] for r in guarded])*100
            ax.errorbar(x,y,yerr=[y-low,high-y],fmt='o',capsize=3)
            ax.axhline(manifest['plan']['accuracy_margin']*100,color='red',linestyle='--',label='Registered tolerance')
            ax.axhline(0,color='gray',linewidth=.7)
            ax.set(ylabel='Guarded − A failure rate (percentage points)',title='Held-out primary accuracy: >=95% simultaneous coverage over 12 points')
        else:
            for name,offset in [('isolated',-.25),('max2',0),('guarded',.25)]:
                values=[r for r in primary if r['decoder']==name]
                y=[r['adaptive_reduction']*100 for r in values] if metric=='bytes' else [r['median_batch_ns_per_shot']['total_hybrid_ns']/r['median_batch_ns_per_shot']['baseline_ns'] for r in values]
                ax.bar(x+offset,y,.25,label=name)
            if metric=='bytes':
                ax.axhline(manifest['plan']['minimum_adaptive_reduction']*100,color='red',linestyle='--',label='Registered target')
                ax.set(ylabel='Adaptive serialized byte reduction (%)',title='Held-out communication; headers, frame and format tag included')
            else:
                ax.axhline(1,color='gray',linestyle='--');ax.set(ylabel='Median batch B/A time',title='Measured CPU timing; sampling/setup/serialization excluded')
        ax.set(xticks=x,xticklabels=labels)
        if metric=='bytes':ax.legend(ncol=4,fontsize=8,loc='upper left',bbox_to_anchor=(0,1.18))
        else:ax.legend(ncol=4,fontsize=8)
        ax.grid(axis='y',alpha=.2)
        fig.tight_layout();fig.savefig(output/f'F1_{metric}.png',dpi=160);plt.close(fig)
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
