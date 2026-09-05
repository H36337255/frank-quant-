# GPT-6 / EP004 已配置環境

官方映像 freqtradeorg/freqtrade:2026.6；digest sha256:d451af021d5e08b70580c0eea5848534e9846b57391b34821c0a5814416397e6。已實際驗證版本、策略載入、配置schema、固定fee、1x及原loss完整性。

- submission/：GPT-6的策略與規定交付文件，以及GOAL、README_FOR_MODEL和原腳手架。
- data/train_valid/：120個檔案；20幣四周期OHLCV、mark、funding，2021-01-01至2025-06-30。
- G:\AI\EP004_Holdout_20260905：工作目錄外的TEST資料；2025-05/06只作預熱，計分2025-07-01至2026-07-01。
- source/：不修改的GitHub來源快照。
- audit/：原始日誌、階段命令、資料雜湊、凍結紀錄、評分、驗證與圖表。
- .analysis312/：穩定Python3.12分析環境。舊.venv以Python3.13 beta建立，發生DLL問題，不使用於正式統計。

使用者於2026-09-05授權依RUNBOOK下載行情後，已完成TRAIN/VALID與獨立TEST資料下載與邊界裁切。原始下載命令與日誌在audit/download.log及download_test.log；資料清冊data_manifest.json與data_manifest_test.json均為READY。沒有合成行情或用零資金費補缺。

compose.yaml服務gpt6預設離線、資料唯讀、只顯示版本，不啟動交易。實際Hyperopt/回測需取得Binance市場metadata，使用run_freqtrade_job.py記錄的官方容器命令；只有test階段掛載外部TEST目錄，且先驗證凍結雜湊。

完整可重現命令在submission/run.md。最後HTML是EP004_Codex_Report.html，所有未知與口徑限制均明載。
