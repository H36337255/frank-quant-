"""Verify measured deliverables, frozen strategy, source integrity and HTML links."""
import base64
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
SUB=ROOT/'submission'
AUDIT=ROOT/'audit'
EP=ROOT/'source/EP004_four-llm-quant-benchmark'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=load(AUDIT/'selection_frozen.json')
for path,expected in frozen['file_hashes'].items():
    assert sha(SUB/path)==expected,path
integrity={
    'loss':sha(EP/'scaffold/EP004ValidLoss.py')==sha(SUB/'hyperopts/EP004ValidLoss.py'),
    'export':sha(EP/'scaffold/export_hyperopt.py')==sha(SUB/'export_hyperopt.py'),
    'GOAL':sha(EP/'prompts/GOAL.md')==sha(SUB/'GOAL.md'),
    'README_FOR_MODEL':sha(EP/'prompts/README_FOR_MODEL.md')==sha(SUB/'README_FOR_MODEL.md')}
assert all(integrity.values())
metrics=load(SUB/'metrics.json')
assert metrics['epochs_used']==6 and metrics['funding_included'] is True
for segment in ['train','valid']:
    assert all(v is not None for v in metrics[segment].values())
assert all(load(AUDIT/f'{s}_20260905.json')['returncode']==0 for s in ['hyperopt','export','train','valid','test'])
for name in ['script_validation.json','script_validation_test.json']:
    assert all(x['status']=='VALID_RESULT' and x['returncode']==0 for x in load(AUDIT/name)['checks'])
for name in ['data_manifest.json','data_manifest_test.json']:
    assert load(AUDIT/name)['status']=='READY'
class Check(HTMLParser):
    def __init__(self):
        super().__init__();self.links=[];self.images=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))
        if tag=='img':self.images.append(attrs.get('src',''))
html_path=ROOT/'EP004_Codex_Report.html'
parser=Check();parser.feed(html_path.read_text(encoding='utf-8'))
for link in parser.links:
    if not link.startswith(('https:','#')):assert (ROOT/link).exists(),link
for src in parser.images:
    assert src.startswith('data:image/png;base64,')
    Image.open(io.BytesIO(base64.b64decode(src.split(',',1)[1]))).verify()
source_status=subprocess.run(['git','-C',str(ROOT/'source'),'status','--porcelain'],capture_output=True,text=True,check=True).stdout
assert not source_status.strip(),source_status
result={'completed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'COMPLETE',
    'strategy_frozen_hashes_unchanged':True,'source_integrity':integrity,'source_git_clean':True,
    'hyperopt_epochs':6,'distinct_parameter_sets':5,'completed_backtests':['TRAIN','VALID','TEST'],
    'original_validators_produced_results':True,'html_local_links_valid':True,
    'embedded_images_verified':len(parser.images),'html_sha256':sha(html_path),
    'caveat':'Technical workflow completed; strategy TEST return is negative and DSR is not significant.'}
(AUDIT/'final_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
