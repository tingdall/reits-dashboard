# REITs 双板块数据看板（REITs Dashboard）

> 上交所 + 深交所 **公募 REITs**（基础设施 / 商业不动产）与 **机构间 REITs**（持有型不动产资产支持专项计划）的申报审核进度看板。

## 项目简介

把沪深两所公开披露的 REITs 申报审核数据，整理成一个**零依赖、免安装**的单文件 HTML 看板：顶部 Tab 切换「公募 / 机构间」，支持筛选、排序、图表、标记、导出，每日自动更新。

数据来源均为交易所官网**公开信息**（上交所 REITs 信息平台 / 持有型不动产信息平台、深交所公募REITs信息平台 / 固定收益信息平台），本仓库仅做数据整理与可视化。

**在线版**：https://tingdall.github.io/reits-dashboard/ （`#public` / `#inter` 可直达对应板块）

## 两个板块的规模（2026-10-25 快照）

| 板块 | 项目数 | 拟发行金额 | 说明 |
|---|---:|---:|---|
| 公募 REITs | 160（上交所 102 / 深交所 58） | 2,389.92 亿 | 含招募说明书「预计募集规模」569 亿，看板标注「（预计）*」 |
| 机构间 REITs | 123（上交所 105 / 深交所 18） | 2,427.45 亿 | 金额披露完整 |

> 注意：**160 条是申报记录数，不是基金只数**。同一只 REIT 的首发与扩募（新购入项目）各占一条，按名称去重约 145 只；看板「发售类型」列可区分。

## 特性

- **双板块融合**：统一交互与图表逻辑，Tab 切换；交易所维度再细分上交所/深交所
- **二级分类统一**：`交通设施 / 能源 / 市政生态 / 产业园 / 物流仓储 / 数据中心 / 办公 / 文旅类 / 消费 / 租赁住房 / 综合业态`，两板块共用一套词典，可直接横向对比
- **变更监控**：每日与上一版快照比对，记录新增项目、状态跃迁、金额变化；看板展示近 7 日动态
- **周度简报**：每周一自动生成三份——公募专项、机构间专项、**合并纪要（含 HTML 版，可直接转发）**
- **金额补齐**：深交所在审项目不披露募集规模，通过招募说明书 PDF 提取「预计募集规模」补齐（16/23）
- **筛选与标记**：关键字、交易所、大类、二级分类、发售类型、状态、管理人、金额、日期等维度；标记与手动分类存 localStorage
- **数据可追溯**：`snapshots/` 保留每日归档，`weekly/` 保留周报，git 历史可回溯任意日期

## 快速开始

```bash
# 1. 看板（本地需 HTTP，file:// 下 fetch 会被拦截）
python -m http.server 8000
# 浏览器打开 http://localhost:8000/index.html

# 2. 更新数据
python reits_update.py     # 机构间 → reits_snapshot.json
python gongmu_update.py    # 公募   → gongmu_snapshot.json

# 3. 生成周报（非周一需加 --force）
python weekly_digest.py --force
```

依赖：Python 3 标准库即可抓取；`fill_prospectus.py` 额外需要 `pypdf` 与本机 Chrome。

## 目录结构

```
index.html              # 唯一看板（双 Tab，单文件自包含）
reits_update.py         # 机构间抓取 + 变更比对 + 周一简报
gongmu_update.py        # 公募抓取 + 变更比对 + 金额补齐读取
classify_public.py      # 公募二级分类（基于底层资产实体）
weekly_digest.py        # 双板块合并周报（Markdown + HTML）
fill_prospectus.py      # 招募说明书 PDF 提取预计募集规模（本地工具）
cls_seed.json           # 机构间分类基线
gap_amounts.json        # 招募说明书提取结果
gongmu_cls.json         # 公募二级分类结果
reits_snapshot.json     # 机构间快照
gongmu_snapshot.json    # 公募快照
snapshots/              # 每日快照归档
weekly/                 # 周报归档
更新流程规范.md          # 增量更新策略
AGENTS.md               # Agent 规则文件
```

## 自动更新与托管

GitHub Actions 每日 **08:15**（北京时间）执行：机构间抓取 → 公募抓取 → 周报生成 → 归档 → 提交，GitHub Pages 自动发布。

为保证数据可信，两个抓取脚本都做了**完整性保护**：任一所抓取失败或条数不足时整体中止，绝不用残缺数据覆盖已有快照。

## 免责声明

本项目仅用于数据展示与研究，数据来自交易所公开信息，不构成任何投资建议。数据准确性以交易所官网为准。

## License

MIT
