"""Check numerical invariants, provenance and the standalone HTML artifact."""
from pathlib import Path
import json,hashlib,re
from html.parser import HTMLParser
import numpy as np,pandas as pd
from scipy import stats
from replicate import ols
ROOT=Path(__file__).resolve().parent;R=ROOT/'results';O=ROOT/'output'
checks=[]
def check(name,condition):
 assert condition,name
 checks.append({'name':name,'passed':True})
def load(name):return json.loads((R/name).read_text(encoding='utf-8'))
# Check custom OLS inference against an independent SciPy implementation.
x=np.array([0.,1.,2.,4.,7.,9.,10.]);y=np.array([2.,3.,5.,6.,10.,9.,14.]);a=ols(y,np.c_[np.ones(len(x)),x]);b=stats.linregress(x,y)
check('OLS slope and standard error match scipy.linregress',abs(a['beta'][1]-b.slope)<1e-12 and abs(a['se'][1]-b.stderr)<1e-12 and abs(a['p'][1]-b.pvalue)<1e-12)
for arm in ['e2e','jd']:
 for t in ['pre','post']:
  d=pd.read_csv(R/f'field_{arm}_{t}_metrics.csv')
  check(f'{arm}_{t}: cost identity and 500 unique IDs',len(d)==500 and d.id.nunique()==500 and np.max(abs(d.total-d.holding-d.stockout))<1e-8)
d=pd.read_csv(R/'offline_per_sku.csv');check('2607 distinct evaluated SKUs',len(d)==2607 and d.SKU.nunique()==2607)
check('independent offline evaluator matches every method',all(x['max_independent_cost_difference']==0 for x in load('offline_semantic_audit.json')))
check('theorem enumeration 1100 instances',load('theorem_validation.json')['single_cycle_cases']==1000 and load('theorem_validation.json')['two_cycle_exhaustive_cases']==100)
check('matching solver gradient',load('matching.json')['gradient_inf_norm']<1e-7)
for item in load('source_manifest.json'):
 p=ROOT/item['path']
 if not p.exists():p=ROOT/'sources'/Path(item['path']).name
 if not p.exists():p=ROOT.parent/'文献和数据'/Path(item['path']).name
 check('SHA256 '+item['path'],p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256'])
text=(O/'T1_论文复现报告.html').read_text(encoding='utf-8')
class AuditHTML(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.refs=[];self.images=[];self.resources=[];self.stack=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='a' and a.get('href','').startswith('#'):self.refs.append(a['href'][1:])
  if tag=='img':self.images.append(a)
  if tag in ['script','link','iframe','img'] and (a.get('src','').startswith(('http','//')) or a.get('href','').startswith(('http','//'))):self.resources.append(a)
parser=AuditHTML();parser.feed(text)
check('unique HTML IDs',len(parser.ids)==len(set(parser.ids)))
check('all navigation anchors exist',all(r in parser.ids for r in parser.refs))
check('six embedded PNGs with alt text',len(parser.images)==6 and all(x.get('src','').startswith('data:image/png;base64,') and x.get('alt') for x in parser.images))
check('no external runtime resources',not parser.resources and not re.search(r'\b(fetch|XMLHttpRequest|WebSocket)\s*\(',text))
embedded=json.loads(re.search(r'<script type="application/json" id="skuData">(.*?)</script>',text,re.S).group(1))
check('HTML dataset equals computed CSV',len(embedded['rows'])==2607 and abs(np.mean([r[2] for r in embedded['rows']])-d.E2E_RNN.mean())<1e-8)
check('expected methodological boundaries included',all(s in text for s in ['没有完整训练特征','17.5%','55.46%','20.096','负订单','0.7698']))
check('no unresolved template tokens','{{' not in text and 'TODO' not in text)
check('valid UTF8 content without replacement chars','\ufffd' not in text)
captions=re.findall(r'<caption>表(\d+)',text)
check('tables numbered in document order',list(map(int,captions))==list(range(1,14)))
(R/'delivery_validation.json').write_text(json.dumps({'passed':True,'checks':checks,'check_count':len(checks),'html_bytes':(O/'T1_论文复现报告.html').stat().st_size,'note':'HTML static/content and numerical checks; Node controls in javascript_validation.json; actual browser screenshots and viewport controls in browser_validation.json'},ensure_ascii=False,indent=2),encoding='utf-8')
print(f'PASS: {len(checks)} numerical, provenance and HTML checks')
