"""One-command software study, controls, optional RTL, retiming and queue audit.

Run from Windows with the installed project Python. Hardware uses WSL Ubuntu.
"""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from qec_project.research import run_study


def run(*arguments):
    subprocess.run([str(a) for a in arguments],check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smoke',action='store_true',help='Small pipeline validation, not research statistical power')
    parser.add_argument('--software-only',action='store_true',help='Skip RTL when WSL/tools are unavailable')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1];os.chdir(root)
    (root/'results').mkdir(exist_ok=True)
    os.environ['TMP']=os.environ['TEMP']=str(root/'results')
    run(sys.executable,'-m','pytest','--basetemp=results/reproduce-tests','-q')
    output=run_study('configs/research-smoke.json' if args.smoke else 'configs/research.json')
    controls=run_study('configs/research-controls.json')
    points=sorted(output.glob('point-*'))
    selected=[]
    for point in points:
        config=json.loads((point/'config.json').read_text())
        if config['rounds']==config['distance'] and config['noise']['after_clifford_depolarization']==.005 and (config['basis'],config['distance']) in [('X',3),('X',5),('X',7),('Z',3)]:
            selected.append((point,config))
    if selected:
        run(sys.executable,'scripts/sinter_crosscheck.py',selected[0][0])
    cases=[]
    if not args.software_only:
        linux_root=subprocess.check_output(['wsl','-d','Ubuntu','--','wslpath','-a',str(root)],text=True).strip()
        command='python3 -m venv "$HOME/.venvs/qec-rtl" && "$HOME/.venvs/qec-rtl/bin/python" -m pip install -r '+shlex.quote(linux_root+'/requirements-rtl-lock.txt')
        run('wsl','-d','Ubuntu','--','bash','-lc',command)
        for point,config in selected:
            case=f'{output.name}-rtl-{config["basis"].lower()}{config["distance"]}'
            directory=Path('results')/case
            run(sys.executable,'scripts/prepare_rtl.py','--replay',point,'--output',directory)
            command='cd '+shlex.quote(linux_root)+' && "$HOME/.venvs/qec-rtl/bin/python" scripts/verify_rtl.py '+shlex.quote(directory.as_posix())+' --build-dir '+shlex.quote('/tmp/'+case)
            run('wsl','-d','Ubuntu','--','bash','-lc',command)
            run(sys.executable,'scripts/score_rtl_replay.py',directory)
            cases.append(case)
        if cases:
            run(sys.executable,'scripts/collect_rtl_evidence.py',*cases,'--output',output/'rtl-evidence')
            shutil.copy2(output/'rtl-evidence/summary.json',output/'hardware_summary.json')
    # Do not overlap timing with sampling, synthesis, compilation or other study jobs.
    run(sys.executable,'scripts/retime_study.py',output)
    run(sys.executable,'scripts/study_queues.py',output)
    run(sys.executable,'scripts/audit_study.py',output)
    run(sys.executable,'scripts/study_summary.py',output)
    run(sys.executable,'scripts/package_study.py',output,controls,'--output',output/'evidence')
    (output/'reproduction.json').write_text(json.dumps(dict(study=str(output),controls=str(controls),rtl_cases=cases,
        note='Simulation and measured CPU results; no physical FPGA timing'),indent=2))
    print('Finished. Figures:',output/'figures')


if __name__=='__main__':main()
