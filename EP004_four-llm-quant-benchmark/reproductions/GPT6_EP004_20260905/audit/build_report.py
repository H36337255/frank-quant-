"""Build a self-contained HTML assessment from recorded checks, never invented metrics."""
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "audit"
SUB = ROOT / "submission"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def cell(value):
    return escape(str(value))


def table(headers, rows):
    head = "".join(f"<th scope='col'>{cell(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in row) + "</tr>" for row in rows)
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def detail(title, obj):
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2)
    return f"<details><summary>{cell(title)}</summary><pre>{cell(text)}</pre></details>"


def main():
    audit = read_json(AUDIT / "execution.json")
    verification = read_json(AUDIT / "script_validation.json")
    metrics = read_json(SUB / "metrics.json")
    trials = read_json(SUB / "hyperopt_results.json")
    commit = audit["source_commit"]["stdout"].strip()
    assert trials["n_epochs"] == 0 and not trials["trials"]
    assert all(value is None for split in ["train", "valid"] for value in metrics[split].values())
    assert all(c["returncode"] != 0 for c in verification["checks"])
    reasons = {
        "factor_causality_check.py": "ModuleNotFoundError: freqtrade；未載入策略、未比較任何真實行情時點。",
        "deflated_sharpe.py": "有效 trial 太少，無法估計 Sharpe 方差；沒有 DSR 數值。",
        "mc_bootstrap.py": "FileNotFoundError: valid.zip；沒有成交序列可重抽樣。",
        "hyperopt_plot.py": "沒有 trials；未產生搜尋收斂或過擬合圖。",
    }
    validator_table = table(["原始腳本", "退出碼", "本次結果"],
                            [(c["script"], c["returncode"], reasons[c["script"]]) for c in verification["checks"]])
    rule_table = table(["考試要求", "本次設定或證據", "判定範圍"], [
        ("固定 20 個永續合約", "與 scaffold/base_config.json 完全相同", "設定核對完成"),
        ("雙向交易", "can_short=True；對稱 enter_long / enter_short", "只有程式實作，實際雙向成交未驗證"),
        ("1x 與固定本金", "未覆寫 leverage；10000 USDT；20 倉位上限", "設定／原始碼核對，執行未驗證"),
        ("單邊費用 0.06%", "config=0.0006；命令 --fee 0.0006", "設定核對，實際扣費未驗證"),
        ("真實 funding", "原始 funding 資料缺失", "未驗證；metrics 使用 null"),
        ("固定目標函數", "EP004ValidLoss 原檔 SHA-256 一致", "完整性核對完成；尚未評分"),
        ("Hyperopt ≤2000 epochs、-j 20", "計畫 6；完成 0；seed=20260905", "已嘗試，Docker 啟動失敗"),
        ("無未來函數", "訊號全部使用 shift(1) 與向後滾動", "設計審閱；原始因果腳本未完成"),
        ("只用 TRAIN / VALID", "未取得任何行情；沒有執行 TEST", "資料限制維持；非完全盲測，見限制"),
        ("指定交付檔案", "策略 + config/run/metrics/hyperopt_results/design/self_assessment", "檔案草案齊備；數值與正式交卷未完成"),
    ])
    performance = table(["指標", "TRAIN", "VALID"],
                        [(key, "未量測（null）", "未量測（null）") for key in metrics["train"]])
    attempts = table(["執行階段", "退出碼", "成功回測數"],
                     [(name, run["returncode"], 0) for name, run in zip(
                         ["Hyperopt", "TRAIN backtesting", "VALID backtesting"], audit["execution_attempts"])])
    logs = "".join(detail(c["script"] + " · 命令與原始輸出", c) for c in verification["checks"])
    logs += detail("Docker / Hyperopt / TRAIN / VALID 原始執行紀錄", {
        "docker_version": audit["docker_version"], "attempts": audit["execution_attempts"]})
    integrity = detail("固定設定、腳手架雜湊及語法檢查", {
        "config_equal": audit["protected_config_equal"], "hashes": audit["scaffold_integrity"],
        "syntax": audit["syntax"], "strategy_sha256": audit["strategy_sha256"],
        "config_sha256": audit["config_sha256"]})
    source_url = f"https://github.com/H36337255/frank-quant-/tree/{commit}/EP004_four-llm-quant-benchmark"
    docs = "".join(detail(name, (SUB / name).read_text(encoding="utf-8"))
                   for name in ["design.md", "self_assessment.md", "run.md"])
    html = f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>EP004｜Codex 實驗評測報告</title>
