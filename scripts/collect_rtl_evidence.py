"""Copy small reproducibility records; count generic synthesis cells honestly."""
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from collections import Counter

rows = []
for name in ('rtl-x3','rtl-z3','rtl-x5'):
    source = Path('results')/name
    xml = ET.parse(source/'verification.xml')
    if xml.findall('.//failure') or xml.findall('.//error'):
        raise RuntimeError(f'{name} did not pass')
    cells = json.loads((source/'netlist.json').read_text())['modules']['local_predecoder']['cells']
    types = Counter(cell['type'] for cell in cells.values())
    row = json.loads((source/'metadata.json').read_text())
    row.update(cells=len(cells),cell_types=dict(types),
               register_bits=sum(count for kind,count in types.items() if 'DFF' in kind),
               cycles=json.loads((source/'cycles.json').read_text()))
    rows.append(row)
    target = Path('reports/evidence/M5')/name
    target.mkdir(parents=True,exist_ok=True)
    for filename in ('local_predecoder.sv','model.dem','metadata.json','verification.xml','cycles.json','synthesis.log'):
        shutil.copy2(source/filename,target/filename)
Path('reports/evidence/M5/summary.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print([(r['basis'],r['distance'],r['cells'],r['register_bits']) for r in rows])
