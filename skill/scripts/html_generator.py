#!/usr/bin/env python3
"""
旅行方案 HTML 生成器
读取 JSON 数据，注入模板，生成最终 HTML 文件。
生成前对数据做完整性校验，问题项打印警告（不阻断生成，但必须人工核对）。

用法:
    python3 html_generator.py <data.json> -o <output.html>
    python3 html_generator.py <data.json>  # 默认输出 trip_plan.html
"""
import json
import sys
import os
import argparse
from pathlib import Path

TEMPLATE_PATH = Path(__file__).parent.parent / "assets" / "html-template" / "template.html"


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t2min(s):
    """'8:30' -> 510，解析失败返回 None"""
    try:
        h, m = str(s).split(":")[:2]
        return int(h) * 60 + int(m)
    except Exception:
        return None


def validate(data):
    """生成前校验，返回警告列表"""
    warns = []

    # 1. 每日时间轴：时间必须递增，且与上一项耗时衔接合理
    for d in data.get("daily_plan", []) or []:
        label = f"Day {d.get('day', '?')}"
        prev_end = None
        prev_title = ""
        for it in d.get("schedule", []) or []:
            cur = t2min(it.get("time"))
            if cur is None:
                warns.append(f"{label}: 项「{it.get('title')}」时间格式异常: {it.get('time')}")
                continue
            if prev_end is not None and cur < prev_end:
                warns.append(f"{label}: 「{prev_title}」结束于 {prev_end//60}:{prev_end%60:02d}，"
                             f"但「{it.get('title')}」开始于 {it.get('time')}，时间倒流")
            dur = it.get("duration_min")
            dur_h = it.get("duration_hours")
            total = (dur or 0) + int((dur_h or 0) * 60)
            prev_end = cur + (total if total else 0)
            prev_title = it.get("title", "")

    # 2. 点位坐标完整性（没坐标的点位无法标上地图）
    for c in data.get("cities", []) or []:
        for a in c.get("attractions", []) or []:
            if a.get("lat") in (None, "") or a.get("lng") in (None, ""):
                warns.append(f"景点「{a.get('name')}」缺少经纬度，地图上将不显示")
            if a.get("day") in (None, ""):
                warns.append(f"景点「{a.get('name')}」缺少 day 字段，无法按天筛选")
    for f in data.get("foods", []) or []:
        if f.get("lat") in (None, "") or f.get("lng") in (None, ""):
            warns.append(f"美食「{f.get('name')}」缺少经纬度，地图上将不显示")
    for h in data.get("accommodations", []) or []:
        if h.get("lat") in (None, "") or h.get("lng") in (None, ""):
            warns.append(f"住宿「{h.get('name')}」缺少经纬度，地图上将不显示")

    # 3. 城际路线 polyline（没有只能画两点直线的示意线）
    for r in data.get("intercity_routes", []) or []:
        if not r.get("polyline") or len(r.get("polyline", [])) < 2:
            warns.append(f"城际路线「{r.get('from')}→{r.get('to')}」缺少 polyline 几何数据，"
                         f"地图只能画起终点示意直线（应用高德 maps_direction_driving 的 steps 提取完整路线坐标）")

    # 4. 行程项与地图联动：景点/餐饮项建议带坐标（用于按天路线编号串联）
    for d in data.get("daily_plan", []) or []:
        for it in d.get("schedule", []) or []:
            if it.get("type") in ("attraction", "lunch", "dinner") and not it.get("lat"):
                warns.append(f"Day {d.get('day')} 行程项「{it.get('title')}」未带 lat/lng，"
                             f"按天路线串联时会尝试按名称匹配景点库（建议直接写入坐标）")

    # 5. 字段名与模板不匹配的常见错误检测
    # 5a. 顶层 days 必须存在且为数字
    if data.get("days") is None:
        warns.append("顶层缺少 days 字段（数字），总览页将显示'undefined天'。"
                     "注意：days 必须是顶层字段，不能嵌套在 trip_info 内")

    # 5b. 住宿必须用 price_min/price_max（数字），不能用 price_range（字符串）
    for h in data.get("accommodations", []) or []:
        if h.get("price_min") is None and h.get("price_range") is not None:
            warns.append(f"住宿「{h.get('name')}」用了 price_range（字符串），"
                         f"模板需要 price_min + price_max（两个数字），否则价格显示 undefined")
        if h.get("price_min") is not None and not isinstance(h.get("price_min"), (int, float)):
            warns.append(f"住宿「{h.get('name')}」的 price_min 不是数字类型: {type(h.get('price_min')).__name__}")

    # 5c. 美食必须用 price_per_person（数字），不能用 price（字符串）
    for f in data.get("foods", []) or []:
        if f.get("price_per_person") is None and f.get("price") is not None:
            warns.append(f"美食「{f.get('name')}」用了 price（字符串），"
                         f"模板需要 price_per_person（数字），否则人均显示 undefined")

    # 5d. 景点必须用 duration_hours（数字），不能用 duration（字符串）
    for c in data.get("cities", []) or []:
        for a in c.get("attractions", []) or []:
            if a.get("duration_hours") is None and a.get("duration") is not None:
                warns.append(f"景点「{a.get('name')}」用了 duration（字符串），"
                             f"模板需要 duration_hours（数字），否则建议游玩时长显示 undefined")

    return warns


def generate_html(data, output_path):
    if not TEMPLATE_PATH.exists():
        print(f"错误: 模板文件不存在 {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    title = data.get("title", "旅行方案")
    subtitle = data.get("subtitle", "")

    warns = validate(data)
    if warns:
        print(f"⚠️  数据校验发现 {len(warns)} 个问题（已生成，但建议修复后重新生成）:", file=sys.stderr)
        for w in warns:
            print(f"   - {w}", file=sys.stderr)

    trip_data_json = json.dumps(data, ensure_ascii=False, indent=2)

    html = template.replace("__TRIP_TITLE__", title)
    html = html.replace("__TRIP_SUBTITLE__", subtitle)
    html = html.replace("__TRIP_DATA__", trip_data_json)

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"✅ 已生成: {output_path}")
    print(f"   文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="旅行方案 HTML 生成器")
    parser.add_argument("data", help="旅行数据 JSON 文件路径")
    parser.add_argument("-o", "--output", default="trip_plan.html", help="输出 HTML 文件路径")
    args = parser.parse_args()

    if not os.path.exists(args.data):
        print(f"错误: 数据文件不存在 {args.data}", file=sys.stderr)
        sys.exit(1)

    data = load_json(args.data)
    generate_html(data, args.output)


if __name__ == "__main__":
    main()
