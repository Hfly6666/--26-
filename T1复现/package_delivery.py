"""Package portable source, inputs, report and outputs without numerical runtimes."""
from pathlib import Path
import hashlib,json,zipfile
ROOT=Path(__file__).resolve().parent;O=ROOT/'output';target=O/'T1_复现代码与数据.zip'
assert json.loads((ROOT/'results/delivery_validation.json').read_text(encoding='utf-8'))['passed']
assert json.loads((ROOT/'results/javascript_validation.json').read_text(encoding='utf-8'))['passed']
selected=[]
for p in ROOT.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(ROOT)
 if any(x in ['__pycache__','mplconfig','vendor'] for x in rel.parts):continue
 if p.suffix=='.zip' and rel.parts[0]=='output':continue
 if p.name=='交付文件校验.json':continue
 selected.append(p)
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(selected):z.write(p,Path('T1复现')/p.relative_to(ROOT))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 assert 'T1复现/output/T1_论文复现报告.html' in z.namelist()
 manifest={'date':'2026-10-25','zip_crc_passed':True,'zip_member_count':len(z.namelist()),'files':[]}
for p in [O/'T1_论文复现报告.html',target]:manifest['files'].append({'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'交付文件校验.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(manifest,ensure_ascii=False,indent=2))
