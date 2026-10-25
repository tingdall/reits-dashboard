# AGENTS.md — REITs 双板块数据看板

## 一句话定位
上交所 + 深交所 **公募 REITs** 与 **机构间 REITs（持有型不动产）** 的申报审核进度看板，单文件 `index.html`，顶部 Tab 切换两个板块，每日自动更新。

## 怎么跑起来
- **看板**：浏览器打开 `index.html`；线上 https://tingdall.github.io/reits-dashboard/ （`#public` / `#inter` 可直达板块）
- **手动更新**：`python reits_update.py`（机构间）→ `python gongmu_update.py`（公募）→ `python weekly_digest.py --force`（周报，可选）
- **本地预览必须走 HTTP**：`python -m http.server 8000`（`file://` 下 `fetch` 被 CORS 拦截，外部快照加载不到）

## 技术栈
纯 HTML/CSS/JS 单文件（品牌橙 #d94016，零外部依赖）；图表为原生 SVG；抓取仅用 Python 标准库 `urllib`；PDF 解析用 `pypdf`。

## 数据源（2026-10 实测）
| 板块 | 接口 | 关键参数 | 规模 |
|---|---|---|---|
| 机构间·上交所 | `query.sse.com.cn/sseQuery/commonSoaQuery.do` | `sqlId=ZQ_XMLB` + `key=持有型不动产` | 105 条 |
| 机构间·深交所 | `bond.szse.cn/api/report/ShowReport/data` | `CATALOGID=xmjdxx` / 详情 `xmjdxx_xq` | 18 条 |
| 公募·上交所 | `query.sse.com.cn/commonSoaQuery.do` | `sqlId=ZQ_XMLB` + **`bond_type=4`** | 102 条 |
| 公募·深交所 | `reits.szse.cn/api/reits/projectrends/query` | `biztypsb=21`(首发) / `23`(新购入) + `bizType=2` | 58 条 |

全部需带 `Referer` + 浏览器 UA。

## 目录与数据流
```
index.html            # 唯一看板（双 Tab；勿手改结构，改动后跑 node --check 校验内嵌 JS）
reits_update.py       # 机构间抓取 → reits_snapshot.json/.js + reits_changes.json + weekly/org-*.md
gongmu_update.py      # 公募抓取 → gongmu_snapshot.json/.js + gongmu_changes.json + 读取 gap_amounts.json
classify_public.py    # 公募二级分类 → gongmu_cls.json
weekly_digest.py      # 双板块合并周报 → weekly/digest-YYYY-Www.md/.html
fill_prospectus.py    # 本地工具：从招募说明书提取「预计募集规模」（需 Chrome，跑完产出 gap_amounts.json）
cls_seed.json         # 机构间分类基线，勿删
```

## 关键约定（踩过的坑，勿重复）
- **二级分类必须用统一词典**：`交通设施/能源/市政生态/产业园/物流仓储/数据中心/办公/文旅类/消费/租赁住房/综合业态`。公募与机构间共用，否则无法跨板块对比。
- **一级分类不统一是故意的**：公募用交易所口径「基础设施/商业不动产」，机构间用「经营权类/产权类」，不要强映射。
- **状态字段**：公募用统一 `stage`（1-6/9）+ 中文 `sname`；机构间用交易所状态码 + `STATUS_LABEL`。渲染统一走 `d.sname || STATUS_LABEL[d.status]`。
- **深交所基金管理人字段是 `acctfm`**（曾误写 `acptfm` 导致整列空）。
- **招募说明书取金额必须做上下文校验**：`BAD_CTX`（类REITs/总发行/不足/未达到…）+ 合理区间 0.5–500 亿，否则会把「历史总发行规模」「募集资金规模不足2亿元」当成本基金规模。
- **`CUR_SEG`/`GONGMU_DATA` 等 `let` 声明必须放在渲染函数之前**，否则启动时 TDZ 报错、统计卡全空。
- **推送不要带 token 参数**（`-c url.https://TOKEN@...` 会被环境 SIGTERM）；凭据已缓存，直接 `git push origin main`。
- **GitHub Pages 有 10 分钟 CDN 缓存**，核验线上要加 `?v=时间戳`。
- **Chrome headless 的 `--window-size` 受系统 DPI 影响**（设 390 实际视口可能 503），判断移动端溢出要注入脚本读 `clientWidth`，不能只看截图。

## 当前状态与下一步
- 公募 **160 条**（上交所 102 / 深交所 58），金额 **2,389.92 亿**（含招募说明书预计口径 569 亿，看板标「（预计）*」）
- 机构间 **123 条**（上交所 105 / 深交所 18），金额 2,427.45 亿
- 两板块均带变更监控（每日 diff + 看板「近期变更」面板 + 周一简报）
- 自动化：GitHub Actions 每日 08:15 —— 机构间抓取 → 公募抓取 → 周报 → 归档 → 提交
- 待办：机构间也补二级分类一致性校验；`weekly/` 三份简报可考虑合并为一份对外
