# -*- coding: utf-8 -*-
"""
机构间REITs数据看板 · 生成脚本（build_reits.py）
================================================
从模板 + 数据生成正式 HTML：
  模板（含 __EMBED_PY__/__EMBED_BAT__ 占位符）
  + 最新数据快照（reits_snapshot.js 的 __REITS_SNAPSHOT__）
  + 最新更新工具源码（reits_update.py / 更新数据.bat，内嵌供下载）
  → 输出正式看板 HTML（单文件，自包含）

本脚本为仓库自包含：模板优先在仓库 `templates/` 子目录，数据快照优先读同目录 `reits_snapshot.js`。
（若从其他环境拷贝而来，模板/数据回退路径会自动探测同级目录，无需配置。）

用法：python build_reits.py
"""
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(sys.argv[0]))  # 脚本所在目录（仓库根 或 deliverables）
ROOT = BASE                                          # 仓库根

# 模板查找顺序：脚本同级 templates/ → 仓库根 templates/（纯仓库内，无外部绝对路径）
TPL_CANDIDATES = [
    os.path.join(BASE, "templates", "reits_dash_template.html"),
    os.path.join(ROOT, "templates", "reits_dash_template.html"),
]
# 数据回退查找顺序：脚本同级 → 仓库 tests/（纯仓库内）
DATA_FALLBACK_CANDIDATES = [
    os.path.join(BASE, "merged_real.json"),
    os.path.join(ROOT, "tests", "merged_real.json"),
]

PY_SRC_FILE = os.path.join(BASE, "reits_update.py")
BAT_SRC_FILE = os.path.join(BASE, "更新数据.bat")
SNAPSHOT_FILE = os.path.join(BASE, "reits_snapshot.js")
OUT_FILE = os.path.join(BASE, "机构间REITs数据看板_正式版.html")
SNAPSHOT_DATE = "2026-08-06"  # 与快照日期一致（或从快照读取）


def first_existing(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def main():
    tpl_path = first_existing(TPL_CANDIDATES)
    if not tpl_path:
        print("[错误] 未找到模板 reits_dash_template.html")
        sys.exit(1)
    tpl = open(tpl_path, encoding="utf-8").read()
    if "__REITS_DATA__" not in tpl:
        print("[错误] 模板缺少 __REITS_DATA__ 占位符")
        sys.exit(1)
    print(f"  模板: {tpl_path}")

    # 1) 数据：优先最新快照（同目录 reits_snapshot.js）
    try:
        raw = open(SNAPSHOT_FILE, encoding="utf-8").read()
        m = re.search(r"var __REITS_SNAPSHOT__ = (.*?);\n", raw, re.S)
        data = json.loads(m.group(1))
        print(f"  数据来源: 快照（{len(data)} 条）")
    except Exception:
        fb = first_existing(DATA_FALLBACK_CANDIDATES)
        if not fb:
            print("[错误] 未找到数据回退文件 merged_real.json")
            sys.exit(1)
        data = json.load(open(fb, encoding="utf-8"))
        print(f"  数据来源: 回退 {fb}（{len(data)} 条）")

    # 2) 更新工具源码：JSON 编码为安全 JS 字符串
    py_js = json.dumps(open(PY_SRC_FILE, encoding="utf-8").read(), ensure_ascii=False)
    bat_js = json.dumps(open(BAT_SRC_FILE, encoding="utf-8").read(), ensure_ascii=False)

    # 3) 组装
    out = tpl.replace("__REITS_DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    out = out.replace("__SNAPSHOT__", SNAPSHOT_DATE)
    out = out.replace("__EMBED_PY__", py_js)
    out = out.replace("__EMBED_BAT__", bat_js)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"已生成: {OUT_FILE}（{len(out)//1024} KB，{len(data)} 条数据，含内嵌更新工具）")


if __name__ == "__main__":
    main()
