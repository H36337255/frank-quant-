"""Render measured results and original validator outputs into a standalone HTML."""
import base64
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'audit'
SUB = ROOT / 'submission'
def load(p):
    return json.loads(p.read_text(encoding='utf-8'))
def fmt(v, pct=False):
    if v is None:
        return '未取得'
    if isinstance(v,int) and not pct:
        return str(v)
    return f'{v*100:.2f}%' if pct else f'{v:,.3f}'
def table(head, rows):
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>'+escape(str(h))+'</th>' for h in head) + '</tr></thead><tbody>' + ''.join('<tr>'+''.join('<td>'+escape(str(c))+'</td>' for c in row)+'</tr>' for row in rows) + '</tbody></table></div>'
def details(title, obj):
    text = obj if isinstance(obj,str) else json.dumps(obj,ensure_ascii=False,indent=2)
    return '<details><summary>'+escape(title)+'</summary><pre>'+escape(text)+'</pre></details>'
def figure(path, caption):
    if not path.exists():
        return '<p>圖表未產生：'+escape(path.name)+'</p>'
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f'<figure><img src="data:image/png;base64,{encoded}" alt="{escape(caption)}"><figcaption>{escape(caption)}</figcaption></figure>'

def main():
    metrics=load(SUB/'metrics.json')
    evidence=load(AUDIT/'score_evidence.json')
    validations=load(AUDIT/'script_validation.json')
    manifest=load(AUDIT/'data_manifest.json')
    hp=load(SUB/'hyperopt_results.json')
    config=load(SUB/'config.json')
    test=load(AUDIT/'test_metrics.json') if (AUDIT/'test_metrics.json').exists() else None
    test_section=''
    valid_dsr=json.loads(next(c['stdout'] for c in validations['checks'] if c['script']=='deflated_sharpe.py'))
    mc_valid=load(AUDIT/'mc.json')
    if test:
        tm,te=test['metrics'],test['evidence']
        test_section='<section><h2>04 · 凍結後 TEST 評測</h2><p>策略及參數先凍結，再於工作目錄外下載與掛載 TEST；未回頭調參。計分範圍為 2025-07-01 至 2026-07-01，2025-05/06 只作預熱。</p>'
        test_section+=table(['總收益','題目方式 Sharpe','已實現日回撤','成交筆數'],[(fmt(te['return_total'],True),fmt(tm['sharpe']),fmt(tm['max_drawdown'],True),tm['n_trades'])])
        test_section+=table(['多單','空單','多頭 PnL / USDT','空頭 PnL / USDT'],[(te['long_trades'],te['short_trades'],fmt(te['long_profit_abs']),fmt(te['short_profit_abs']))])
        test_stats=load(AUDIT/'script_validation_test.json')
        test_dsr=json.loads(next(c['stdout'] for c in test_stats['checks'] if c['script']=='deflated_sharpe.py'))
        test_section+=table(['原始統計腳本','VALID','TEST'],[('DSR（原腳本0.95門檻）',fmt(valid_dsr['DSR']),fmt(test_dsr['DSR'])),('MC交易序列 prob(profit)',fmt(mc_valid['prob_profit'],True),fmt(load(AUDIT/'mc_test.json')['prob_profit'],True))])
        test_section+='<p>本次 TEST 虧損，多頭損失超過空頭收益；這個答案沒有在最終評測取得正報酬。題目方式 Sharpe 以已實現平倉日計算，與 Freqtrade 顯示的 daily wallet balance Sharpe 不同，不混用。</p>'
        test_section+=details('TEST 原始成交評分與日期口徑',test)
        test_section+=details('TEST 原始 DSR 與 Monte Carlo 腳本輸出',load(AUDIT/'script_validation_test.json'))
        test_section+=figure(AUDIT/'mc_test.png','TEST：原始交易序列 Monte Carlo；不得視為實際組合錢包盈利機率')+'</section>'
    performance=[]
    labels={'ann_return':'年化收益（CAGR）','sharpe':'題目口徑 Sharpe','sortino':'Sortino','calmar':'Calmar',
            'max_drawdown':'已實現日淨值最大回撤','win_rate':'勝率','profit_factor':'Profit factor',
            'turnover_per_year':'年化雙邊名義換手','n_trades':'成交筆數','sharpe_net_of_costs':'扣成本後 Sharpe'}
    for key,label in labels.items():
        performance.append((label,fmt(metrics['train'][key],key in ['ann_return','max_drawdown','win_rate']),
                            fmt(metrics['valid'][key],key in ['ann_return','max_drawdown','win_rate'])))
    sides=[(s.upper(),evidence[s]['long_trades'],evidence[s]['short_trades'],
            fmt(evidence[s]['long_profit_abs']),fmt(evidence[s]['short_profit_abs']),
            fmt(evidence[s]['funding_fees_sum'])) for s in ['train','valid']]
    all_valid=all(c['status']=='VALID_RESULT' for c in validations['checks'])
    validation_rows=[(c['script'],c['returncode'],'已取得有效輸出' if c['status']=='VALID_RESULT' else '未取得有效輸出') for c in validations['checks']]
    # DSR and Monte Carlo results are printed by the unchanged upstream scripts.
    validation_details=''.join(details(c['script']+'：原始命令與輸出',c) for c in validations['checks'])
    images=figure(AUDIT/'charts/convergence_codex.png','原始 hyperopt_plot.py：驗證 Sharpe 與搜尋收斂')
    images+=figure(AUDIT/'charts/overfit_codex.png','原始 hyperopt_plot.py：訓練／驗證落差；圖中 argmax 未必等於固定 loss 選參')
    images+=figure(AUDIT/'mc.png','原始 mc_bootstrap.py：VALID 交易序列重抽樣；不是多倉並存的錢包淨值模擬')
    pct_return=fmt(evidence['valid']['return_total'],True)
    state='TRAIN / VALID / TEST 已回測；四項驗證有有效輸出' if all_valid and test else 'TRAIN / VALID 已回測；見各項驗證狀態'
    html=f'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GPT-6 · EP004 實測評測報告</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f3f5f3;color:#1b303a;font:16px/1.8 system-ui,"Microsoft JhengHei",sans-serif}}main{{max-width:1080px;margin:auto;padding:48px 28px}}h1{{font-size:42px;line-height:1.25;margin:12px 0}}h2{{font-size:24px}}header small{{color:#146a65;letter-spacing:.15em}}.status{{background:#e7f0ec;border-left:5px solid #146a65;padding:20px;margin:24px 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.card,section{{background:#fff;border:1px solid #d5dedb;border-radius:10px;padding:25px;margin:20px 0}}.card b{{display:block;font-size:30px}}.muted,figcaption{{color:#526873;font-size:14px}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #d5dedb;vertical-align:top}}th{{background:#edf3f0}}a{{color:#146a65}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.7 monospace;background:#f2f5f4;padding:18px;max-height:580px;overflow:auto}}details{{border-top:1px solid #d5dedb;padding:14px 0}}summary{{cursor:pointer;color:#146a65}}img{{max-width:100%;height:auto}}figure{{margin:22px 0}}code{{overflow-wrap:anywhere}}@media(max-width:650px){{main{{padding:25px 15px}}h1{{font-size:30px}}.cards{{grid-template-columns:1fr;gap:0}}.card{{margin:6px 0}}section{{padding:20px}}}}</style></head><body><main>
