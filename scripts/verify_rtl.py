"""Run inside WSL using its project virtual environment."""
import argparse
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from cocotb_tools.runner import get_runner

parser = argparse.ArgumentParser()
parser.add_argument('directory',type=Path)
parser.add_argument('--build-dir',type=Path,help='Optional Linux-native scratch path for faster WSL builds')
args = parser.parse_args()
directory = args.directory.resolve()
root = Path(__file__).resolve().parents[1]
os.environ['VECTOR_FILE'] = str(directory/'vectors.json')
os.environ['CYCLE_FILE'] = str(directory/'cycles.json')
os.environ['OUTPUT_FILE'] = str(directory/'observed_outputs.json')
runner = get_runner('verilator')
runner.build(sources=[directory/'local_predecoder.sv'],hdl_toplevel='local_predecoder',
             build_dir=args.build_dir or directory/'sim_build',always=True,build_args=['-Wno-fatal'])
runner.test(hdl_toplevel='local_predecoder',test_module='verify_predecoder',
            test_dir=root/'rtl/tb',results_xml=str(directory/'verification.xml'))
tree = ET.parse(directory/'verification.xml')
if tree.findall('.//failure') or tree.findall('.//error'):
    raise RuntimeError('RTL verification failed; synthesis not accepted')
subprocess.run(['yosys','-l',str(directory/'synthesis.log'),'-p',
                f'read_verilog -sv {directory}/local_predecoder.sv; synth -top local_predecoder; stat; write_json {directory}/netlist.json'],check=True)
