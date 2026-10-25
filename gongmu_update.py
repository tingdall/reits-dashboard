#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
公募 REITs 数据抓取（上交所 + 深交所）
- 零第三方依赖（仅标准库）
- 双所完整性保护：任一交易所失败则整体中止，绝不用不完整数据覆盖
- 失败自动重试
- 输出：gongmu_snapshot.json / gongmu_snapshot.js

接口（2026-10 实测）：
  上交所 GET query.sse.com.cn/commonSoaQuery.do
         sqlId=ZQ_XMLB & bond_type=4 & isPagination=true & pageHelp.*
  深交所 GET reits.szse.cn/api/reits/projectrends/query
         biztypsb=21(首发) / 23(新购入项目) & bizType=2 & pageIndex/pageSize
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# ---------------- 上交所 ----------------
SSE_URL = "https://query.sse.com.cn/commonSoaQuery.do"
SSE_REFERER = "https://www.sse.com.cn/reits/info/"
SSE_SQL_ID = "ZQ_XMLB"
SSE_BOND_TYPE = "4"          # 4 = 公募 REITs（机构间用 key=持有型不动产）
SSE_PAGE_SIZE = 200

# ---------------- 深交所 ----------------
SZSE_URL = "https://reits.szse.cn/api/reits/projectrends/query"
SZSE_REFERER = "https://reits.szse.cn/projectdynamic/index.html"
SZSE_BIZ_TYPE = "2"
SZSE_SUB_TYPES = {"21": "首发", "23": "新购入项目"}
SZSE_PAGE_SIZE = 200

OUT_JSON = "gongmu_snapshot.json"
OUT_JS = "gongmu_snapshot.js"
RETRY = 3
RETRY_WAIT = 5

# ---------------- 码值映射（取自交易所官方 JS 源码） ----------------
REITS_TYPE_MAP = {"0": "首次发售", "1": "扩募发售"}
ASSET_TYPE_MAP = {"0": "商业不动产", "1": "基础设施"}

SSE_STATUS_NAME = {
    "0": "已申报", "1": "已受理", "2": "已反馈", "3": "已接收反馈意见",
    "4": "通过", "5": "未通过", "8": "终止", "9": "中止",
    "10": "已回复交易所意见", "11": "提交注册", "12": "注册生效",
}

# 统一阶段：1申报 2受理 3问询/反馈 4审核意见 5提交注册 6注册生效 9终止/中止
SSE_STAGE = {
    "0": 1, "1": 2, "2": 3, "3": 3, "10": 3,
    "4": 4, "5": 4, "11": 5, "12": 6,
    "8": 9, "9": 9,
}
SZSE_STAGE = {5: 1, 10: 2, 20: 3, 30: 4, 40: 6, 60: 9}
STAGE_NAME = {1: "申报", 2: "受理", 3: "问询/反馈", 4: "审核意见",
              5: "提交注册", 6: "注册生效", 9: "终止/中止"}


def clean(v):
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s in ("-", "null", "None") else s


def to_amt(v):
    s = clean(v)
    if not s:
        return None
    try:
        f = float(s.replace(",", ""))
        return round(f, 2) if f > 0 else None
    except ValueError:
        return None


def http_get_json(url, referer):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": referer,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    })
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode("utf-8", "replace")
    return json.loads(raw)


def get_with_retry(url, referer, label):
    last = None
    for i in range(1, RETRY + 1):
        try:
            return http_get_json(url, referer)
        except Exception as e:                       # noqa: BLE001
            last = e
            print(f"  [{label}] 第 {i} 次失败: {e}")
            if i < RETRY:
                time.sleep(RETRY_WAIT)
    raise RuntimeError(f"{label} 连续 {RETRY} 次失败: {last}")


