"""Invoke unmodified upstream validators on this submission; record real failures."""
import hashlib
import json
import os
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EP = ROOT / "source/EP004_four-llm-quant-benchmark"
SUB = ROOT / "submission"
OUT = ROOT / "audit"
SCRIPTS = EP / "scripts"


def execute(name, args, need):
    script = SCRIPTS / name
    argv = [sys.executable, str(script)] + args
    if name == "factor_causality_check.py" and (OUT / "data_manifest.json").exists():
        argv = ["docker", "run", "--rm", "--network", "none", "--entrypoint", "python",
                "-v", f"{SUB}:/freqtrade/user_data",
                "-v", f"{ROOT / 'data/train_valid'}:/freqtrade/user_data/data:ro",
                "-v", f"{SCRIPTS}:/experiment_scripts:ro", "freqtradeorg/freqtrade:2026.6",
                "/experiment_scripts/factor_causality_check.py", "--strategy", "CodexCausalTrend"]
    try:
        environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
        process = subprocess.run(argv, cwd=SUB, capture_output=True, text=True, env=environment,
                                 encoding="utf-8", errors="replace", timeout=60)
        result = {"returncode": process.returncode, "stdout": process.stdout,
                  "stderr": process.stderr}
    except (OSError, subprocess.TimeoutExpired) as exc:
        result = {"returncode": None, "stdout": "", "stderr": str(exc)}
    successful = result['returncode'] == 0
    if name == 'factor_causality_check.py':
        successful = successful and '[PASS]' in result['stdout']
    return {"script": name, "argv": argv, "cwd": str(SUB),
            "sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
            "required_input": need, "status": "VALID_RESULT" if successful else "NO_VALID_RESULT", **result}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    checks = [
        execute("factor_causality_check.py", ["--strategy", "CodexCausalTrend", "--config",
                str(SUB / "config.json"), "--datadir", str(SUB / "data")],
                "Freqtrade runtime and real TRAIN/VALID OHLCV"),
        execute("deflated_sharpe.py", ["--hyperopt", str(SUB / "hyperopt_results.json"),
                "--trades", str(SUB / "backtest_results/valid.zip"), "--wallet", "10000"],
                "At least two valid trials plus actual chosen-strategy backtest trades"),
        execute("mc_bootstrap.py", ["--trades", str(SUB / "backtest_results/valid.zip"),
                "--iters", "5000", "--block", "10", "--seed", "20260905",
                "--out", str(OUT / "mc.json"), "--plot", str(OUT / "mc.png")],
                "Actual chosen-strategy trades"),
        execute("hyperopt_plot.py", ["--input", str(SUB / "hyperopt_results.json"),
                "--outdir", str(OUT / "charts"), "--tag", "codex"],
                "Actual hyperopt trials"),
    ]
    versions = {}
    for package in ["numpy", "pandas", "matplotlib", "freqtrade"]:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "python": sys.executable, "python_version": sys.version,
              "packages": versions, "checks": checks,
              "skipped": {
                  "make_video_charts.py": "Original four-model constants; not this candidate's measurements",
                  "make_metric_charts.py": "Original four-model constants/paths, including GATES; not a validator for this candidate",
                  "usage_cost.py": "Claude Code log format; not applicable to this Codex session; no cost imputed"
              },
              "note": "Causality uses the official container when a data manifest exists; other scripts use the host requirements environment. Each status follows its actual output."}
    (OUT / "script_validation.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for item in checks:
        print(item["script"], "exit=", item["returncode"])
        print((item["stderr"] or item["stdout"]).strip())
    return 2 if any(item["returncode"] != 0 for item in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
