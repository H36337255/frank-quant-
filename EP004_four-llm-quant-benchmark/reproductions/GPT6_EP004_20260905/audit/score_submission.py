"""Compute self-reported metrics from actual exported trades with the fixed loss Sharpe."""
import json
import math
from pathlib import Path
import sys
import zipfile
import numpy as np
import pandas as pd

ROOT = Path('/experiment')
SUB = Path('/freqtrade/user_data')
sys.path.insert(0, str(SUB / 'hyperopts'))
from EP004ValidLoss import _sharpe_daily, TRAIN_START, VALID_START, VALID_END

def archive_for(segment):
    run = json.loads((ROOT / f'audit/{segment}_20260905.json').read_text())
    name = run['backtest_zip'].replace('\\', '/').split('/')[-1]
    path = SUB / 'backtest_results' / name
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if name.endswith('.json') and '_config' not in name:
                data = json.loads(archive.read(name))
                candidate = data.get('strategy', {}).get('CodexCausalTrend', {})
                if 'trades' in candidate:
                    return path.name, candidate
    raise RuntimeError('No strategy trades found')

def compute(segment):
    name, stat = archive_for(segment)
    trades = pd.DataFrame(stat['trades'])
    if trades.empty:
        raise RuntimeError('No actual trades; cannot score')
    start, end = (TRAIN_START, VALID_START) if segment == 'train' else (VALID_START, VALID_END)
    if segment == 'test':
        start, end = pd.Timestamp('2025-07-01',tz='UTC'), pd.Timestamp('2026-07-01',tz='UTC')
    cap = 10000.0
    dates = pd.to_datetime(trades['close_date'], utc=True).dt.floor('D')
    pnl = pd.to_numeric(trades['profit_abs'])
    daily = pnl.groupby(dates).sum().reindex(pd.date_range(start, end, freq='D'), fill_value=0.0) / cap
    equity = pd.concat([pd.Series([cap]), (cap * (1 + daily.cumsum())).reset_index(drop=True)], ignore_index=True)
    drawdown = (1 - equity / equity.cummax()).max()
    years = len(daily) / 365
    ending = cap + float(pnl.sum())
    annual = (ending / cap) ** (1 / years) - 1 if ending > 0 else -1.0
    downside = float(np.sqrt(np.mean(np.minimum(daily.to_numpy(), 0.0) ** 2)))
    positive, negative = float(pnl[pnl > 0].sum()), float(-pnl[pnl < 0].sum())
    sharpe = _sharpe_daily(trades, start, end, cap)
    metrics = {
        'ann_return': annual, 'sharpe': sharpe,
        'sortino': float(daily.mean()) / downside * math.sqrt(365) if downside > 0 else None,
        'calmar': annual / float(drawdown) if drawdown > 0 else None,
        'max_drawdown': float(drawdown), 'win_rate': float((pnl > 0).mean()),
        'profit_factor': positive / negative if negative > 0 else None,
        'turnover_per_year': float(pd.to_numeric(trades['stake_amount']).sum()) * 2 / cap / years,
        'n_trades': len(trades), 'sharpe_net_of_costs': sharpe
    }
    evidence = {
        'archive': name, 'profit_abs': float(pnl.sum()), 'return_total': ending / cap - 1,
        'long_trades': int((~trades['is_short'].astype(bool)).sum()),
        'short_trades': int(trades['is_short'].astype(bool).sum()),
        'long_profit_abs': float(pnl[~trades['is_short'].astype(bool)].sum()),
        'short_profit_abs': float(pnl[trades['is_short'].astype(bool)].sum()),
        'funding_column_present': 'funding_fees' in trades,
        'funding_fees_sum': float(pd.to_numeric(trades['funding_fees']).sum()) if 'funding_fees' in trades else None,
        'fee_open_values': sorted(trades['fee_open'].unique().tolist()),
        'fee_close_values': sorted(trades['fee_close'].unique().tolist()),
        'leverage_values': sorted(trades['leverage'].unique().tolist()),
        'first_open': str(pd.to_datetime(trades['open_date'], utc=True).min()),
        'last_close': str(pd.to_datetime(trades['close_date'], utc=True).max()),
        'score_calendar_days': len(daily),
    }
    assert evidence['fee_open_values'] == [0.0006] and evidence['fee_close_values'] == [0.0006]
    assert evidence['leverage_values'] == [1.0]
    return metrics, evidence

if '--test-only' in sys.argv:
    test_metrics,test_evidence=compute('test')
    (ROOT/'audit/test_metrics.json').write_text(json.dumps({'metrics':test_metrics,'evidence':test_evidence},indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({'metrics':test_metrics,'evidence':test_evidence},indent=2))
    raise SystemExit(0)

output = json.loads((SUB / 'metrics.json').read_text())
hyperopt = json.loads((SUB / 'hyperopt_results.json').read_text())
output['epochs_used'] = hyperopt['n_epochs']
evidence = {}
for segment in ['train', 'valid']:
    output[segment], evidence[segment] = compute(segment)
output['funding_included'] = all(evidence[s]['funding_column_present'] for s in evidence)
(SUB / 'metrics.json').write_text(json.dumps(output, indent=2, allow_nan=False), encoding='utf-8')
evidence['definitions'] = {
    'sharpe': 'Unmodified EP004ValidLoss._sharpe_daily, close-date realized profit_abs, zero-filled fixed calendar, ddof=1, sqrt(365)',
    'ann_return': 'CAGR of final wallet over the scoring calendar length / 365; fraction',
    'sortino': 'Mean daily realized return / RMS negative daily return * sqrt(365), target 0',
    'max_drawdown': 'Daily realized equity drawdown including initial wallet; fraction; not intraday/mark-to-market drawdown',
    'calmar': 'ann_return / daily realized max_drawdown',
    'win_rate': 'Fraction of trades with profit_abs > 0',
    'profit_factor': 'Sum positive profit_abs / absolute sum negative profit_abs',
    'turnover_per_year': '2 * sum entry stake / initial wallet / scoring years; round-trip entry-notional approximation',
    'funding': 'Presence of actual funding_fees on exported trades; cross-check data manifest and engine logs',
}
(ROOT / 'audit/score_evidence.json').write_text(json.dumps(evidence, indent=2, allow_nan=False), encoding='utf-8')
print(json.dumps(output, indent=2))
