# HTML 模板规范

## 技术选型

- **单文件 HTML**：所有 CSS/JS 内联，数据内嵌为 JSON，双击即可打开。
- **地图**：Leaflet.js + OpenStreetMap（免费，无需 API key）。
- **交互**：原生 JS，无框架依赖。
- **样式**：简洁现代，移动端适配。

## 页面结构（Tab 切换）

| Tab | 内容 |
|-----|------|
| 总览 | 地图 + 路线 + 行程概要卡片 |
| 行程 | 按天时间线，每天的景点+交通+餐饮 |
| 景点 | 卡片网格，点击展开详情（门票/时长/贴士/天气） |
| 美食 | 卡片列表，可按类型筛选 |
| 住宿 | 卡片列表 + 价格区间滑块（双滑块 min/max） |
| 行李 | 分类清单，可勾选 |

## 数据注入方式

模板中预留 `window.TRIP_DATA = {};`，生成脚本将完整 JSON 注入此处。所有页面从该对象读取数据渲染。

**⚠ 字段名必须与模板 JS 一致**，否则页面会显示 undefined。完整字段规范见 SKILL.md 的「Step 8: JSON 数据结构规范」。以下是模板 JS 实际读取的关键字段速查：

| 数据区 | 模板读取的字段 | 常见错误 |
|--------|---------------|----------|
| 顶层 | `D.days`（数字）、`D.title`、`D.subtitle`、`D.coords` | ❌ `days` 放进 `trip_info` → 总天数 undefined |
| 景点 | `a.name`、`a.lat`、`a.lng`、`a.day`、`a.duration_hours`（数字）、`a.ticket`、`a.address`、`a.tips` | ❌ `duration`（字符串）→ 建议游玩 undefined |
| 美食 | `f.name`、`f.lat`、`f.lng`、`f.day`、`f.type`、`f.price_per_person`（数字）、`f.must_try`（数组）、`f.address`、`f.source`、`f.note` | ❌ `price`（字符串）→ 人均 undefined；`signature` → 不渲染 |
| 住宿 | `h.name`、`h.lat`、`h.lng`、`h.day`、`h.price_min`（数字）、`h.price_max`（数字）、`h.rating`、`h.area`、`h.near`、`h.tags`（数组）、`h.note` | ❌ `price_range`（字符串）→ 价格 undefined；`address` → 位置不显示 |
| 路线 | `r.from`、`r.to`、`r.mode`、`r.day`、`r.distance_km`、`r.duration_hours`、`r.polyline`（数组） | ❌ 缺 `polyline` → 只画两点直线 |
| 时间轴 | `s.time`、`s.type`、`s.title`、`s.duration_min`、`s.duration_hours`、`s.ref`、`s.lat`、`s.lng` | ❌ `attraction`/`lunch`/`dinner` 项缺 `lat`/`lng` → 按天路线串联失败 |

## 地图要求

- 标记所有景点、住宿、美食点位（不同图标/颜色区分）。
- **图层开关**：地图上方有「图层」控制条，景点/美食/住宿/路线四类标记各有独立 checkbox，可单独显示或隐藏（用户可只看路线、或关掉美食住宿降噪）。
- **真实路线**：城际路线用 `intercity_routes[].polyline`（完整几何，来自高德 driving steps）绘制；自驾实线蓝色，高铁/飞机等非自驾紫色虚线；polyline 缺失时退化为起终点蓝色虚线并在生成时告警。
- **按天路线**：选中某一天时，地图按当天 schedule 顺序给景点/餐厅编号（标记内显示"第N站"数字）并连线：
  - 有 `daily_plan[].route`（每段 leg 含 polyline）→ 绘制当天真实行驶路线（红色实线）。
  - 没有 → 按行程顺序将带坐标的点连红色虚线兜底。
- 点击标记弹出简要信息（名称+类型，按天模式下显示"第N站"）。
- 自动适配视野包含所有可见标记和路线。
- **坐标系**：模板内置 GCJ-02→WGS-84 转换（高德坐标直接用）；JSON 顶层 `"coords": "wgs84"` 可跳过转换。
- 行程页每个带坐标的时间轴卡片有「📍 在地图上查看」按钮，点击跳转总览页并定位到该点。

## 住宿筛选

- 双滑块：最低价、最高价。
- 实时过滤卡片列表。
- 显示当前筛选结果数量。
- 滑块范围 = 所有酒店价格的 min/max。

## 颜色规范

- 主色：#2563eb（蓝色，旅行感）
- 景点标记：#ef4444（红）
- 美食标记：#f59e0b（橙）
- 住宿标记：#10b981（绿）
- 城际路线（自驾）：#2563eb 实线
- 城际路线（高铁/飞机）：#7c3aed 虚线
- 按天路线：#ef4444（红）

## 生成脚本

`scripts/html_generator.py` 接收一个 JSON 文件路径，读取模板 `assets/html-template/template.html`，替换 `__TRIP_DATA__` 占位符，输出最终 HTML。

生成前自动校验（打印 ⚠️ 警告，需修复后重新生成）：
1. 每日时间轴时间是否递进（无倒流/重叠）
2. 景点/美食/住宿是否缺经纬度
3. 景点是否缺 day 字段
4. 城际路线是否缺 polyline
5. 行程项（景点/正餐）是否带坐标

用法：
```bash
python3 scripts/html_generator.py data.json -o output.html
```