# ================= 上交所 =================
def fetch_sse():
    qs = urllib.parse.urlencode({
        "isPagination": "true",
        "sqlId": SSE_SQL_ID,
        "bond_type": SSE_BOND_TYPE,
        "pageHelp.pageSize": SSE_PAGE_SIZE,
        "pageHelp.pageNo": 1,
        "pageHelp.beginPage": 1,
        "pageHelp.cacheSize": 1,
    }, safe=".")
    data = get_with_retry(f"{SSE_URL}?{qs}", SSE_REFERER, "SSE")
    rows = (data.get("pageHelp") or {}).get("data") or []
    total = (data.get("pageHelp") or {}).get("total")
    print(f"  上交所返回 {len(rows)} 条（total={total}）")

    items = []
    for r in rows:
        st = clean(r.get("AUDIT_STATUS"))
        items.append({
            "id": clean(r.get("BOND_NUM")) or clean(r.get("SEQ")),
            "name": clean(r.get("AUDIT_NAME")),
            "pname": clean(r.get("PRIORITY_NAME")),
            "mgr": clean(r.get("PRIORITY_MANAGER")),      # 专项计划管理人
            "writer": clean(r.get("WRITER_NAME")),        # 基金管理人
            "origin": clean(r.get("FULL_NAME")),          # 原始权益人
            "amt": to_amt(r.get("PLAN_ISSUE_AMOUNT")),
            "status": st,
            "sname": SSE_STATUS_NAME.get(st, clean(r.get("AUDIT_SUB_STATUS"))),
            "stage": SSE_STAGE.get(st, 0),
            "ptype": ASSET_TYPE_MAP.get(clean(r.get("REITS_ASSET_TYPE")), "-"),
            "itype": REITS_TYPE_MAP.get(clean(r.get("REITS_TYPE")), "-"),
            "acc": clean(r.get("ACCEPT_DATE")),
            "up": clean(r.get("PUBLISH_DATE")),
            "ex": "上交所",
            "seg": "public",
        })
    return items, total


# ================= 深交所 =================
def fetch_szse():
    items, stage_stat = [], {}
    total = 0
    for sub, subname in SZSE_SUB_TYPES.items():
        qs = urllib.parse.urlencode({
            "biztypsb": sub,
            "bizType": SZSE_BIZ_TYPE,
            "pageIndex": 0,
            "pageSize": SZSE_PAGE_SIZE,
        })
        data = get_with_retry(f"{SZSE_URL}?{qs}", SZSE_REFERER, f"SZSE-{sub}")
        rows = data.get("data") or []
        total += data.get("totalSize") or len(rows)
        print(f"  深交所 {subname}(biztypsb={sub}) 返回 {len(rows)} 条（total={data.get('totalSize')}）")

        # 阶段漏斗统计（仅取一次，用于看板展示）
        if not stage_stat:
            stage_stat = {s.get("stageName"): s.get("projectCount")
                          for s in (data.get("stageList") or [])}

        for r in rows:
            stage = SZSE_STAGE.get(r.get("stage") or r.get("prjstatus"), 0)
            items.append({
                "id": str(r.get("prjid") or ""),
                "name": clean(r.get("cmpnm")),
                "pname": clean(r.get("specialPlanName")),
                "mgr": clean(r.get("sprinst")),            # 专项计划管理人
                "writer": clean(r.get("acctfm")),          # 基金管理人（注意字段名 acctfm）
                "origin": clean(r.get("primitiveInterestsor")),
                "amt": to_amt(r.get("maramt")),
                "status": clean(r.get("prjstatus")),
                "sname": clean(r.get("prjst")),
                "stage": stage,
                "ptype": clean(r.get("bizcategorynm")) or "-",
                "itype": clean(r.get("biztypsbName")) or subname,
                "acc": clean(r.get("acptdt")),
                "up": clean(r.get("updtdt")),
                "ex": "深交所",
                "seg": "public",
            })
    return items, total, stage_stat


HIST_FILE = "gongmu_changes.json"   # 变更历史（累积，保留 90 天）
HIST_KEEP_DAYS = 90


