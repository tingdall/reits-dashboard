# AGENTS.md — 机构间REITs数据看板

## 一句话定位
上交所 + 深交所「持有型不动产」（机构间REIT）项目数据的单文件 HTML 看板，跟踪项目状态、分类与标记。

## 怎么跑起来
- **打开看板**：浏览器打开 `机构间REITs数据看板_v5分类版.html`（纯静态单文件，零依赖，无需服务器；含双系统更新工具）
- **更新数据**：双击 `更新数据.bat`（Windows）/ `更新数据.command`（Mac，从看板页面下载）自动抓取两所最新数据并回写 HTML；或命令行 `python reits_update.py`
- **查看基础版**：`机构间REITs数据看板_正式版.html`（沪深融合基础功能）

## 技术栈
- 纯 HTML + CSS + JS 单文件（品牌橙 #d94016），无框架、无 CDN、无构建
- 图表：原生 SVG（圆环图、横向条形图），CSS 实现交互
- Python 标准库 urllib 抓取（零第三方依赖）

## 目录与约定
- **仓库即唯一目录**：所有交付物、脚本、文档均在仓库根目录；模板构建与回归为开发辅助（见下），不在公开分发范围内
- **数据流**：`reits_update.py`（抓取两所）→ `reits_snapshot.js`（外部快照）→ HTML 启动时优先加载外部快照，内嵌数据兜底
- **数据模型**：`{id, num, name, mgr, writer, amt, status, up, acc, origin, ex, ptype, psub, pflag, pnote}`；`ex`=交易所（"上交所"/"深交所"）
- **字段映射**：深交所 fxr(发行人)→origin；cxsqc→writer；cxsjc→mgr；nfxje→amt；xmzt 中文→STATUS_MAP_SZSE
- **编号约定**：合并后全局连续编号 1..N（跨两所不重复），由 reits_update.py 在排序后统一重排 num，勿手改
- **默认排序约定**：三级排序（更新日期降序 → 受理日期降序 → 拟发行金额降序），前端 applyFilters 在默认状态（sortKey=up 且降序）走三级比较；手动点表头仍走单列排序
- 标记数据 localStorage 双写（reits_dash_mark_v1 / _bak），刷新不丢
- 手动分类覆盖 localStorage 双写（reits_dash_cls_v1 / _bak），前端优先于快照

## 开发辅助（模板/回归）
- **构建**：`build_reits.py` 从模板（模板文件在 `templates/` 子目录，见 `docs/03_构建与发布.md`）生成正式 HTML；改 HTML 前先改模板再构建
- **验证**：改完建议 `node --check` 抽取内嵌 JS 语法检查 + Chrome 无头回归（`tests/` 下回归脚本模式），再提交

## 更新流程规范（增量策略，必读 `更新流程规范.md`）
- **分类字段增量**：ptype/psub/pflag/pnote 默认从旧快照按 id 继承，**每次更新不重算**；仅新增项目（标「待分类」）或 CLS_VERSION 递增（全量重分类提示）才触发重新分类
- **分类基线**：`cls_seed.json`（id→分类）用于首次建立基线/补漏；勿删，删除会导致大量项目变待分类
- **快照版本号**：reits_snapshot.js 输出 `__REITS_CLS_VERSION__`，脚本下次运行比对
- **其他模块**：基础字段随抓取自然更新；编号每次重排；前端标记/手动分类（localStorage）独立不受更新影响
- **红线**：禁止无版本变更时重算已有分类；禁止手改正式 HTML（改模板→build_reits.py）

## 当前状态与下一步
- **已融合两所**：上交所 92 条 + 深交所 13 条 = 105 条（2026-08-07 快照）；顶部 Tab（全部/上交所/深交所）与左侧交易所多选联动
- 接口经验：上交所强制 Referer 白名单（bond.sse.com.cn）；深交所带页面 Referer 即可；**浏览器均无法直连**，更新必须走 reits_update.py
- 已知 Bug 修复记录：buildMulti 重复 addEventListener 互相抵消 → el._multiBound 只绑一次（勿回归）
- 下一步：按需扩展（如公募REITs 复用抓取架构、对比视图），改动前先读本文件与 README/docs 保持结构一致
