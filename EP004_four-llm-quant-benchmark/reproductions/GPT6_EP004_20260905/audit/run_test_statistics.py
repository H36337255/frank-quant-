"""Evaluate frozen-candidate TEST trades with unchanged upstream statistics."""
import json
from run_repository_checks import execute, SUB, OUT

checks=[
    execute('deflated_sharpe.py',['--hyperopt',str(SUB/'hyperopt_results.json'),
            '--trades',str(SUB/'backtest_results/test.zip'),'--wallet','10000'],
            'Original TRAIN/VALID search trials and frozen-candidate TEST trades'),
    execute('mc_bootstrap.py',['--trades',str(SUB/'backtest_results/test.zip'),
            '--iters','5000','--block','10','--seed','20260905',
            '--out',str(OUT/'mc_test.json'),'--plot',str(OUT/'mc_test.png')],
            'Frozen-candidate TEST trades')]
(OUT/'script_validation_test.json').write_text(json.dumps({'checks':checks},indent=2,ensure_ascii=False),encoding='utf-8')
for item in checks:
    print(item['script'],item['returncode'])
    print(item['stdout'])
if any(item['status']!='VALID_RESULT' for item in checks):
    raise SystemExit(2)
