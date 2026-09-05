# 最新評測狀態

本次已完成6輪搜尋、TRAIN/VALID/TEST實際回測、原scripts驗證及HTML報告。早期execution.json中的「缺少行情／Docker不可用」是歷史啟動失敗紀錄，後續使用者啟動Docker並授權依RUNBOOK下載資料後已排除。

策略在TEST虧損23.1079%，不是成功盈利的策略。所有績效來自真實成交，原始腳手架沒有修改。最新完整報告：../EP004_Codex_Report.html。最終檔案／規則核對：final_audit.json。

TRAIN總收益427.1526%，題目Sharpe1.19337；VALID總收益17.3684%，題目Sharpe0.50203；TEST總收益-23.1079%，同方法Sharpe-1.14645。TEST指標不加入規定僅TRAIN/VALID的metrics.json，另存test_metrics.json。策略於selection_frozen.json記錄的時間凍結，TEST於其後下載與評分，沒有再改參數。

VALID DSR0.6464、TEST DSR0.137，均不顯著。原MC的盈利序列比例41.84%／4.08%不是多倉共同錢包的真正盈利機率。因果檢查20幣共200點PASS。完整公式、日期日數差異、資料來源與非完全盲測限制見設計、自評與HTML。
