---
name: help-u-2-travel
description: 旅行规划助手，生成交互式 HTML 旅行方案。支持自驾、公共交通（高铁/飞机/地铁）及混合出行模式。覆盖路线规划、城际与城内交通、景点详情（门票/天气/游玩时长/专属贴士）、美食推荐（小红书/抖音真实热度检索，过滤营销号）、住宿筛选（按预算区间+位置优先级）、行李清单。当用户要求规划旅行、自驾游、做攻略、行程安排、旅行方案时使用。
---

# Help U 2 Travel

生成一份可交互的 HTML 旅行方案，包含总览地图、每日行程、景点详情、美食、住宿、行李清单。

## 工作流程

### Step 1: 需求收集

向用户确认以下信息（缺失项主动询问，不要假设）：

| 字段 | 说明 |
|------|------|
| 出发地 | 城市名 |
| 目的地 | 城市/景区名，可多个 |
| 天数 | 总天数 |
| 人数 | 成人/儿童数量 |
| 交通方式 | 自驾 / 高铁+当地 / 飞机+当地 / 混合 |
| 预算范围 | 人均或总预算（元），用于住宿和餐饮粗筛 |
| 特殊偏好 | 亲子/摄影/徒步/美食/休闲等 |
| 起床时间 | 每天大概几点起（如8:00），用于安排每日时间轴 |
| 车型（如自驾） | 油车/新能源，影响充电规划 |

### Step 1.5: 行程范围确认（必须，不要跳过）

需求收集后、规划路线前，**必须先问用户：这 N 天是否全部待在同一个目的地？**

- **是** → 按单目的地深度游规划（周边景点按天分组）。
- **否** → 不要自行假设，先问清楚：
  1. 用户心里是否已有想去的其他地点（顺路城市、回程途经点、另一个目的地）？
  2. 若没有明确想法，用 `maps_text_search` 搜索主目的地周边 100-200km 内的知名城市/景区（如千岛湖周边：黄山、新安江山水画廊、建德、桐庐），结合用户偏好（亲子/山水/古镇）给出 2-3 个候选组合，让用户选择。
  3. 确定多目的地后，规划串联路线：各城市间用 `maps_direction_driving` 计算实际车程，校验单日驾驶 ≤6 小时，超了就砍点或加天。
- 确认结果（单/多目的地、途经顺序）要复述给用户确认后，再进入 Step 2。

### Step 2: 路线骨架

1. 用高德 `maps_geo` 将出发地和各目的地转为经纬度。
2. 城际段：
   - 自驾 → `maps_direction_driving` 获取路线、里程、耗时。
   - 高铁/飞机 → 用通用搜索查班次和耗时，标注"需用户自行确认实时班次"。
3. **提取完整路线几何（必须）**：`maps_direction_driving` 返回的 `steps[].polyline` 是 `"lng,lat;lng,lat;..."` 格式的字符串，必须逐段解析并合并为 `[[lat,lng], ...]` 数组，存入 `intercity_routes[].polyline`。**只存起终点是不够的**——地图会退化为两点直线，无法展示真实路线。
4. 每条城际路线标注 `day` 字段（第几天发生，返程可标最后一天），用于地图按天筛选。
5. 确定每日住宿城市，确保单日驾驶/移动时间合理（自驾单日 ≤6 小时纯驾驶）。
6. 生成路线总览数据。

数据结构示例：
```json
{
  "from": "合肥", "to": "千岛湖", "mode": "自驾", "day": 1,
  "distance_km": 423, "duration_hours": 5.1,
  "from_lat": 31.82, "from_lng": 117.23,
  "to_lat": 29.61, "to_lng": 118.95,
  "polyline": [[31.82,117.23],[31.79,117.31],[31.70,117.60],"...全程坐标点"]
}
```

### Step 3: 城内行程（按时间轴）

对每个停留城市的每一天，根据用户起床时间生成时间轴：

