"""Bound downloaded data before exposing it to the strategy. No invented/fill rows."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import sys

ROOT = Path('/experiment')
holdout = '--holdout' in sys.argv
if holdout:
    frozen = json.loads((ROOT / 'audit/selection_frozen.json').read_text())
    for rel, expected in frozen['file_hashes'].items():
        assert hashlib.sha256((ROOT/'submission'/rel).read_bytes()).hexdigest() == expected
BASE = Path('/holdout/binance/futures') if holdout else ROOT / 'data/train_valid/binance/futures'
config = json.loads((ROOT / 'submission/config.json').read_text())
start = pd.Timestamp('2025-05-01' if holdout else '2021-01-01', tz='UTC')
end = pd.Timestamp('2026-07-01' if holdout else '2025-07-01', tz='UTC')
records, missing = [], []
for pair in config['exchange']['pair_whitelist']:
    prefix = pair.replace('/', '_').replace(':', '_')
    for tf, kind in [('30m', 'futures'), ('1h', 'futures'), ('4h', 'futures'),
                     ('1d', 'futures'), ('1h', 'mark'), ('1h', 'funding_rate')]:
        path = BASE / f'{prefix}-{tf}-{kind}.feather'
        if not path.exists():
            missing.append(path.name)
            continue
        raw = pd.read_feather(path)
        dates = pd.to_datetime(raw['date'], utc=True)
        # Do not inspect, summarize or report prices outside the allowed interval.
        keep = (dates >= start) & (dates < end)
        bounded = raw.loc[keep].reset_index(drop=True)
        removed = int((~keep).sum())
        if removed:
            bounded.to_feather(path)
        dates = pd.to_datetime(bounded['date'], utc=True)
        records.append({
            'file': path.name, 'pair': pair, 'timeframe': tf, 'kind': kind,
            'rows': len(bounded), 'out_of_boundary_rows_removed': removed,
            'first': str(dates.min()), 'last': str(dates.max()),
            'duplicate_dates': int(dates.duplicated().sum()),
            'sorted': dates.is_monotonic_increasing,
            'missing_values': int(bounded.isna().sum().sum()),
            'max_gap_hours': float(dates.diff().dt.total_seconds().max() / 3600) if len(dates) > 1 else None,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        })
bad = [r['file'] for r in records if not r['rows'] or r['duplicate_dates'] or not r['sorted'] or r['missing_values']]
result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
          'source': 'Binance via official Freqtrade 2026.6 download-data; newly user-authorized',
          'timerange': '20250501-20260701' if holdout else '20210101-20250701', 'end_exclusive': True,
          'purpose': 'Frozen candidate TEST evaluation; May/June warmup only' if holdout else 'TRAIN/VALID',
          'expected_files': 120, 'actual_files': len(records), 'missing': missing,
          'invalid': bad, 'records': records,
          'status': 'READY' if not missing and not bad else 'INCOMPLETE'}
(ROOT / ('audit/data_manifest_test.json' if holdout else 'audit/data_manifest.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k != 'records'}, indent=2))
if missing or bad:
    raise SystemExit(2)
