"""Verify exported trial joins against raw epoch trades, then freeze the candidate."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import sys
import pandas as pd

ROOT=Path('/experiment')
SUB=Path('/freqtrade/user_data')
sys.path.insert(0,str(SUB/'hyperopts'))
from EP004ValidLoss import _sharpe_daily,TRAIN_START,VALID_START,VALID_END

raw_path=next((SUB/'hyperopt_results').glob('*.fthypt'))
raw=[json.loads(line) for line in raw_path.read_text().splitlines() if line.strip()]
exported=json.loads((SUB/'hyperopt_results.json').read_text())
checks=[]
for entry,trial in zip(raw,exported['trials'],strict=True):
    trades=pd.DataFrame(entry['results_metrics']['trades'])
    close=pd.to_datetime(trades['close_date'],utc=True)
    ts=_sharpe_daily(trades.loc[close<VALID_START],TRAIN_START,VALID_START,10000)
    vs=_sharpe_daily(trades.loc[close>=VALID_START],VALID_START,VALID_END,10000)
    expected=-(vs-0.5*max(0,ts-vs))
    assert round(ts,4)==trial['train_sharpe'] and round(vs,4)==trial['valid_sharpe']
    assert entry['params_dict']==trial['params']
    assert abs(entry['loss']-expected)<1e-10
    checks.append({'epoch':entry['current_epoch'],'params':entry['params_dict'],
                   'loss':entry['loss'],'train_sharpe':ts,'valid_sharpe':vs,
                   'long_trades':entry['results_metrics']['trade_count_long'],
                   'short_trades':entry['results_metrics']['trade_count_short']})
best=min(checks,key=lambda x:(x['loss'],-x['params']['trend_window'],-x['params']['entry_band']))
config=json.loads((SUB/'config.json').read_text())
assert best['params']==config['_experiment']['candidate_parameters']
assert best['long_trades']>0 and best['short_trades']>0
result={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'selected':best,'actual_epochs':len(raw),
        'distinct_parameter_sets':len({json.dumps(x['params'],sort_keys=True) for x in checks}),
        'export_join_verified_against_raw_trades':True,
        'duplicate_note':'Epochs 1 and 4 repeat the same parameters and recomputed scores; no ambiguous different-score join observed.',
        'trials':checks,'file_hashes':{str(p.relative_to(SUB)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [SUB/'strategies/CodexCausalTrend.py',SUB/'strategies/CodexCausalTrend.json',
                      SUB/'config.json',SUB/'hyperopt_results.json']}}
(ROOT/'audit/selection_frozen.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
