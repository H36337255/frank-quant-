# 從封存重現

在本資料夾開啟PowerShell。Docker使用官方 `freqtradeorg/freqtrade:2026.6`，原執行digest為 `sha256:d451af021d5e08b70580c0eea5848534e9846b57391b34821c0a5814416397e6`。

## 只重跑既有成交的统计驗證

使用穩定Python（原完成環境為3.12.14；避免3.13 beta）：

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -X utf8 -m pip install -r ./upstream/requirements.txt
New-Item -ItemType Directory -Force ./out | Out-Null
& ./.venv/Scripts/python.exe -X utf8 ./upstream/scripts/deflated_sharpe.py --hyperopt ./submission/hyperopt_results.json --trades ./submission/backtest_results/valid.zip --wallet 10000
& ./.venv/Scripts/python.exe -X utf8 ./upstream/scripts/mc_bootstrap.py --trades ./submission/backtest_results/valid.zip --iters 5000 --block 10 --seed 20260905 --out ./out/mc_valid.json --plot ./out/mc_valid.png
& ./.venv/Scripts/python.exe -X utf8 ./upstream/scripts/hyperopt_plot.py --input ./submission/hyperopt_results.json --outdir ./out --tag codex
```

TEST將上面trades改為test.zip、輸出另命名，不能覆蓋VALID。腳本未修改；DSR CLI依實際原始碼使用`--trades`。

## 重跑策略回測

先依原RUNBOOK準備並核對行情。固定20幣、30m/1h/4h/1d、真實mark/funding。TRAIN/VALID只留2021-01-01至2025-06-30；TEST放在工作根目錄外，需預熱資料。原始行情不隨本封存提交。

```powershell
$ArchiveRoot = (Get-Location).Path
$TrainingData = '<absolute TRAIN+VALID data directory>'
docker run --rm -v "${ArchiveRoot}/submission:/freqtrade/user_data" -v "${TrainingData}:/freqtrade/user_data/data:ro" freqtradeorg/freqtrade:2026.6 backtesting --strategy CodexCausalTrend --config /freqtrade/user_data/config.json --cache none --fee 0.0006 --timerange 20210101-20240630 --export trades
docker run --rm -v "${ArchiveRoot}/submission:/freqtrade/user_data" -v "${TrainingData}:/freqtrade/user_data/data:ro" freqtradeorg/freqtrade:2026.6 backtesting --strategy CodexCausalTrend --config /freqtrade/user_data/config.json --cache none --fee 0.0006 --timerange 20240701-20250630 --export trades
docker run --rm --network none --entrypoint python -v "${ArchiveRoot}/submission:/freqtrade/user_data" -v "${TrainingData}:/freqtrade/user_data/data:ro" -v "${ArchiveRoot}/upstream/scripts:/scripts:ro" freqtradeorg/freqtrade:2026.6 /scripts/factor_causality_check.py --strategy CodexCausalTrend
```

最後在策略已固定的情況下，改掛獨立TEST資料目錄、timerange改20250701-20260701，保持費率及cache參數。不要把TEST掛入搜尋。

要重跑整次Hyperopt，請另建乾淨user_data副本，保留原始證據；初始buy_params為trend_window=120、entry_band=1.0，搜尋前不能套用封存的最終策略參數JSON。完整指令為hyperopt、--spaces buy、--epochs 6、-j 20、--random-state 20260905、--hyperopt-loss EP004ValidLoss、--timerange 20210101-20250630、--fee 0.0006。不加--cache none，不改固定規則。

原實驗真正的每階段命令及時間是audit/*_20260905.json。`audit/*.py`為原本機輔助程式，其中硬編碼的來源／資料位置需按原檔記錄配置；本文件上面的命令才是此封存的可攜式入口。封存後未再執行新一輪搜尋。
