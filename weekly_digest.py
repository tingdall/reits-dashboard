#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REITs 周度纪要（公募 + 机构间 合并版）
- 每周一生成，读取当日两份快照与变更记录，输出对比视角的纪要
- 用法：python weekly_digest.py [--force]
- 输出：weekly/REITs周度纪要-YYYY-Www.md
"""
import json
import os
import sys
from datetime import date

BASE = os.path.dirname(os.path.abspath(sys.argv[0]))
WEEKLY_DIR = "weekly"

GONG_SNAP, GONG_CHG = "gongmu_snapshot.json", "gongmu_changes.json"
ORG_SNAP, ORG_CHG = "reits_snapshot.json", "reits_changes.json"

# 机构间状态码 → 归类
ORG_PASS = {"4"}
ORG_RUNNING = {"0", "1", "2", "3", "10", "11"}
ORG_STOP = {"8", "9"}


def load(path):
    p = os.path.join(BASE, path)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def fmt_amt(v):
    return f"{v:,.2f}" if isinstance(v, (int, float)) else "—"


def esc(s):
    return (str(s if s is not None else "")
            .replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


HTML_CSS = """
:root{--bg:#faf9f7;--card:#fff;--ink:#1f1d1b;--ink2:#4a453f;--muted:#7d766c;
--line:#e7e1d7;--line2:#f0ebe3;--acc:#d94016;--wash:#fdf3ee;--wash-line:#f6dcd0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink2);font-size:15px;line-height:1.7;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
-webkit-font-smoothing:antialiased;overflow-x:hidden;max-width:100%}
.wrap{max-width:820px;width:100%;margin:0 auto;padding:0 18px 56px}
header{padding:34px 0 22px;border-bottom:1px solid var(--line)}
.badge{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.08em;color:var(--acc);
background:var(--wash);border:1px solid var(--wash-line);border-radius:999px;padding:4px 12px}
h1{font-size:clamp(22px,5vw,30px);margin:14px 0 8px;color:var(--ink);font-weight:800;letter-spacing:-.02em;line-height:1.3}
.meta{font-size:13px;color:var(--muted);margin:0}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:22px 0 6px}
@media(max-width:620px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 14px 12px;
box-shadow:0 1px 2px rgba(31,29,27,.04),0 10px 24px -16px rgba(217,64,22,.5)}
.stat .n{font-size:clamp(20px,4.4vw,26px);font-weight:800;color:var(--acc);letter-spacing:-.02em;line-height:1.1;
font-variant-numeric:tabular-nums}
.stat .k{font-size:12px;color:var(--muted);margin-top:5px}
section{margin-top:30px}
h2{font-size:17px;color:var(--ink);font-weight:750;margin:0 0 12px;letter-spacing:-.01em;
padding-left:11px;border-left:3px solid var(--acc);line-height:1.3}
.tw{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid var(--line);border-radius:12px;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:520px}
th{background:#faf9f6;text-align:left;font-weight:700;color:var(--ink);padding:10px 12px;
border-bottom:1px solid var(--line);font-size:12.5px;white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid var(--line2);vertical-align:top}
tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.total{font-weight:700;color:var(--ink)}
.insight{background:var(--wash);border:1px solid var(--wash-line);border-radius:12px;padding:14px 16px;
margin-top:12px;font-size:14px;color:var(--ink2)}
.insight b{color:var(--acc)}
ul{margin:0;padding-left:20px}
li{margin-bottom:7px}
.empty{color:var(--muted);font-size:14px;padding:10px 2px}
footer{margin-top:34px;padding-top:16px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted);line-height:1.8}
"""


def build_html(year, week, start, today, g_items, o_items, g_amt, o_amt,
               g_cnt_amt, o_cnt_amt, g_running, g_pass, g_stop,
               o_running, o_pass, o_stop, g_avg, o_avg,
               g_add, g_st, o_add, o_st, all_add, all_st, points):
    def rows_add():
        if not all_add:
            return '<tr><td colspan="6" class="empty">本周无新增项目</td></tr>'
        out = []
        for seg, x in all_add[:40]:
            out.append(
                '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td class="num">{}</td><td>{}</td></tr>'.format(
                    seg, esc((x.get("name") or "")[:60]), esc(x.get("ex", "")),
                    esc(x.get("ptype", "")), fmt_amt(x.get("amt")), esc(x.get("sname", ""))))
        return "".join(out)

    def rows_st():
        if not all_st:
            return '<tr><td colspan="4" class="empty">本周无状态变化</td></tr>'
        out = []
        for seg, x in all_st[:50]:
            out.append(
                '<tr><td>{}</td><td>{}</td><td>{}</td><td>{} → {}</td></tr>'.format(
                    seg, esc((x.get("name") or "")[:60]), esc(x.get("ex", "")),
                    esc(x.get("from") or "—"), esc(x.get("to") or "—")))
        return "".join(out)

    pts = "".join(f"<li>{p[2:]}</li>" for p in points)   # 去掉 md 的 "- "
    ga, oa = fmt_amt(g_amt), fmt_amt(o_amt)
    g_rate = f"{g_cnt_amt}/{len(g_items)}"
    o_rate = f"{o_cnt_amt}/{len(o_items)}"
    multi = (o_avg / g_avg) if g_avg else 0
    struct = ("机构间以单一大额项目为主，公募更分散。" if o_avg > g_avg else "公募单项目体量更大。")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>REITs 周度纪要 · {year}-W{week:02d}</title>
<style>{HTML_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <span class="badge">周度纪要 · {year}-W{week:02d}</span>
    <h1>REITs 市场周度纪要</h1>
    <p class="meta">统计区间 {start} ~ {today}　｜　数据截至 {today}</p>
    <p class="meta">覆盖：公募 REITs（上交所 + 深交所）· 机构间 REITs（持有型不动产）</p>
  </header>

  <div class="stats">
    <div class="stat"><div class="n">{len(g_items) + len(o_items)}</div><div class="k">在审及存量项目</div></div>
    <div class="stat"><div class="n">{fmt_amt(g_amt + o_amt)}</div><div class="k">拟发行金额（亿元）</div></div>
    <div class="stat"><div class="n">{len(g_add) + len(o_add)}</div><div class="k">本周新增项目</div></div>
    <div class="stat"><div class="n">{len(g_st) + len(o_st)}</div><div class="k">本周状态变化</div></div>
  </div>

  <section>
    <h2>一、两个市场的结构对比</h2>
    <div class="tw"><table>
      <thead><tr><th>维度</th><th class="num">公募 REITs</th><th class="num">机构间 REITs</th><th class="num">合计</th></tr></thead>
      <tbody>
        <tr><td>项目总数</td><td class="num">{len(g_items)}</td><td class="num">{len(o_items)}</td><td class="num total">{len(g_items) + len(o_items)}</td></tr>
        <tr><td>拟发行金额（亿元）</td><td class="num">{ga}</td><td class="num">{oa}</td><td class="num total">{fmt_amt(g_amt + o_amt)}</td></tr>
        <tr><td>金额披露率</td><td class="num">{g_rate}</td><td class="num">{o_rate}</td><td class="num">{g_cnt_amt + o_cnt_amt}/{len(g_items) + len(o_items)}</td></tr>
        <tr><td>单项目均值（亿元）</td><td class="num">{g_avg:,.2f}</td><td class="num">{o_avg:,.2f}</td><td class="num">—</td></tr>
        <tr><td>审核中</td><td class="num">{g_running}</td><td class="num">{o_running}</td><td class="num total">{g_running + o_running}</td></tr>
        <tr><td>注册生效 / 审核通过</td><td class="num">{g_pass}</td><td class="num">{o_pass}</td><td class="num total">{g_pass + o_pass}</td></tr>
        <tr><td>终止 / 中止</td><td class="num">{g_stop}</td><td class="num">{o_stop}</td><td class="num total">{g_stop + o_stop}</td></tr>
      </tbody>
    </table></div>
    <div class="insight">
      机构间单项目平均拟发行 <b>{o_avg:,.2f} 亿</b>，公募 <b>{g_avg:,.2f} 亿</b>（{multi:.1f} 倍）。
      {struct}
      公募深交所在审项目不披露规模，故公募金额合计为<b>下限</b>。
    </div>
  </section>

  <section>
    <h2>二、本周变化</h2>
    <div class="tw"><table>
      <thead><tr><th>板块</th><th class="num">新增项目</th><th class="num">状态变化</th></tr></thead>
      <tbody>
        <tr><td>公募 REITs</td><td class="num">{len(g_add)}</td><td class="num">{len(g_st)}</td></tr>
        <tr><td>机构间 REITs</td><td class="num">{len(o_add)}</td><td class="num">{len(o_st)}</td></tr>
        <tr><td class="total">合计</td><td class="num total">{len(g_add) + len(o_add)}</td><td class="num total">{len(g_st) + len(o_st)}</td></tr>
      </tbody>
    </table></div>
  </section>

  <section>
    <h2>三、本周看点</h2>
    <ul>{pts}</ul>
  </section>

  <section>
    <h2>四、新增项目明细</h2>
    <div class="tw"><table>
      <thead><tr><th>板块</th><th>名称</th><th>交易所</th><th>类型</th><th class="num">金额(亿)</th><th>状态</th></tr></thead>
      <tbody>{rows_add()}</tbody>
    </table></div>
  </section>

  <section>
    <h2>五、状态变化明细</h2>
    <div class="tw"><table>
      <thead><tr><th>板块</th><th>名称</th><th>交易所</th><th>变化</th></tr></thead>
      <tbody>{rows_st()}</tbody>
    </table></div>
  </section>

  <footer>
    <b>口径说明</b><br>
    · 数据来源：上交所 / 深交所 公开披露信息（公募 REITs 信息平台、持有型不动产信息平台）<br>
    · 公募「注册生效」对应 stage=6；机构间「审核通过」对应交易所状态码 4<br>
    · 公募深交所仅在注册生效后披露拟发行规模，未披露项目不计入合计<br>
    · 「已通过」为存量累计（含历年已发行产品），判断当期节奏请看「审核中」<br>
    · 两板块金额为不同产品类型的简单加总，仅作规模参考<br>
    <br>自动生成于 {today} · 数据源 reits-dashboard
  </footer>
</div>
</body>
</html>
"""