1. 用 `maps_text_search` 搜索该城市核心景点（关键词："城市名 必去景点"），取 top 8-12。
2. 对每个景点用 `maps_search_detail` 获取地址、评分、营业时间。
3. 用通用搜索补充：门票价格、建议游玩时长、景点专属贴士。
4. 按地理位置聚类排序，分配到每天，每日 2-4 个景点。
5. **生成每日时间轴**（以起床时间为起点）：
   - 起床 → 早餐（30-60分钟）→ 出发 → 景点1（含交通时间）→ 午餐（60-90分钟）→ 景点2 → 晚餐 → 回酒店
   - 景点间交通：用 `maps_direction_transit_integrate`（公共交通）或 `maps_direction_driving`（自驾）或步行估算，列出 2-3 种方式及耗时。
   - 用餐时间锚点：早餐起床后30分钟，午餐12:00左右，晚餐18:00左右。
   - 每天总活动时间 ≤10 小时，留出休息弹性。
   - **时间轴必须累进自检**：每一项的开始时间 = 上一项开始时间 + 上一项耗时。逐项计算一遍再写入，不允许出现时间倒流或重叠（生成脚本会校验并告警）。
6. 每个景点、美食、住宿都标注 `day` 字段（第几天），用于 HTML 按天筛选。
7. **行程项带坐标（必须）**：schedule 中的 `attraction` / `lunch` / `dinner` 项直接写入该地点的 `lat`/`lng`（来自高德 POI），这样地图选中某天时才能按游览顺序编号串联。
8. **每日路线几何（可选增强）**：对当天含驾车/移动的段，可用 `maps_direction_driving` 结果生成 `daily_plan[].route`（每段一个 leg，含 polyline），地图将绘制当天真实行驶路线；没有 route 时地图自动按行程顺序连虚线兜底。

时间轴数据结构：
```json
{
  "daily_plan": [
    {
      "day": 1,
      "date": "2026-08-17",
      "wake_up": "8:00",
      "schedule": [
        {"time": "8:00", "type": "wakeup", "title": "起床"},
        {"time": "8:30", "type": "breakfast", "title": "早餐", "location": "酒店附近"},
        {"time": "9:00", "type": "transport", "title": "前往中心湖区码头", "duration_min": 15, "mode": "自驾"},
        {"time": "9:15", "type": "attraction", "title": "中心湖区（梅峰岛）", "duration_hours": 5, "ref": "attr_1"},
        {"time": "12:00", "type": "lunch", "title": "渔乐岛用餐", "location": "岛上餐厅"},
        {"time": "14:30", "type": "attraction", "title": "月光岛", "duration_hours": 1.5, "ref": "attr_2"},
        {"time": "16:30", "type": "transport", "title": "返回酒店", "duration_min": 20, "mode": "打车"},
        {"time": "18:00", "type": "dinner", "title": "鱼味馆", "ref": "food_1"},
        {"time": "20:00", "type": "leisure", "title": "骑龙巷散步"}
      ]
    }
  ]
}
```

### Step 4: 美食检索

详见 [references/food-research.md](references/food-research.md)。

- 优先小红书，抖音为补充。
- 每个城市检索 1-2 次（如"杭州美食推荐""杭州本地人吃的店"）。
- 判断标准：点赞收藏数 ≥ 阈值；排除模板化文案、统一硬广配图、明显营销号。
- 输出：店名、类型、人均、推荐菜、地址、来源平台。

### Step 5: 住宿筛选

详见 [references/accommodation.md](references/accommodation.md)。

- 位置优先级：景区步行可达 > 城内景点交通枢纽（地铁交汇/市中心）> 其他。
- 价格：用户预算 ±20% 范围粗筛，预检索 8-15 家，HTML 前端做价格区间滑块筛选。
- 用通用搜索检索（"城市名 区域 酒店推荐 价格"），记录酒店名、位置、价格区间、评分、特色。
- 不保证实时价格，标注"价格为参考价，以实际预订为准"。

### Step 6: 天气与行李

1. 用 `maps_weather` 查询各目的地天气（行程日期内）。
2. 生成行李清单：通用清单 + 目的地专属（高原/海边/山区等）+ 天气适配。
   详见 [references/packing-checklist.md](references/packing-checklist.md)。

### Step 7: 生成 HTML

1. 将以上所有数据整理为 JSON 结构。
2. 运行 `scripts/html_generator.py` 生成交互式 HTML。
   详见 [references/html-template.md](references/html-template.md)。
   **脚本会做数据校验（时间轴累进、点位坐标、路线 polyline），出现 ⚠️ 警告必须修复数据后重新生成，不允许带着警告交付。**
