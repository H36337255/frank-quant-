# 實際重現流程

工作目錄：G:\AI\codex\QuantExperiment。交易引擎固定官方 freqtradeorg/freqtrade:2026.6；已拉取 digest sha256:d451af021d5e08b70580c0eea5848534e9846b57391b34821c0a5814416397e6。

## 已配置

submission/ 是 GPT-6 user_data，含 GOAL.md、README_FOR_MODEL.md、策略、config.json、hyperopts/EP004ValidLoss.py 與根 export_hyperopt.py。原檔來源在 source/EP004_four-llm-quant-benchmark，未修改。TRAIN/VALID資料在 data/train_valid，TEST獨立在 G:\AI\EP004_Holdout_20260905。只使用已驗收的資料清冊，所有實驗掛載行情唯讀。

## 實際命令

从 G:\AI\codex 執行以下已檢入的命令記錄程式；每一階段完整 docker argv、時間、exit code 均保存至 audit/<stage>_20260905.json，日誌同名.log。

```powershell
python QuantExperiment/audit/run_freqtrade_job.py hyperopt
python QuantExperiment/audit/run_freqtrade_job.py export
python QuantExperiment/audit/run_freqtrade_job.py train
python QuantExperiment/audit/run_freqtrade_job.py valid
python QuantExperiment/audit/run_freqtrade_job.py test
```

Hyperopt 已實際完成一次，seed20260905、6epochs、-j20、--spaces buy、--hyperopt-loss EP004ValidLoss、timerange20210101-20250630、--fee0.0006。防護會拒絕在已有 .fthypt 的目录重复搜尋；要重現請使用新的乾淨 user_data副本，不刪除既有證據。需重跑完整搜尋時，將初始 buy_params 恢復成設計前的120/1.0並移開副本中的匯出策略參數檔，避免把最終參數當成初始條件。原始搜尋 epoch紀錄為權威。

原 export_hyperopt.py 匯出6輪。audit/audit_selection.py 以原始成交逐輪重算 loss，選第6輪180/1.0，保存selection_frozen.json。現有策略buy_params、策略JSON及config參數紀錄一致；所有正式回測使用此固定設定。

TRAIN命令區間20210101-20240630，VALID為20240701-20250630，TEST為20250701-20260701；三者全部 --cache none、--fee0.0006、--export trades。不傳 --timeframe。TEST啟動前核對凍結雜湊。

## 評分與原 scripts 驗證

```powershell
docker run --rm --network none --entrypoint python -v G:/AI/codex/QuantExperiment:/experiment -v G:/AI/codex/QuantExperiment/submission:/freqtrade/user_data freqtradeorg/freqtrade:2026.6 /experiment/audit/score_submission.py
docker run --rm --network none --entrypoint python -v G:/AI/codex/QuantExperiment:/experiment -v G:/AI/codex/QuantExperiment/submission:/freqtrade/user_data freqtradeorg/freqtrade:2026.6 /experiment/audit/score_submission.py --test-only
& 'G:\AI\codex\QuantExperiment\.analysis312\Scripts\python.exe' -X utf8 QuantExperiment/audit/run_repository_checks.py
& 'G:\AI\codex\QuantExperiment\.analysis312\Scripts\python.exe' -X utf8 QuantExperiment/audit/run_test_statistics.py
python QuantExperiment/audit/build_results_report.py
```

在回測JSON所記錄的zip上建立同內容的train.zip、valid.zip、test.zip別名，供原腳本明确读取，不依賴「最新一份」推測。原 deflated_sharpe.py 接受 --trades，RUNBOOK 的 --backtest 拼法與原程式不符，此處依實際CLI使用 --trades，不改腳本。

分析使用穩定Python3.12.14、numpy2.3.5、pandas3.0.1、matplotlib3.11.1，均滿足原requirements。較早的Python3.13 beta環境曾DLL失敗，保留紀錄但不作正式分析環境。四個驗證腳本均保持原檔；因果在官方容器跑，其他分析在.analysis312。TEST另跑DSR與MC。MC固定seed20260905、iters5000、block10。

## 文件與限制

metrics.json 僅含TRAIN與VALID；TEST在audit/test_metrics.json。公式、原始交易成本核對在score_evidence.json。圖表／驗證原始輸出在script_validation.json、script_validation_test.json。最終HTML在../EP004_Codex_Report.html。原先的execution.json與初次REPORT反映資料尚未提供的歷史狀態，最新狀態以final_audit.json為準。
