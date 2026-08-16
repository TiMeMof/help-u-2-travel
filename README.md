# Help U 2 Travel 🧭

旅行规划 skill：输入需求，产出一份**可交互的单文件 HTML 旅行方案**——真实路线地图、每日行程时间轴、景点/美食/住宿/行李清单，双击浏览器打开即用。

## ✨ 功能一览

| 模块 | 说明 |
|------|------|
| 🗺️ 总览地图 | Leaflet 真实路网路线（高德 API polyline），景点/美食/住宿/路线四类图层可单独开关 |
| 📅 每日行程 | 按起床时间生成时间轴（起床→早餐→交通→景点→…），自动校验时间累进 |
| 🏛️ 景点详情 | 门票、开放时间、建议游玩时长、天气、专属贴士（如"穿防滑鞋"） |
| 🍜 美食 | 小红书/抖音真实热度检索，过滤营销号，标注来源与热度 |
| 🏨 住宿 | 预检索一批后前端价格双滑块筛选，位置优先级排序 |
| 🎒 行李 | 通用 + 自驾专属 + 目的地专属 + 天气适配，可勾选 |

**按天联动**：切到 Day 1/2/3，地图只显示当天点位，按游览顺序给景点编号并连线当日路线。

## 🚀 怎么用

### 方式一：对话触发（推荐）

skill 已安装在豆包和 WorkBuddy 的用户级 skill 目录，直接说人话即可触发：

```
帮我规划一个合肥到千岛湖的 3 天自驾游，预算人均 1500，早上 8 点起
做一个杭州 2 日游方案，高铁出行
规划川西 7 天自驾，重点看住宿和高反应对
```

流程会自动走：**需求收集 → 行程范围确认（是否全程同一目的地）→ 高德查路线/坐标 → 排每日时间轴 → 检美食/住宿 → 生成 HTML**。中间会向你确认目的地范围、住宿偏好等关键决策。

### 方式二：命令行手动生成

已有数据 JSON 时，直接跑生成器：

```bash
python3 skill/scripts/html_generator.py data.json -o 方案.html
```

数据格式参考 `output/qiandaohu_demo.json`。生成器内置校验（时间轴倒流、缺坐标、缺 polyline 等都会打 ⚠️ 警告），**警告清零再交付**。

## 📁 仓库结构

```
skill/
├── SKILL.md                          # 主流程（agent 执行的完整工作流）
├── references/
│   ├── route-planning.md             # 路线方法论 + polyline 提取 + 坐标规范
│   ├── accommodation.md              # 住宿筛选逻辑
│   ├── food-research.md              # 美食检索 + 营销号判断标准
│   ├── packing-checklist.md          # 行李清单模板
│   └── html-template.md              # HTML 模板规范
├── scripts/
│   └── html_generator.py             # JSON → HTML（含数据校验）
└── assets/html-template/
    └── template.html                 # 交互式页面模板
output/                               # 演示：千岛湖 3 日自驾（真实高德数据）
```

## 🔄 部署与同步

| 位置 | 用途 |
|------|------|
| `skill/`（本仓库） | **版本管理的源**，改动从这里开始 |
| 豆包 `.../.user_skills/help-u-2-travel/` | 豆包运行副本 |
| `~/.workbuddy/skills/help-u-2-travel/` | WorkBuddy 运行副本（含环境适配段） |

改完本仓库后，把 `skill/` 内容同步到上面两个运行目录。

## 📐 数据格式速览

核心字段（完整示例见 `output/qiandaohu_demo.json`）：

```jsonc
{
  "coords": "gcj02",              // 高德坐标原样写入，模板自动转 WGS-84
  "cities[].attractions[]":       // 景点：name/day/lat/lng/ticket/duration_hours/tips
  "intercity_routes[]":           // 城际：from/to/day/polyline(完整路线几何!)
  "daily_plan[]":                 // 每日：wake_up/schedule[](时间轴项，景点带lat/lng)/route[]
  "foods[]":                      // name/day/type/price_per_person/heat/source
  "accommodations[]":             // name/day[]/price_min/price_max/near/lat/lng
  "packing": { essential, driving, destination_specific, weather_note }
}
```

## ⚠️ 开发铁律

1. **禁止编造坐标**：所有 lat/lng 和 polyline 必须来自高德 API 真实返回（POI 搜索记得限定区县 `city`，否则会搜到同名地点）。搜不到的点删掉或换点。
2. **路线必须完整几何**：从 `maps_direction_driving` 的 `steps[].polyline` 提取全程坐标（`"lng,lat;lng,lat"` → `[[lat,lng],...]`），只存起终点会被生成器告警。
3. **时间轴必须累进自检**：每项开始时间 = 上一项开始 + 耗时。
4. **HTML 自包含**：单文件可离线打开（地图瓦片和 Leaflet 走 CDN）。
