# help-u-2-travel

旅行规划 skill：生成交互式 HTML 旅行方案（总览地图 + 每日行程时间轴 + 景点/美食/住宿/行李）。

## 仓库结构

```
skill/                  # skill 源码（与豆包目录同步）
├── SKILL.md            # 主流程
├── references/         # 方法论文档
├── scripts/            # html_generator.py（JSON → HTML，含数据校验）
└── assets/html-template/template.html
output/                 # 演示数据与生成产物
├── qiandaohu_demo.json # 千岛湖示例数据（真实高德数据）
└── 千岛湖3日自驾方案_v4.html
```

## 部署位置（改动后需手动同步）

| 位置 | 用途 |
|------|------|
| `skill/`（本仓库） | 版本管理的源 |
| `~/Library/Application Support/Doubao/Default/.doubao/agent_mode/workspace/.user_skills/help-u-2-travel/` | 豆包运行副本 |
| `~/.workbuddy/skills/help-u-2-travel/` | WorkBuddy 运行副本（含环境适配段） |

## 开发约定

- 坐标与路线 polyline 必须来自高德 API 真实返回，禁止手工编造（见 skill/references/route-planning.md）
- 修改流程：改本仓库 → 生成器校验零警告 → 同步到两个运行副本
- 生成命令：`python3 skill/scripts/html_generator.py data.json -o output.html`
