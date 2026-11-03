"""Four headline figures with tightly defined scope; no inferred physical clocks."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plots(directory):
    directory = Path(directory)
    rows = json.loads((directory/'study.json').read_text())
    figure_dir = directory/'figures';figure_dir.mkdir(exist_ok=True)
    fig,axes = plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,basis in zip(axes,('X','Z')):
        for distance in sorted({r['distance'] for r in rows}):
            points = sorted([r for r in rows if r['basis']==basis and r['distance']==distance and r['rounds']==distance and r['mode']=='isolated'],key=lambda r:r['p'])
            if not points:continue
            for decoder,style in [('baseline','-'),('hybrid','--')]:
                y = np.array([r[f'{decoder}_failures']/r['shots'] for r in points])
                low = np.array([r[f'{decoder}_ci'][0] for r in points])
                high = np.array([r[f'{decoder}_ci'][1] for r in points])
                ax.errorbar([r['p'] for r in points],y,yerr=[np.maximum(0,y-low),np.maximum(0,high-y)],
                            linestyle=style,marker='o',label=f'd={distance}, {"A" if decoder=="baseline" else "B"}')
        ax.set(title=f'{basis} memory, rounds=d',xlabel='p (each of four circuit noise channels)');ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set_ylabel('Logical failure probability per memory window')
    fig.suptitle('Paired samples; 95% Wilson intervals; isolated-pair mode')
    fig.tight_layout();fig.savefig(figure_dir/'logical_error.png',dpi=160);plt.close(fig)

    selected = sorted([r for r in rows if r['basis']=='X' and r['p']==.005 and r['rounds']==r['distance'] and r['mode']=='isolated'],key=lambda r:r['distance'])
    if not selected:
        selected = [r for r in rows if r['mode']=='isolated'][:3]
    x=np.arange(len(selected)); width=.2
    fig,ax=plt.subplots(figsize=(8,4.5))
    for i,(key,label) in enumerate([('baseline_ns','A: MWPM'),('predecode_ns','B: preprocessing'),('residual_decode_ns','B: MWPM'),('total_hybrid_ns','B: total')]):
        ax.bar(x+(i-1.5)*width,[r['batch_per_window_ns'][key]['p50']/1000 for r in selected],width,label=label)
    ax.set(xticks=x,xticklabels=[f"d={r['distance']}" for r in selected],ylabel='Median amortized CPU time per window (us)',
           title='X memory, rounds=d, p=.005; batch processing, setup/I/O excluded')
    ax.set_yscale('log');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(figure_dir/'component_latency.png',dpi=160);plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    selected=[r for r in rows if r['basis']=='X' and r['rounds']==r['distance'] and r['mode']=='isolated']
    for ax,encoding in zip(axes,('sparse','adaptive')):
        for d in sorted({r['distance'] for r in selected}):
            points=sorted([r for r in selected if r['distance']==d],key=lambda r:r['p'])
            for side,style in [('baseline','-'),('hybrid','--')]:
                ax.plot([r['p'] for r in points],[r[f'{encoding}_{side}_bytes']/r['shots'] for r in points],
                        marker='o',linestyle=style,label=f'd={d}, {"A" if side=="baseline" else "B"}')
        ax.set(xlabel='p',ylabel='Serialized bytes per memory window',title=f'{encoding.capitalize()} format (headers + frame included)');ax.grid(alpha=.2)
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='lower center',ncol=3,fontsize=8)
    fig.suptitle('X memory, rounds=d; adaptive adds one format-tag byte')
    fig.tight_layout(rect=(0,.12,1,1));fig.savefig(figure_dir/'communication.png',dpi=160);plt.close(fig)

    hardware=directory/'hardware_summary.json'
    if not hardware.exists():hardware=Path('reports/evidence/M5/summary.json')
    if hardware.exists():
        entries=json.loads(hardware.read_text())
        fig,ax=plt.subplots(figsize=(8,4.5))
        ax.bar([f"{r['basis']}, d={r['distance']}" for r in entries],[r['cells'] for r in entries])
        ax.set(ylabel='Generic Yosys cells (including registers)',title='Parallel fixed-graph prototype: one cycle availability without stalls')
        fig.text(.5,.01,'No target mapping, timing closure, physical FPGA speed or power measurement',ha='center',fontsize=8)
        fig.tight_layout(rect=(0,.04,1,1));fig.savefig(figure_dir/'rtl_resources.png',dpi=160);plt.close(fig)
