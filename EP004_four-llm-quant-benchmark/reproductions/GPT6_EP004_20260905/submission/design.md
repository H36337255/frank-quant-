# GPT-6 的 EP004 答案：雙向趨勢與波動帶

已完成官方 Freqtrade 2026.6 的 6 輪 Hyperopt、TRAIN／VALID／TEST 回測及原始驗證腳本。來源題目版本為 `3b0c48c47ffeb42b0a2aecbdcaeb99618c9bc4e7`。資料原先不在倉庫，使用者後續授權依 RUNBOOK 第 2 節自 Binance 下載。TEST 在參數凍結後才於工作目錄外準備並評分。

## 策略設計

採一般 IStrategy 趨勢策略，固定 20 幣各自套用相同對稱規則，不依表現挑幣。4h 是事前決定：降低訊號評估頻率，同時保留比日線更快的退出反應；不是搜尋其他周期後挑出的結果。

使用過去 60／120／180 根收盤的簡單均值作為趨勢中心，過去 30 根 true range 的簡單均值作為波動尺度。前一根收盤超過中心加 0.5／1 倍波動尺度時做多，低於中心減波動尺度時做空；回穿均值退出。歷史成交量及波動必須為正。入場帶與中心退出形成遲滯區，但實測仍有大量交易，不能宣稱已有效解決換手成本。

固定 10% 止損，沒有最低持倉、加倉或槓桿覆寫，預設 1x。錢包 10000、max_open_trades=20、unlimited stake、tradable_balance_ratio=0.99 照原設定。全部訊號輸入 shift(1)，向後滾動，不使用全樣本正規化；實際執行另有引擎訊號延遲。

## 搜尋與選參

事前預算為 6 epochs，seed 20260905，-j 20，原封不動使用 EP004ValidLoss。所有參數在 buy space，三種均值預先全部計算，每輪 entry／exit 再選用，避免參數在 populate_indicators 內被 Hyperopt 快取。

實際完成 6 輪，只有 5 組不同參數。第 1、4 輪重複，不追加搜尋。按原始 loss 最低值選第 6 輪：trend_window=180、entry_band=1.0，loss=-0.6131839648663211。該輪合併區間按平倉日拆出的 TRAIN Sharpe=1.078899647252134、VALID Sharpe=0.7684225256615921；多單1530、空單1541。

使用原 export_hyperopt.py 匯出全部 6 輪，再從原始 .fthypt 每輪真實成交重新計算 Sharpe／loss 核對：所有匯出分數、參數配對一致。重複 loss 對應相同參數和分數，本次未見不同分數被錯接。證據在 ../audit/selection_frozen.json。策略、引擎參數檔、config、搜尋結果都已保存凍結雜湊，TEST 前後不得變更。

## 正式回測結果與口徑

正式 TRAIN、VALID 各自從 10000 USDT 開始，不能把合併 Hyperopt 分段分數直接充當單獨回測結果。正式 TRAIN 共2325筆，總收益427.1526%，题目口徑 Sharpe=1.19337；VALID 共766筆，總收益17.3684%，Sharpe=0.50203。TEST 共803筆，總收益-23.1079%，相同已實現 PnL 方法的 Sharpe=-1.14645。這些是真實回測，不代表策略成功。

Sharpe 原樣呼叫 EP004ValidLoss._sharpe_daily：按 close_date 彙總 profit_abs／初始本金、補零日、樣本標準差、sqrt(365)。不等於 Freqtrade 的 daily wallet balance（盯市）Sharpe。原函式 TRAIN 日索引包含 VALID_START，且 RUNBOOK 的日期端點與自然語言月份邊界略有不同，照原命令保留不修訂。

metrics.json 僅包含 TRAIN／VALID。其他指標的完整公式在 ../audit/score_evidence.json：CAGR、零目標 downside-RMS Sortino、已實現日淨值回撤及 Calmar、逐筆勝率與 Profit factor。換手採兩倍入場名義本金／初始資金／年數，是名義換手近似。TEST 獨立存 ../audit/test_metrics.json，其固定計分日曆含366日，原 DSR 腳本依首末成交只取365日，兩者差異明載。

## 成本、資料與驗證

單邊0.0006；依原 base_config 註解已含滑點代理，slippage_bps=0 表示沒有另加第二層滑點，不表示真實市場沒有滑點。已核對所有匯出交易費率0.0006、槓桿1x及真實 funding_fees 欄位。資料完整性、日期、缺口、SHA-256 在資料清冊中；不合成缺值，不以零 funding 替代。

原 factor_causality_check.py 在凍結參數下通過20幣共200個抽查點，最大全量／截斷差=0。VALID DSR=0.6464，不顯著；TEST DSR=0.137，也不顯著。原 Monte Carlo 的 VALID／TEST prob(profit) 分別為41.84%／4.08%，但其逐筆複利模型不是多倉並存的實際錢包，不能把它當真實組合盈利機率。搜尋圖雖提示末段仍改善，本次遵守事前六輪預算，不根據事後圖表增加搜尋。
