"""Validate the actual Freqtrade runtime/config without accessing market data."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import freqtrade
from freqtrade.configuration import Configuration
from freqtrade.configuration.config_validation import validate_config_schema
from freqtrade.resolvers import StrategyResolver

ROOT = Path("/experiment")
SUB = Path("/freqtrade/user_data")
config = Configuration.from_files([str(SUB / "config.json")])
config["user_data_dir"] = SUB
config["strategy_path"] = str(SUB / "strategies")
config["strategy"] = "CodexCausalTrend"
strategy = StrategyResolver.load_strategy(config)
validate_config_schema(config)
sys.path.insert(0, str(SUB / "hyperopts"))
from EP004ValidLoss import EP004ValidLoss

assert freqtrade.__version__ == "2026.6", freqtrade.__version__
assert strategy.can_short is True
assert strategy.timeframe == "4h"
assert strategy.buy_params == config['_experiment']['candidate_parameters']
assert len(config["exchange"]["pair_whitelist"]) == 20
assert config["fee"] == 0.0006
assert config["dry_run_wallet"] == 10000
assert config["max_open_trades"] == 20
assert strategy.leverage("BTC/USDT:USDT", datetime.now(timezone.utc), 1.0, 1.0, 100.0,
                         entry_tag=None, side="long") == 1.0
assert strategy.leverage("BTC/USDT:USDT", datetime.now(timezone.utc), 1.0, 1.0, 100.0,
                         entry_tag=None, side="short") == 1.0
source_loss = ROOT / "source/EP004_four-llm-quant-benchmark/scaffold/EP004ValidLoss.py"
loss_hash = hashlib.sha256((SUB / "hyperopts/EP004ValidLoss.py").read_bytes()).hexdigest()
assert loss_hash == hashlib.sha256(source_loss.read_bytes()).hexdigest()
result = {
    "checked_at_utc": datetime.now(timezone.utc).isoformat(),
    "freqtrade_version": freqtrade.__version__,
    "strategy_loaded": type(strategy).__name__,
    "config_schema": "PASS",
    "can_short": strategy.can_short,
    "timeframe": strategy.timeframe,
    "long_leverage": 1.0, "short_leverage": 1.0,
    "loss_loaded": EP004ValidLoss.__name__, "loss_sha256": loss_hash,
    "market_data_files": len(list((SUB / "data").rglob("*.feather"))),
    "backtest_status": "NOT_RUN_MISSING_MARKET_DATA",
    "note": "Runtime/config validation only; no synthetic or external market data used."
}
(ROOT / "audit/freqtrade_runtime.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