3. HTML 包含：总览地图页（按天筛选 + 图层开关）、每日行程时间轴页、景点详情、美食页、住宿页（带价格筛选）、行李清单页。
   - **地图图层开关**：景点/美食/住宿/路线四类标记可单独勾选显示或隐藏，用户可以只看路线、或只看景点。
   - **真实路线**：城际路线和按天路线用 polyline 完整几何绘制，不是两点直线。
   - **按天路线**：选中某天时，地图按当天行程顺序给景点/餐厅编号（第N站）并连线。
4. 用 `present_files` 交付 HTML 文件。

### Step 8: JSON 数据结构规范（必须严格遵守字段名）

模板 JS 直接按字段名读取数据，**字段名写错会导致页面显示 undefined**。以下是模板实际使用的全部字段，生成 JSON 时必须严格匹配。

#### 顶层字段

```json
{
  "title": "旅行方案标题",
  "subtitle": "副标题",
  "coords": "gcj02",
  "days": 4,                        // ← 顶层数字，不要放进 trip_info
  "cities": [...],                   // 景点（按城市分组）
  "foods": [...],                    // 美食
  "accommodations": [...],           // 住宿
  "intercity_routes": [...],         // 城际路线
  "daily_plan": [...],              // 每日时间轴
  "packing": {...},                  // 行李清单
  "weather": {...}                   // 天气
}
```

> **⚠ 常见错误**：把 `days` 放进 `trip_info.days` 会导致总览页显示"undefined天"。`days` 必须是顶层独立字段。

#### cities[].attractions[] 字段

| 字段 | 类型 | 模板用途 | 说明 |
|------|------|----------|------|
| `id` | string | 引用 | 如 "attr_1"，schedule 中 ref 指向此值 |
| `name` | string | 标题 | 景点名称 |
| `lat` | number | 地图标记 | 纬度（来自高德 POI） |
| `lng` | number | 地图标记 | 经度（来自高德 POI） |
| `day` | number | 按天筛选 | 第几天（整数） |
| `duration_hours` | number | "建议游玩 X小时" | **数字**，如 5 表示5小时。不要写字符串"5小时" |
| `ticket` | string | "门票"行 | 票价信息，如 "门票+游船 195元/人" |
| `address` | string | "地址"行 | 详细地址 |
| `tips` | string | "💡"提示行 | 游玩贴士 |
| `rating` | string | 评分 | 如 "4.5" |

#### foods[] 字段

| 字段 | 类型 | 模板用途 | 说明 |
|------|------|----------|------|
| `id` | string | 引用 | 如 "food_1" |
| `name` | string | 标题 | 餐厅名称 |
| `lat` | number | 地图标记 | 纬度 |
| `lng` | number | 地图标记 | 经度 |
| `day` | number | 按天筛选 | 第几天 |
| `type` | string | 分类标签+筛选 | 如 "鱼头汤/湖鲜" |
| `price_per_person` | number | "人均 ¥X" | **数字**，如 80。不要写字符串"人均80-100元" |
| `must_try` | array | 招牌菜 | 如 ["砂锅鱼头", "剁椒鱼头"] |
| `address` | string | "地址"行 | 详细地址 |
| `hours` | string | "营业时间"行 | 如 "10:00-22:00"（可选） |
| `source` | string | 来源标签 | 如 "小红书" / "大众点评" |
| `note` | string | 提示行 | 排队/订座等提示（可选） |

> **⚠ 常见错误**：用 `price`（字符串"人均80元"）代替 `price_per_person`（数字 80）；用 `signature` 代替 `must_try`；用 `tips` 代替 `note`。

#### accommodations[] 字段

| 字段 | 类型 | 模板用途 | 说明 |
|------|------|----------|------|
| `id` | string | 引用 | 如 "hotel_1" |
| `name` | string | 标题 | 酒店名称 |
| `lat` | number | 地图标记 | 纬度 |
| `lng` | number | 地图标记 | 经度 |
| `day` | string/number | "Day X入住"标签 | 如 "1-3" 或 1 |
| `price_min` | number | 价格滑块+显示 | **数字**，如 350。不要写 `price_range` 字符串 |
| `price_max` | number | 价格滑块+显示 | **数字**，如 450 |
| `rating` | string | 评分 | 如 "4.5" |
| `type` | string | 类型标签 | 如 "商务酒店" |
| `area` | string | "📍"位置行 | 区域/地址 |
| `near` | string | "📍"位置行 | 附近地标（可选） |
| `tags` | array | 标签 | 如 ["含早", "停车场"]（可选） |
| `note` | string | 提示行 | 特色/注意事项 |