def main():
    force = "--force" in sys.argv
    if date.today().weekday() != 0 and not force:
        print("今天不是周一，跳过（如需强制生成请加 --force）")
        return

    g_snap, o_snap = load(GONG_SNAP), load(ORG_SNAP)
    if not g_snap or not o_snap:
        print("缺少快照文件，无法生成纪要")
        sys.exit(1)

    g_items = g_snap.get("items") or []
    o_items = o_snap.get("items") or []
    g_hist = load(GONG_CHG) or []
    o_hist = load(ORG_CHG) or []

    iso = date.today().isocalendar()
    year, week = iso[0], iso[1]
    today = date.today().isoformat()

    g_days, o_days = g_hist[:7], o_hist[:7]
    g_start = g_days[-1].get("date") if g_days else today
    o_start = o_days[-1].get("date") if o_days else today
    start = min(g_start, o_start)

    def agg(hist):
        add, st = [], []
        for h in hist:
            add.extend(h.get("added", []))
            st.extend(h.get("status_changed", []))
        return add, st

    g_add, g_st = agg(g_days)
    o_add, o_st = agg(o_days)

    # ---- 指标 ----
    g_amt = sum(x["amt"] for x in g_items if x.get("amt"))
    o_amt = sum(x["amt"] for x in o_items if x.get("amt"))
    g_cnt_amt = sum(1 for x in g_items if x.get("amt"))
    o_cnt_amt = sum(1 for x in o_items if x.get("amt"))

    g_running = sum(1 for x in g_items if 1 <= int(x.get("stage") or 0) <= 5)
    g_pass = sum(1 for x in g_items if int(x.get("stage") or 0) == 6)
    g_stop = sum(1 for x in g_items if int(x.get("stage") or 0) == 9)

    o_running = sum(1 for x in o_items if str(x.get("status")) in ORG_RUNNING)
    o_pass = sum(1 for x in o_items if str(x.get("status")) in ORG_PASS)
    o_stop = sum(1 for x in o_items if str(x.get("status")) in ORG_STOP)

    g_avg = g_amt / g_cnt_amt if g_cnt_amt else 0
    o_avg = o_amt / o_cnt_amt if o_cnt_amt else 0

    L = []
    L.append(f"# REITs 周度纪要 · {year}-W{week:02d}")
    L.append("")
    L.append(f"> 统计区间：{start} ~ {today}　｜　数据截至：{today}")
    L.append("> 覆盖范围：公募 REITs（上交所 + 深交所）、机构间 REITs（持有型不动产资产支持专项计划）")
    L.append("")

    L.append("## 一、全市场概览")
    L.append("")
    L.append("| 维度 | 公募 REITs | 机构间 REITs | 合计 |")
    L.append("|---|---:|---:|---:|")
    L.append(f"| 项目总数 | {len(g_items)} | {len(o_items)} | **{len(g_items) + len(o_items)}** |")
    L.append(f"| 拟发行金额（亿元） | {fmt_amt(g_amt)} | {fmt_amt(o_amt)} | **{fmt_amt(g_amt + o_amt)}** |")
    L.append(f"| 金额披露率 | {g_cnt_amt}/{len(g_items)}（{g_cnt_amt * 100 // max(len(g_items), 1)}%）"
             f" | {o_cnt_amt}/{len(o_items)}（{o_cnt_amt * 100 // max(len(o_items), 1)}%）"
             f" | {g_cnt_amt + o_cnt_amt}/{len(g_items) + len(o_items)} |")
    L.append(f"| 审核中 | {g_running} | {o_running} | {g_running + o_running} |")
    L.append(f"| 注册生效 / 审核通过 | {g_pass} | {o_pass} | {g_pass + o_pass} |")
    L.append(f"| 终止 / 中止 | {g_stop} | {o_stop} | {g_stop + o_stop} |")
    L.append("")
    L.append(f"**结构对比**：公募单项目平均拟发行 **{g_avg:,.2f} 亿**，机构间 **{o_avg:,.2f} 亿**"
             f"（{o_avg / g_avg:.1f} 倍）。"
             + ("机构间以单一大额项目为主，公募更分散。" if o_avg > g_avg else "公募单项目体量更大。"))
    L.append("")

    L.append("## 二、本周变化")
    L.append("")
    L.append("| 板块 | 新增项目 | 状态变化 |")
    L.append("|---|---:|---:|")
    L.append(f"| 公募 REITs | {len(g_add)} | {len(g_st)} |")
    L.append(f"| 机构间 REITs | {len(o_add)} | {len(o_st)} |")
    L.append(f"| **合计** | **{len(g_add) + len(o_add)}** | **{len(g_st) + len(o_st)}** |")
    L.append("")

    L.append("## 三、本周看点")
    L.append("")
    points = []
    for name, hist, seg in (("公募", g_st, "公募REITs"), ("机构间", o_st, "机构间REITs")):
        into = [x for x in hist if (str(x.get("status_to")) in ORG_PASS
                                    or str(x.get("stage_to")) == "6")]
        stop = [x for x in hist if (str(x.get("status_to")) in ORG_STOP
                                    or str(x.get("stage_to")) == "9")]
        if into:
            points.append(f"- **{seg}**：{len(into)} 个项目进入注册/通过阶段 —— "
                          + "、".join((x.get("name") or "")[:26] for x in into[:4]))
        if stop:
            points.append(f"- **{seg}**：{len(stop)} 个项目终止/中止 —— "
                          + "、".join((x.get("name") or "")[:26] for x in stop[:4]))
    all_add = [("公募REITs", x) for x in g_add] + [("机构间REITs", x) for x in o_add]
    if all_add:
        tot = sum((x.get("amt") or 0) for _, x in all_add)
        top = max(all_add, key=lambda t: (t[1].get("amt") or 0))
        points.append(f"- 本周新增 {len(all_add)} 个项目，合计拟发行 **{tot:,.2f} 亿元**；"
                      f"最大单笔为 **{top[1].get('name', '')[:28]}**（{fmt_amt(top[1].get('amt'))} 亿）")
    if not points:
        points.append("- 本周两板块均无新增项目、无状态变化，审核队列保持稳定。")
    L.extend(points)
    L.append("")

    L.append("## 四、新增项目明细")
    L.append("")
    if all_add:
        L.append("| 板块 | 名称 | 交易所 | 类型 | 拟发行金额(亿元) | 当前状态 |")
        L.append("|---|---|---|---|---:|---|")
        for seg, x in all_add[:40]:
            L.append("| {} | {} | {} | {} | {} | {} |".format(
                seg, (x.get("name") or "")[:40], x.get("ex", ""),
                x.get("ptype", ""), fmt_amt(x.get("amt")), x.get("sname", "")))
        if len(all_add) > 40:
            L.append(f"\n> 另有 {len(all_add) - 40} 个新增项目，详见看板。")
    else:
        L.append("本周无新增项目。")
    L.append("")

    all_st = [("公募REITs", x) for x in g_st] + [("机构间REITs", x) for x in o_st]
    L.append("## 五、状态变化明细")
    L.append("")
    if all_st:
        L.append("| 板块 | 名称 | 交易所 | 变化 |")
        L.append("|---|---|---|---|")
        for seg, x in all_st[:50]:
            L.append("| {} | {} | {} | {} → {} |".format(
                seg, (x.get("name") or "")[:40], x.get("ex", ""),
                x.get("from") or "—", x.get("to") or "—"))
    else:
        L.append("本周无状态变化。")
    L.append("")

    L.append("---")
    L.append("")
    L.append("**口径说明**")
    L.append("")
    L.append("- 数据来源：上交所 / 深交所 公开披露信息（公募 REITs 信息平台、持有型不动产信息平台）。")
    L.append("- 公募「注册生效」对应 stage=6；机构间「审核通过」对应交易所状态码 4。")
    L.append("- 公募深交所仅在项目注册生效后披露拟发行规模，未披露项目显示「注册后披露」且不计入合计。")
    L.append("- 两部合计金额为不同产品类型的简单加总，仅作规模参考，不宜直接横向比较。")
    L.append("")
    L.append(f"*自动生成于 {today} · 数据源 reits-dashboard*")

    os.makedirs(os.path.join(BASE, WEEKLY_DIR), exist_ok=True)
    base_name = f"digest-{year}-W{week:02d}"

    md_path = os.path.join(BASE, WEEKLY_DIR, base_name + ".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    html_doc = build_html(year, week, start, today, g_items, o_items, g_amt, o_amt,
                          g_cnt_amt, o_cnt_amt, g_running, g_pass, g_stop,
                          o_running, o_pass, o_stop, g_avg, o_avg,
                          g_add, g_st, o_add, o_st, all_add, all_st, points)
    html_path = os.path.join(BASE, WEEKLY_DIR, base_name + ".html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)

    print(f"已生成：{os.path.join(WEEKLY_DIR, base_name)}.md / .html")
    print(f"  公募 {len(g_items)} 条 / {fmt_amt(g_amt)} 亿　机构间 {len(o_items)} 条 / {fmt_amt(o_amt)} 亿")


if __name__ == "__main__":
    main()
