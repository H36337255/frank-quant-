# GPT-6 · EP004 量化實驗（2026-09-05）

本資料夾是一次已完成實驗的獨立封存：依原題目設計 CodexCausalTrend，使用官方 Freqtrade 2026.6、原始 EP004ValidLoss、固定20幣、1x及單邊0.06%，完成6輪搜尋與TRAIN／VALID／TEST回測。

入口：[HTML完整評測報告](EP004_Codex_Report.html)（下載後以瀏覽器開啟；圖片已內嵌）。

| 區間 | 總收益 | 題目方式 Sharpe |
|---|---:|---:|
| TRAIN | +427.15% | 1.193 |
| VALID | +17.37% | 0.502 |
| TEST | -23.11% | -1.146 |

TEST虧損，不能宣稱策略成功。原始因果腳本抽查200點PASS；VALID／TEST DSR為0.6464／0.137，均未達原腳本0.95門檻。Sharpe、回撤與統計限制見報告，不混用不同口徑。

## 檔案

- `submission/`：我的策略、引擎參數、config、設計、自評、metrics及全部6輪搜尋結果。
- `submission/backtest_results/`：三段實際成交zip，可直接交給原統計腳本。
- `audit/`：原始執行命令、日誌、資料清冊、凍結與完整性紀錄、驗證結果、圖表；歷史輔助程式保留供審閱。
- `upstream/`：所用原始題目、腳手架、驗證腳本與requirements快照，保留MIT授權。
- [REPRODUCE.md](REPRODUCE.md)：從這份封存資料夾重跑驗證／回測的可攜式命令。

本封存不包含原始行情、Python虛擬環境或Docker快取。原始每輪 .fthypt 以 `audit/raw_hyperopt.zip` 保存，避免漏掉重新核對匯出配對所需的證據。

## 來源與限制

原題目來源：[frank-quant- / EP004](https://github.com/H36337255/frank-quant-/tree/3b0c48c47ffeb42b0a2aecbdcaeb99618c9bc4e7/EP004_four-llm-quant-benchmark)。倉庫未提供行情；使用者後續授權依RUNBOOK第2節從Binance下載。行情雜湊與邊界記錄在清冊中，不能證明與原作者資料逐位元一致。

README事前已公開原模型TEST結果，所以不是與原考試完全等價的盲測。此候選本身則先凍結策略與參數，再於工作目錄外下載TEST並評分，未回頭調參。

`audit/final_audit.json` 是原工作目錄完成時的紀錄；其中 `source_git_clean` 僅指當時來源快照未修改，不表示本次封存倉庫工作樹狀態。部分歷史JSON／run.md包含當時的Windows絕對路徑；它們是執行證據，不應直接當作其他機器的路徑。可攜式操作請依REPRODUCE.md。