<style>
:root{{--ink:#182b36;--muted:#546775;--paper:#f3f5f3;--line:#d5dedb;--accent:#146a65;--warn:#934719}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 system-ui,"Microsoft JhengHei",sans-serif}}
main{{max-width:1080px;margin:auto;padding:56px 32px 72px}}.eyebrow{{letter-spacing:.16em;color:var(--accent);font-size:12px;font-weight:750}}
h1{{font-size:clamp(30px,5vw,50px);line-height:1.2;letter-spacing:-.03em;margin:16px 0}}h2{{font-size:23px;line-height:1.4;margin:0 0 20px}}h3{{font-size:18px;margin:25px 0 10px}}
p{{margin:12px 0}}.lede{{max-width:780px;font-size:19px;color:var(--muted)}}.meta{{font-size:13px;color:var(--muted);overflow-wrap:anywhere}}
.status{{border-left:5px solid #bf6b35;background:#fff3e8;padding:20px 24px;margin:28px 0}}.status strong{{color:var(--warn);font-size:20px}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:28px 0}}.stat{{padding:22px;background:white;border:1px solid var(--line);border-radius:10px}}.stat b{{display:block;font-size:36px;line-height:1.3;font-variant-numeric:tabular-nums}}.stat span{{color:var(--muted);font-size:14px}}
nav{{display:flex;gap:18px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding:10px 0 22px;margin-bottom:28px}}a{{color:var(--accent);text-underline-offset:3px}}nav a{{font-size:14px}}
section{{background:white;border:1px solid var(--line);border-radius:12px;padding:30px;margin:22px 0}}.number{{color:var(--accent);font-size:13px;letter-spacing:.15em;display:block;margin-bottom:8px}}
.table-wrap{{overflow-x:auto;margin:18px 0}}table{{border-collapse:collapse;width:100%;font-size:14px}}th{{text-align:left;background:#eef4f1;color:#344e58}}th,td{{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}}td:first-child{{font-weight:600}}code{{font-size:13px;overflow-wrap:anywhere;background:#eef4f1;padding:2px 5px;border-radius:3px}}
details{{border-top:1px solid var(--line);padding:14px 0}}summary{{cursor:pointer;color:var(--accent);font-size:14px;font-weight:600}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f2f5f4;padding:18px;border-radius:6px;font:12px/1.7 ui-monospace,Consolas,monospace;max-height:620px;overflow:auto}}
.note{{color:var(--muted);font-size:14px}}footer{{color:var(--muted);font-size:13px;padding-top:22px}}ul{{padding-left:22px}}
@media(max-width:650px){{main{{padding:30px 16px}}section{{padding:22px 18px}}.stats{{grid-template-columns:1fr;gap:10px}}.stat{{padding:16px}}.stat b{{font-size:28px}}th,td{{padding:10px;min-width:105px}}}}
@media print{{body{{background:white}}main{{padding:0;max-width:none}}nav{{display:none}}section{{break-inside:avoid;border-radius:0}}details{{break-inside:avoid}}pre{{max-height:none}}a{{color:inherit}}}}
</style></head><body><main>
<header><div class="eyebrow">EP004 / REPRODUCTION AUDIT / CODEX</div>
<h1>同一道量化題，<br>本次證據到哪裡？</h1>
<p class="lede">CodexCausalTrend 的策略答案、考試規則核對與原始脚本驗證紀錄。所有績效欄位都以實際執行證據為準。</p>
<p class="meta">來源 commit：{cell(commit)}<br>驗證時間（UTC）：{cell(verification['checked_at_utc'])}</p>
<div class="status"><strong>實驗未完成 · 缺少倉庫原始行情</strong><p>已寫出策略並嘗試執行，但沒有成功回測或有效 Hyperopt trial。原始驗證腳本均未取得有效結果，因此無法判定收益、穩健性或是否通過考試。</p></div>
<div class="stats"><div class="stat"><b>0</b><span>成功完成的回測</span></div><div class="stat"><b>0 / 6</b><span>完成 epochs / 計畫上限</span></div><div class="stat"><b>4</b><span>原始驗證腳本已嘗試；有效結果 0</span></div></div>
<nav aria-label="報告章節"><a href="#data">資料證據</a><a href="#answer">我的答案</a><a href="#rules">規則核對</a><a href="#checks">腳本驗證</a><a href="#metrics">績效</a><a href="#files">檔案與後續</a></nav></header>
<section id="data"><span class="number">01 / DATA</span><h2>倉庫提供題目與結果，未附原始行情</h2>
<p>本次以 <a href="{source_url}">指定倉庫 EP004 固定版本</a> 為唯一實驗內容來源。已讀取 README、RUNBOOK、<code>prompts/GOAL.md</code>、<code>prompts/README_FOR_MODEL.md</code>、所用腳手架及驗證腳本。</p>
<p>整份主分支共有 <strong>{audit['tracked_file_count']} 個追蹤檔案</strong>。盤點沒有 feather、parquet、CSV、zip 等行情或回測封存檔，也沒有 OHLCV、mark、funding 的獨立資料檔。既有 JSON 為設定、其他候選的 metrics 與 hyperopt 結果。2026-09-05 查詢該倉庫公開 Release 清單得到 <code>[]</code>。</p>
<p>RUNBOOK 第 2 節要求另行執行 <code>download-data</code>。在本次「只能使用倉庫資料」的限制下，無法用交易所下載或合成數據補足。以上結論限於已核對的主分支與公開 Release。</p>
<p class="note">執行工具使用本機 Python 及已安裝的 numpy/pandas；這些是計算環境，不是額外市場資料。</p>
{detail('完整追蹤檔案清單與資料候選盤點', {'files': audit['tracked_files'], 'data_candidates': audit['possible_raw_data_or_archives'], 'json_paths': audit['json_paths_for_manual_inventory_review']})}</section>
<section id="answer"><span class="number">02 / ORIGINAL ANSWER</span><h2>我的答案：4h 雙向趨勢與波動帶</h2>
<p>使用原生 IStrategy，各幣套用相同的對稱規則。上一根收盤高於歷史均價加波動帶則做多，低於均價減波動帶則做空。回到均價另一側退出；固定 10% 止損。</p>
{table(['設計項目', '候選設定', '理由與限制'], [
('趨勢中心', '60 / 120 / 180 根的簡單均值', '10 / 20 / 30 天視窗；預設 120，尚未優化'),
('入場帶', '30 根 true range 均值 × 0.5 / 1.0', '入場與退出分離以減少來回交易；成效未驗證'),
('資料時點', '所有訊號輸入 shift(1)', '只用先前資料；動態因果檢查尚未完成'),
('搜尋', '最多 6 epochs，seed 20260905，-j 20', '僅 6 個參數組合；不保證 Hyperopt 遍歷全部'),
('成本與倉位', '0.0006 / side；1x；固定 20 幣', '沿用原規則；真實扣費與 funding 未驗證')])}
<p>這些是事前候選設計理由，沒有已量測的優勢。預設參數不能稱為最優；震盪、反轉延遲與高度相關部位都是主要風險。</p>
<p class="note">README 已公開 TEST 熊市與其他候選結果，閱讀 README 後的本次答案不能宣稱與原四模型相同的完全盲測。</p>{docs}</section>
<section id="rules"><span class="number">03 / EXAM RULES</span><h2>設定符合，不代表執行驗收通過</h2>{rule_table}{integrity}
<p class="note">metrics 的 null 是未知值，並非零收益。funding_included=null 與未填實測數字明確不滿足正式交卷 schema 的完成要求。</p></section>
<section id="checks"><span class="number">04 / VERIFICATION</span><h2>原始 scripts 的實際執行結果</h2>
<p>直接呼叫來源倉庫的原始檔案，保存命令、退出碼與原始輸出。沒有修改驗證器以使其通過，也沒有提供替代成交資料。</p>{validator_table}
<h3>Hyperopt 與回測啟動嘗試</h3>{attempts}<p>Docker 在一般使用者權限下仍無可連線的 Docker Desktop Linux 引擎；三條命令在容器啟動階段停止。因果腳本另以本機 Python 嘗試，因沒有 freqtrade 模組而停止。</p>
<h3>未套用的其他 scripts</h3><p><code>make_video_charts.py</code> 與 <code>make_metric_charts.py</code> 含原四模型常數／路徑；後者的 GATES 亦含固定通過標記。這些圖不能視為本次實測結果。<code>usage_cost.py</code> 讀取 Claude Code 日誌，與本次 Codex 執行不適用，因此成本未估算。</p>
<h3>驗證口徑限制</h3><p>EP004ValidLoss 按平倉日彙總已實現 PnL，使用起始錢包、零交易補零日及 sqrt(365)。它不等於每日未實現部位盯市曲線。DSR 腳本的日索引只覆蓋首末成交日，與固定評分日期未必相同；Monte Carlo 以每筆 profit_ratio 串接複利，不是多倉並存下的真實錢包淨值。未來即使執行成功，報告也需保留這些限制。</p>
{logs}{detail('驗證 Python 與依賴版本', {'python': verification['python'], 'version': verification['python_version'], 'packages': verification['packages']})}</section>
<section id="metrics"><span class="number">05 / PERFORMANCE</span><h2>目前沒有可評分的績效</h2>{performance}
<p>DSR、Monte Carlo 盈利機率、多空收益拆解、alpha、beta、搜尋收斂與資金曲線均未取得。本報告沒有繪製推測曲線，也不以原作者或其他候選數字代填。</p>
<p class="note">此處評估的是完成狀態與證據，不為尚未執行的策略打績效分數。</p></section>
<section id="files"><span class="number">06 / DELIVERABLES</span><h2>可檢查的交付與下一步</h2>
<ul><li><a href="submission/strategies/CodexCausalTrend.py">我的策略原始碼</a> · <a href="submission/config.json">候選設定</a></li>
<li><a href="submission/design.md">設計說明</a> · <a href="submission/self_assessment.md">風險自評</a> · <a href="submission/run.md">重現命令</a></li>
<li><a href="submission/metrics.json">未量測指標紀錄</a> · <a href="submission/hyperopt_results.json">零次搜尋紀錄</a></li>
<li><a href="audit/execution.json">環境與回測原始證據</a> · <a href="audit/script_validation.json">scripts 原始驗證證據</a></li>
<li><a href="audit/verify_and_attempt.py">資料核對／啟動檢查程式</a> · <a href="audit/run_repository_checks.py">原始驗證器呼叫程式</a> · <a href="audit/build_report.py">本報告產生器</a></li></ul>
<p>完成實驗首先需要能追溯至本倉庫的 20 幣 TRAIN/VALID OHLCV、mark、funding 原檔，並維持 TEST 隔離。若這些檔案未在倉庫內提供，需要補上其倉庫位置，或由使用者明確修改資料來源限制。準備 Freqtrade 2026.6 後，才可完成搜尋、回測及腳本驗證。</p>
<p class="note">已保留原 MIT <a href="audit/LICENSE">授權</a>。本報告為可離線開啟的單一 HTML；附檔連結需與 QuantExperiment 目錄一同保存。</p></section>
<footer>Codex · EP004 reproducibility assessment · 所有未知結果保持未知。<br>報告由已保存的 execution.json 與 script_validation.json 生成。</footer>
</main></body></html>"""
    target = ROOT / "EP004_Codex_Report.html"
    target.write_text(html, encoding="utf-8")

    class LinkCheck(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links, self.ids = [], set()
        def handle_starttag(self, tag, attrs):
            attr = dict(attrs)
            if "id" in attr:
                self.ids.add(attr["id"])
            if tag == "a":
                self.links.append(attr.get("href", ""))
    parser = LinkCheck()
    parser.feed(html)
    for href in parser.links:
        if href.startswith("#"):
            assert href[1:] in parser.ids, href
        elif not href.startswith("https://"):
            assert (ROOT / unquote(href)).is_file(), href
    assert "<script" not in html and "<img" not in html
    print("Created", target)
    print("HTML parsed; all local links/anchors resolve; metrics are null; script failures preserved.")


if __name__ == "__main__":
    main()
