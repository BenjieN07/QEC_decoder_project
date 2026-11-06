import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot_results(output):
    output=Path(output);rows=json.loads((output/'results.json').read_text())
    selected=[r for r in rows if r['role'] in ('primary','smoke')]
    guarded=[r for r in selected if r['decoder']=='guarded']
    x=np.arange(len(guarded));labels=[f"{r['basis']} d{r['distance']}\np={r['p']}" for r in guarded]
    fig,axes=plt.subplots(3,1,figsize=(11,11),sharex=True)
    delta=np.array([r['paired_delta'] for r in guarded])*100
    low=np.array([r['paired_ci'][0] for r in guarded])*100
    high=np.array([r['paired_ci'][1] for r in guarded])*100
    axes[0].errorbar(x,delta,yerr=[delta-low,high-delta],fmt='o',capsize=3)
    axes[0].axhline(guarded[0]['accuracy_margin']*100,color='red',linestyle='--',label='Registered tolerance')
    axes[0].axhline(0,color='gray',linewidth=.5)
    axes[0].set(ylabel='Guarded − A failure rate\n(percentage points)',title='F1 held-out rule: simultaneous primary intervals (smoke uses pointwise intervals)')
    axes[0].legend()
    for name,shift in [('isolated',-.24),('max2',0),('guarded',.24)]:
        points=[r for r in selected if r['decoder']==name]
        axes[1].bar(x+shift,[r['adaptive_reduction']*100 for r in points],.24,label=name)
        axes[2].bar(x+shift,[r['median_batch_ns_per_shot']['total_hybrid_ns']/r['median_batch_ns_per_shot']['baseline_ns'] for r in points],.24,label=name)
    axes[1].axhline(5,color='red',linestyle='--');axes[1].set(ylabel='Adaptive byte reduction (%)');axes[1].legend()
    axes[2].axhline(1,color='gray',linestyle='--');axes[2].set(ylabel='Median CPU batch B/A',xticks=x,xticklabels=labels)
    for ax in axes:ax.grid(axis='y',alpha=.2)
    fig.tight_layout();fig.savefig(output/'F1_comparison.png',dpi=150);plt.close(fig)
    with (output/'results.csv').open('w',newline='',encoding='utf-8') as file:
        flat=[]
        for r in rows:
            record={k:v for k,v in r.items() if not isinstance(v,(dict,list,tuple))}
            record['paired_ci_low'],record['paired_ci_high']=r['paired_ci']
            record.update({f'{k}_per_shot':v for k,v in r['median_batch_ns_per_shot'].items()})
            flat.append(record)
        writer=csv.DictWriter(file,fieldnames=flat[0].keys());writer.writeheader();writer.writerows(flat)
