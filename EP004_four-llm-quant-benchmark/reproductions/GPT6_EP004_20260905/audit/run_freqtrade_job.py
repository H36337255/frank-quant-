"""Run one audited experiment stage in the official image, preserving its exit code."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import hashlib

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / 'submission'
AUDIT = ROOT / 'audit'
IMAGE = 'freqtradeorg/freqtrade:2026.6'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['hyperopt', 'train', 'valid', 'test', 'export', 'causality'])
    args = parser.parse_args()
    manifest = json.loads((AUDIT / 'data_manifest.json').read_text())
    if manifest['status'] != 'READY':
        raise SystemExit('Data manifest not READY')
    datadir = ROOT / 'data/train_valid'
    if args.stage == 'test':
        frozen = json.loads((AUDIT/'selection_frozen.json').read_text())
        for rel, expected in frozen['file_hashes'].items():
            assert hashlib.sha256((SUB/rel).read_bytes()).hexdigest() == expected
        assert json.loads((AUDIT/'data_manifest_test.json').read_text())['status'] == 'READY'
        datadir = Path('G:/AI/EP004_Holdout_20260905')
    docker = ['docker', 'run', '--rm', '-v', f'{SUB}:/freqtrade/user_data',
              '-v', f'{datadir}:/freqtrade/user_data/data:ro',
              '-v', f'{ROOT / "source/EP004_four-llm-quant-benchmark/scripts"}:/experiment_scripts:ro']
    common = ['--strategy', 'CodexCausalTrend', '--config', '/freqtrade/user_data/config.json',
              '--fee', '0.0006', '--no-color']
    if args.stage == 'hyperopt':
        if list((SUB / 'hyperopt_results').glob('*.fthypt')):
            raise SystemExit('Existing hyperopt results: refusing an unrecorded repeat search')
        command = docker + [IMAGE, 'hyperopt'] + common + [
            '--hyperopt-loss', 'EP004ValidLoss', '--spaces', 'buy', '--epochs', '6',
            '-j', '20', '--random-state', '20260905', '--timerange', '20210101-20250630']
    elif args.stage in ['train', 'valid', 'test']:
        timerange = {'train':'20210101-20240630','valid':'20240701-20250630','test':'20250701-20260701'}[args.stage]
        command = docker + [IMAGE, 'backtesting'] + common + [
            '--cache', 'none', '--timerange', timerange, '--export', 'trades']
    elif args.stage == 'export':
        command = docker + ['--network', 'none', '--entrypoint', 'python', IMAGE,
                            '/freqtrade/user_data/export_hyperopt.py', '--model', 'Codex (GPT-6)']
    else:
        command = docker + ['--network', 'none', '--entrypoint', 'python', IMAGE,
                            '/experiment_scripts/factor_causality_check.py', '--strategy', 'CodexCausalTrend']
    started = datetime.now(timezone.utc).isoformat()
    log_path = AUDIT / f'{args.stage}_20260905.log'
    with log_path.open('w', encoding='utf-8') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    record = {'stage': args.stage, 'started': started, 'finished': datetime.now(timezone.utc).isoformat(),
              'command': command, 'returncode': result.returncode, 'log': str(log_path)}
    if args.stage in ['train', 'valid', 'test'] and result.returncode == 0:
        archives = sorted((SUB / 'backtest_results').glob('*.zip'), key=lambda p: p.stat().st_mtime)
        if archives:
            record['backtest_zip'] = str(archives[-1])
    (AUDIT / f'{args.stage}_20260905.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
    print(json.dumps(record, indent=2))
    print(log_path.read_text(encoding='utf-8')[-8000:])
    return result.returncode

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.exit(main())