def load_json_safe(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def diff_items(prev, curr):
    """对比上一版快照，返回 (新增, 状态变化, 金额变化)。"""
    pm = {}
    if prev and isinstance(prev.get("items"), list):
        for x in prev["items"]:
            if x.get("id"):
                pm[str(x["id"])] = x
    cm = {str(x["id"]): x for x in curr if x.get("id")}

    added, status_chg, amt_chg = [], [], []
    for k, cur in cm.items():
        old = pm.get(k)
        if not old:
            added.append({
                "id": k, "name": cur.get("name"), "ex": cur.get("ex"),
                "amt": cur.get("amt"), "sname": cur.get("sname"),
                "itype": cur.get("itype"), "ptype": cur.get("ptype"),
            })
            continue
        o_st, n_st = str(old.get("stage")), str(cur.get("stage"))
        o_sn, n_sn = (old.get("sname") or ""), (cur.get("sname") or "")
        if o_st != n_st or o_sn != n_sn:
            status_chg.append({
                "id": k, "name": cur.get("name"), "ex": cur.get("ex"),
                "from": o_sn, "to": n_sn,
                "stage_from": old.get("stage"), "stage_to": cur.get("stage"),
            })
        o_amt, n_amt = old.get("amt"), cur.get("amt")
        if (o_amt is None) != (n_amt is None) or (o_amt or 0) != (n_amt or 0):
            amt_chg.append({
                "id": k, "name": cur.get("name"), "ex": cur.get("ex"),
                "from": o_amt, "to": n_amt,
            })
    return added, status_chg, amt_chg


def main():
    cst = timezone(timedelta(hours=8))
    today = datetime.now(cst).strftime("%Y-%m-%d")
    print(f"== 公募 REITs 抓取  {today} ==")

    results = {}
    # 双所完整性保护：任一失败直接退出，不产出残缺快照
    try:
        print("[上交所]")
        results["sse"] = fetch_sse()
    except Exception as e:                            # noqa: BLE001
        print(f"!! 上交所抓取失败，按完整性保护中止: {e}")
        sys.exit(1)

    try:
        print("[深交所]")
        results["szse"] = fetch_szse()
    except Exception as e:                            # noqa: BLE001
        print(f"!! 深交所抓取失败，按完整性保护中止: {e}")
        sys.exit(1)

    sse_items, sse_total = results["sse"]
    szse_items, szse_total, stage_stat = results["szse"]

    # 基本体检
    if not sse_items or not szse_items:
        print("!! 某一交易所返回 0 条，疑似异常，中止")
        sys.exit(1)
    if sse_total and len(sse_items) < sse_total:
        print(f"!! 上交所条数不足（{len(sse_items)}/{sse_total}），中止")
        sys.exit(1)
    if szse_total and len(szse_items) < szse_total:
        print(f"!! 深交所条数不足（{len(szse_items)}/{szse_total}），中止")
        sys.exit(1)

    items = sse_items + szse_items
    ids = [i["id"] for i in items if i["id"]]
    dup = len(ids) - len(set(ids))
    if dup:
        print(f"!! 发现 {dup} 个重复 ID，中止")
        sys.exit(1)

    amt_sum = round(sum(i["amt"] for i in items if i["amt"]), 2)

    # ---------- 变更监控：与上一版快照比对 ----------
    prev = load_json_safe(os.path.join(BASE, OUT_JSON))
    added, status_chg, amt_chg = diff_items(prev, items)
    today_changes = {
        "date": today,
        "prev_date": (prev or {}).get("date", ""),
        "added": added,
        "status_changed": status_chg,
        "amount_changed": amt_chg,
    }
    # 累积历史（同日重跑覆盖，保留最近 N 天）
    hist = load_json_safe(os.path.join(BASE, HIST_FILE)) or []
    if not isinstance(hist, list):
        hist = []
    hist = [h for h in hist if h.get("date") != today]
    hist.append(today_changes)
    hist.sort(key=lambda h: h.get("date", ""), reverse=True)
    hist = hist[:HIST_KEEP_DAYS]
    with open(os.path.join(BASE, HIST_FILE), "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, separators=(",", ":"))

    payload = {
        "date": today,
        "seg": "public",
        "count": len(items),
        "amount_sum": amt_sum,
        "stage_stat": stage_stat,
        "changes": today_changes,
        "items": items,
    }

    with open(os.path.join(BASE, OUT_JSON), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(BASE, OUT_JS), "w", encoding="utf-8") as f:
        f.write("window.GONGMU_DATA=" + json.dumps(payload, ensure_ascii=False,
                                                   separators=(",", ":")) + ";\n")

    print(f"\n完成：{len(items)} 条（上交所 {len(sse_items)} / 深交所 {len(szse_items)}）")
    print(f"金额合计：{amt_sum} 亿元（有值 {sum(1 for i in items if i['amt'])} 条）")
    st = {}
    for i in items:
        st[STAGE_NAME.get(i["stage"], "未知")] = st.get(STAGE_NAME.get(i["stage"], "未知"), 0) + 1
    print("阶段分布：", st)
    print("样例：", json.dumps(items[0], ensure_ascii=False))


if __name__ == "__main__":
    main()