> **⚠ 常见错误**：用 `price_range`（字符串"350-450元"）代替 `price_min`+`price_max`（两个数字）；用 `address` 代替 `area`；用 `features`/`tips` 代替 `note`。

#### intercity_routes[] 字段

| 字段 | 类型 | 模板用途 | 说明 |
|------|------|----------|------|
| `from` | string | 路线标签 | 出发地 |
| `to` | string | 路线标签 | 目的地 |
| `mode` | string | 路线标签 | "自驾"/"高铁"等 |
| `day` | number | 按天筛选 | 第几天 |
| `distance_km` | number | 路线信息 | 公里数 |
| `duration_hours` | number | 路线信息 | 小时数 |
| `from_lat`/`from_lng` | number | 路线起点 | 经纬度 |
| `to_lat`/`to_lng` | number | 路线终点 | 经纬度 |
| `polyline` | array | **地图路线绘制** | `[[lat,lng],...]` 完整坐标点数组，来自高德 driving steps |
| `waypoints` | string | 路线信息 | 途经点描述（可选） |
| `charging_note` | string | 路线信息 | 充电桩提示（可选） |

#### daily_plan[] 字段

| 字段 | 类型 | 模板用途 | 说明 |
|------|------|----------|------|
| `day` | number | 日期标签 | 第几天 |
| `date` | string | 日期标签 | 如 "2026-08-17" |
| `wake_up` | string | 起床时间 | 如 "7:00" |
| `title` | string | 当日标题 | 如 "中心湖区 · 天屿山日落" |
| `summary` | string | 当日摘要 | 一句话概述 |
| `schedule` | array | 时间轴 | 见下 |

#### schedule[] 项字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `time` | string | 开始时间，如 "8:00"（必须递进，不能倒流） |
| `type` | string | "wakeup"/"breakfast"/"transport"/"attraction"/"lunch"/"dinner"/"hotel"/"leisure" |
| `title` | string | 显示标题 |
| `duration_min` | number | 持续分钟数（transport/lunch/dinner/leisure 用） |
| `duration_hours` | number | 持续小时数（attraction 用） |
| `mode` | string | 交通方式（transport 用），如 "自驾" |
| `distance_km` | number | 驾驶距离（transport 用，可选） |
| `ref` | string | 引用景点/美食的 id（attraction/lunch/dinner 用） |
| `lat`/`lng` | number | 坐标（attraction/lunch/dinner 必须带，用于地图按天路线串联） |
| `location` | string | 地点描述（breakfast/lunch 用，可选） |
| `note` | string | 备注（可选） |

## 关键约束

- **交通方式可扩展**：城际和城内交通都抽象为"方式+耗时+备注"，不要硬编码为自驾。
- **高德工具优先**：路线、POI、天气必须用高德 MCP 工具，不要用通用搜索替代。
- **禁止编造坐标**：所有 lat/lng 和 polyline 必须来自高德 API 的真实返回，严禁凭印象手写坐标——手工估算的坐标会整体偏移数公里，画出来的路线对不上真实道路。检索不到的点宁可从方案中删除，也不要编位置。
- **坐标系**：高德返回的是 GCJ-02 坐标，直接原样写入 JSON 即可（默认 `coords: gcj02`），模板内置 GCJ-02→WGS-84 转换以纠正 OSM 底图偏移；只有数据本身是 WGS-84 时才在 JSON 顶层声明 `"coords": "wgs84"`。
- **美食真实性**：宁少勿滥，营销号内容坚决排除。
- **住宿非实时**：明确标注价格为参考，不做虚假实时承诺。
- **HTML 自包含**：所有 CSS/JS 内联或 CDN，单个 HTML 文件可直接打开。
- **可拓展性**：数据结构和模板设计为多交通方式通用，自驾只是其中一种。

## 工具依赖

- 高德地图 MCP（`maps_geo`, `maps_direction_driving`, `maps_direction_transit_integrate`, `maps_text_search`, `maps_search_detail`, `maps_weather`, `maps_schema_personal_map`）
- 通用搜索（住宿、景点门票、美食补充）
- 浏览器自动化（小红书/抖音美食检索）
