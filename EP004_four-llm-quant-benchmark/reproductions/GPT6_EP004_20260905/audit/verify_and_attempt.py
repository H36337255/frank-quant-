"""Record actual checks and failed execution attempts without inventing market data."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
EP = SOURCE / "EP004_four-llm-quant-benchmark"
SUBMISSION = ROOT / "submission"
AUDIT = ROOT / "audit"


def command(args, timeout=30):
    try:
        result = subprocess.run(args, cwd=SUBMISSION, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"argv": args, "returncode": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"argv": args, "returncode": None, "error": str(exc)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    tracked_result = command(["git", "-C", str(SOURCE), "ls-tree", "-r", "--name-only", "HEAD"])
    if tracked_result["returncode"] != 0:
        raise RuntimeError(tracked_result)
    tracked = tracked_result["stdout"].splitlines()
    candidates = [p for p in tracked if p.lower().endswith(
        (".feather", ".parquet", ".csv", ".h5", ".hdf5", ".zip", ".gz"))
        or any(term in p.lower() for term in ("ohlcv", "funding", "-mark", "data_shared", "data_full"))]
    tracked_json = [p for p in tracked if p.endswith((".json", ".jsonl"))]
    config = json.loads((SUBMISSION / "config.json").read_text(encoding="utf-8"))
    base = json.loads((EP / "scaffold/base_config.json").read_text(encoding="utf-8"))
    protected_keys = [k for k in base if not k.startswith(("_", "$"))]
    config_equal = {k: config.get(k) == base[k] for k in protected_keys}
    syntax = {}
    for path in [SUBMISSION / "strategies/CodexCausalTrend.py",
                 SUBMISSION / "hyperopts/EP004ValidLoss.py",
                 SUBMISSION / "hyperopts/export_hyperopt.py",
                 SUBMISSION / "strategies/factor_causality_check.py"]:
        content = path.read_text(encoding="utf-8")
        ast.parse(content, filename=str(path))
        compile(content, str(path), "exec")
        syntax[str(path.relative_to(SUBMISSION))] = "syntax_pass_only_not_imported"
    copies = {
        "loss": (EP / "scaffold/EP004ValidLoss.py", SUBMISSION / "hyperopts/EP004ValidLoss.py"),
        "export": (EP / "scaffold/export_hyperopt.py", SUBMISSION / "hyperopts/export_hyperopt.py"),
        "causality": (EP / "scripts/factor_causality_check.py", SUBMISSION / "strategies/factor_causality_check.py"),
    }
    copy_checks = {name: {"source_sha256": sha(a), "copy_sha256": sha(b),
                          "identical": sha(a) == sha(b)} for name, (a, b) in copies.items()}
    engine = command(["docker", "version"])
    # Only attempt failing startup when no engine is available. If an engine is
    # available, absent data must block execution before any image pull/network call.
    attempts = []
    if engine["returncode"] != 0:
        docker = ["docker", "run", "--rm", "--pull", "never", "-v",
                  f"{SUBMISSION}:/freqtrade/user_data", "freqtradeorg/freqtrade:2026.6"]
        common = ["--strategy", "CodexCausalTrend", "--config", "/freqtrade/user_data/config.json",
                  "--fee", "0.0006"]
        attempts.append(command(docker + ["hyperopt"] + common + [
            "--hyperopt-loss", "EP004ValidLoss", "--spaces", "buy", "--epochs", "6",
            "-j", "20", "--random-state", "20260905", "--timerange", "20210101-20250630"]))
        for timerange in ["20210101-20240630", "20240701-20250630"]:
            attempts.append(command(docker + ["backtesting"] + common + [
                "--cache", "none", "--timerange", timerange, "--export", "trades"]))
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": command(["git", "-C", str(SOURCE), "rev-parse", "HEAD"]),
        "source_status": command(["git", "-C", str(SOURCE), "status", "--short"]),
        "tracked_file_count": len(tracked), "tracked_files": tracked,
        "possible_raw_data_or_archives": candidates,
        "json_paths_for_manual_inventory_review": tracked_json,
        "protected_config_equal": config_equal, "scaffold_integrity": copy_checks,
        "syntax": syntax, "docker_version": engine, "execution_attempts": attempts,
        "strategy_sha256": sha(SUBMISSION / "strategies/CodexCausalTrend.py"),
        "config_sha256": sha(SUBMISSION / "config.json"),
        "epochs_completed": 0, "backtests_completed": 0,
        "real_data_causality_test": "NOT_RUN", "funding_accounting": "NOT_VERIFIED",
        "both_sides_traded": "NOT_VERIFIED",
        "status": "BLOCKED_MISSING_REPOSITORY_MARKET_DATA",
        "note": "File inventory and syntax checks are not a strategy performance experiment."
    }
    (AUDIT / "execution.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    assert all(config_equal.values()), "Protected config differs from source"
    assert all(item["identical"] for item in copy_checks.values()), "Scaffold differs from source"
    print(json.dumps({k: report[k] for k in ["tracked_file_count", "possible_raw_data_or_archives",
                     "epochs_completed", "backtests_completed", "status"]}, indent=2))
    print("Saved actual command output to", AUDIT / "execution.json")
    return 2  # A blocked experiment must not return a success code.


if __name__ == "__main__":
    sys.exit(main())