<header><small>EP004 / GPT-6 / MEASURED RESULTS</small><h1>雙向趨勢策略<br>實際跑完後的答案</h1><p>固定 20 幣、1x、單邊 0.06%，使用官方 Freqtrade 2026.6 與原始 EP004ValidLoss。</p><p class="muted">報告更新：{datetime.now(timezone.utc).isoformat()} · 策略 CodexCausalTrend</p><div class="status">{state}。VALID 正收益沒有延續至 TEST；本次策略在最終評測虧損。</div>
<div class="cards"><div class="card"><b>{pct_return}</b>VALID 總收益</div><div class="card"><b>{fmt(metrics['valid']['sharpe'])}</b>VALID 題目口徑 Sharpe</div><div class="card"><b>{hp['n_epochs']}</b>實際搜尋 epochs</div></div></header>
<section><h2>01 · 資料與可重現性</h2><p>原始題目及腳手架來自倉庫 commit <code>3b0c48c47ffeb42b0a2aecbdcaeb99618c9bc4e7</code>。倉庫未附原始行情；使用者後續明確授權依 RUNBOOK 第 2 節下載，因此本次行情來自 Binance 官方下載流程。</p><p>TRAIN/VALID 共 {manifest['actual_files']} 個資料檔，涵蓋 20 幣 × 四個 OHLCV 周期，加 1h mark 與 funding 檔。候選輸入已裁切為 2021-01-01 ≤ date &lt; 2025-07-01；沒有合成價格或補零 funding。TEST 僅在策略凍結後独立評分，不進入搜尋。資料本身仍可能存在交易所歷史缺口，詳見清冊。</p><p class="muted">官方映像 digest：sha256:d451af021d5e08b70580c0eea5848534e9846b57391b34821c0a5814416397e6</p>{details('資料清冊、實際日期與 SHA-256',manifest)}</section>
<section><h2>02 · 我的策略與選參</h2><p>4h 的對稱趨勢策略：上一根收盤偏離歷史均值超過 ATR 帶時入場，回穿均值退出，固定 10% 止損。所有訊號输入使用 shift(1)。搜尋空間為三個均值窗口 × 兩個波動帶，事前設定最多六輪，不因結果追加搜尋。</p>{details('最終設定與選參紀錄',config['_experiment'])}{details('設計說明',(SUB/'design.md').read_text(encoding='utf-8'))}</section>
<section><h2>03 · 真實回測績效</h2>{table(['指標','TRAIN','VALID'],performance)}<p>TRAIN／VALID 回測各自使用 --cache none、--fee 0.0006。Sharpe 以原始 loss 的函式重算；它按平倉日已實現 PnL 補齊零日，不是未實現部位逐日盯市淨值。</p>{table(['區間','多單','空單','多頭 PnL / USDT','空頭 PnL / USDT','funding_fees 原始合計'],sides)}<p class="muted">funding 合計保留 Freqtrade 原始欄位符號；回测 profit_abs 已包含引擎計入的交易成本。回撤與 Calmar 使用已實現日淨值，不能與不同口徑直接混比。</p>{details('指標公式、費率、槓桿與成交證據',evidence)}</section>
{test_section}<section><h2>05 · 原始 scripts 驗證</h2>{table(['腳本','退出碼','狀態'],validation_rows)}<p>因果性 PASS 只代表本次抽查點通過，並不是所有市場狀況的證明。DSR 的顯著性與 Monte Carlo 盈利機率以以下原始輸出為準，腳本執行成功不等於策略表現良好。</p>{validation_details}{images}</section>
<section><h2>05 · 解讀限制</h2><p>README 已揭露其他策略的 TEST 結果，因此本候選不是與原四模型完全同等的盲測。驗證集已用於選參，VALID 成績也不能當成從未看過的樣本外績效。固定 20 幣有倖存者偏差；趨勢規則容易在盤整反覆虧損，相關部位可能累積市場 beta。</p><p>原始 DSR 腳本使用首末成交日作為日索引，未必等於題目固定日曆。Monte Carlo 逐筆串接 profit_ratio，不能當作 20 倉位共同錢包的盈利機率。原 exporter 使用四捨五入 loss 配對，重複鍵核對見選參紀錄。</p>{details('風險自評',(SUB/'self_assessment.md').read_text(encoding='utf-8'))}</section>
<section><h2>06 · 交付檔案</h2><p><a href="submission/strategies/CodexCausalTrend.py">策略</a> · <a href="submission/config.json">設定</a> · <a href="submission/metrics.json">實測 metrics</a> · <a href="submission/hyperopt_results.json">每輪搜尋</a> · <a href="submission/run.md">重現命令</a></p><p><a href="audit/data_manifest.json">行情清冊</a> · <a href="audit/score_evidence.json">評分證據</a> · <a href="audit/script_validation.json">原始驗證輸出</a> · <a href="SETUP.md">環境配置</a></p></section>
<footer class="muted">報告只使用本次實際產生的結果；不存在的結果不補寫。保留原倉庫 MIT 授權。</footer></main></body></html>'''
    (ROOT/'EP004_Codex_Report.html').write_text(html,encoding='utf-8')
    print('Report generated from measured results:',ROOT/'EP004_Codex_Report.html')

if __name__=='__main__':
    main()
