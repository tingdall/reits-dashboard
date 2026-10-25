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
    name = f"REITs周度纪要-{year}-W{week:02d}.md"
    path = os.path.join(BASE, WEEKLY_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"已生成：{os.path.join(WEEKLY_DIR, name)}")
    print(f"  公募 {len(g_items)} 条 / {fmt_amt(g_amt)} 亿　机构间 {len(o_items)} 条 / {fmt_amt(o_amt)} 亿")


if __name__ == "__main__":
    main()
