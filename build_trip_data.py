#!/usr/bin/env python3
"""千岛湖4日自驾方案 - 生成完整旅行数据JSON"""
import json
import urllib.request
import urllib.parse
import os

AMAP_KEY = "77434027b606e7d7535716364c2a5d75"
BASE = "https://restapi.amap.com/v3"

def amap_get(path, params):
    params["key"] = AMAP_KEY
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def driving(origin_lng, origin_lat, dest_lng, dest_lat, waypoint=None):
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "extensions": "all",
        "strategy": 2,
    }
    if waypoint:
        params["waypoints"] = waypoint
    return amap_get("direction/driving", params)

def extract_polyline(driving_result, sample_step=5):
    pts = []
    for step in driving_result.get("route", {}).get("paths", [{}])[0].get("steps", []):
        poly = step.get("polyline", "")
        for seg in poly.split(";"):
            if "," in seg:
                lng, lat = seg.split(",")
                pts.append([float(lat), float(lng)])
    if sample_step > 1 and len(pts) > sample_step:
        sampled = pts[::sample_step]
        if sampled[-1] != pts[-1]:
            sampled.append(pts[-1])
        return sampled
    return pts

# Load existing data
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, "amap_data.json"), "r", encoding="utf-8") as f:
    amap = json.load(f)

# 新安江山水画廊(深渡镇) POI coordinates from search
xaj_lat = 29.862743
xaj_lng = 118.618285

# 千岛湖 coordinates
qd_lat = amap["geo"]["qiandao"]["lat"]
qd_lng = amap["geo"]["qiandao"]["lng"]

# 合肥 coordinates
hf_lat = amap["geo"]["hefei"]["lat"]
hf_lng = amap["geo"]["hefei"]["lng"]

# 徽州古城 coordinates
hz_lat = amap["geo"]["huizhou"]["lat"]
hz_lng = amap["geo"]["huizhou"]["lng"]

# Get Day 4 route: 千岛湖 → 新安江山水画廊(深渡镇) → 合肥
print("Getting Day4 route: 千岛湖 → 深渡镇 → 合肥...")
route_d4a = driving(qd_lng, qd_lat, xaj_lng, xaj_lat)
path_d4a = route_d4a["route"]["paths"][0]
poly_d4a = extract_polyline(route_d4a, sample_step=5)
print(f"  千岛湖→深渡镇: {float(path_d4a['distance'])/1000:.0f}km, {int(path_d4a['duration'])//60}min")

route_d4b = driving(xaj_lng, xaj_lat, hf_lng, hf_lat)
path_d4b = route_d4b["route"]["paths"][0]
poly_d4b = extract_polyline(route_d4b, sample_step=5)
print(f"  深渡镇→合肥: {float(path_d4b['distance'])/1000:.0f}km, {int(path_d4b['duration'])//60}min")

# Merge Day4 full polyline
poly_d4_full = poly_d4a + poly_d4b
dist_d4 = float(path_d4a["distance"])/1000 + float(path_d4b["distance"])/1000
dur_d4 = int(path_d4a["duration"])//60 + int(path_d4b["duration"])//60

# ============ Build Trip Data ============
trip_data = {
    "title": "千岛湖4日自驾之旅",
    "subtitle": "合肥出发 · 途经徽州古城+新安江山水画廊 · 4人新能源自驾",
    "coords": "gcj02",
    "trip_info": {
        "departure": "合肥",
        "destination": "千岛湖",
        "days": 4,
        "people": 4,
        "vehicle_type": "新能源车",
        "accommodation_budget": "400元/晚/间",
        "total_driving_km": round(amap["routes"]["day1_full"]["distance_km"] + dist_d4, 0),
    },
    "weather": {
        "city": "淳安县（千岛湖）",
        "casts": [],
        "note": "8月中旬高温多雨，注意防暑防雨，正午避免户外暴晒"
    },
}

# Weather
if amap.get("weather", {}).get("forecasts"):
    for c in amap["weather"]["forecasts"][0].get("casts", []):
        trip_data["weather"]["casts"].append({
            "date": c["date"],
            "day_weather": c["dayweather"],
            "day_temp": c["daytemp"],
            "night_temp": c["nighttemp"],
            "wind": f"{c['daywind']}风{c['daypower']}",
        })

# Cities & Attractions
trip_data["cities"] = [
    {
        "name": "千岛湖",
        "days": [2, 3],
        "attractions": [
            {
                "id": "attr_1", "name": "千岛湖中心湖区（梅峰岛·渔乐岛·龙山岛）",
                "lat": 29.596547, "lng": 119.005926, "day": 2,
                "address": "杭州市淳安县梦姑路348号",
                "ticket": "门票+游船 195元/人（经济舱），畅游套票168元/人",
                "duration": "5小时（含游船）",
                "hours": "8:00-15:30（游船8:00-14:00发船）",
                "tips": "必登梅峰岛俯瞰千岛全景，缆车往返60元可选；渔乐岛可午餐补给；建议赶早班船（8:30-9:00最佳），自带零食水；游船A线含月光岛/渔乐岛/梅峰岛",
                "rating": "4.3",
            },
            {
                "id": "attr_2", "name": "天屿山观景台",
                "lat": 29.627268, "lng": 119.047662, "day": 2,
                "address": "杭州市淳安县天屿路天屿风景旅游度假区内",
                "ticket": "门票50元，门票+景观扶梯72元，+森林水滑道175元",
                "duration": "1.5-2小时",
                "hours": "8:00-20:00",
                "tips": "千岛湖最佳日落观景点，扶梯上山省力，山顶俯瞰岛屿星罗棋布，强烈推荐傍晚前往看日落",
                "rating": "4.6",
            },
            {
                "id": "attr_3", "name": "千岛湖东南湖区（黄山尖·天池岛·桂花岛）",
                "lat": 29.585378, "lng": 119.076233, "day": 3,
                "address": "杭州市淳安县千岛湖东南湖区旅游码头",
                "ticket": "门票+游船 45.5元/人起，含黄山尖缆车80.5元/人",
                "duration": "4小时（含游船）",
                "hours": "8:00-15:00（游船8:00-14:00发船）",
                "tips": "游客比中心湖区少，水更清；黄山尖可看'天下为公'群岛奇观；天池岛有古采石遗迹；桂花岛有猴子，亲子友好",
                "rating": "4.5",
            },
            {
                "id": "attr_4", "name": "环湖自驾（淳杨线·千汾线精华段）",
                "lat": 29.5038, "lng": 118.95, "day": 3,
                "address": "千岛湖环湖公路",
                "ticket": "免费",
                "duration": "2-3小时",
                "hours": "全天",
                "tips": "自驾最美路段：淳杨线（千岛湖镇→汾口方向）沿途湖光山色，上江埠大桥观景台必停，小金山观景台视野绝佳；沿途看到观景台随时停",
                "rating": "4.7",
            },
            {
                "id": "attr_5", "name": "下姜村",
                "lat": 29.448, "lng": 118.88, "day": 3,
                "address": "杭州市淳安县下姜村",
                "ticket": "免费",
                "duration": "1小时",
                "hours": "全天",
                "tips": "电影《我和我的家乡》取景地，美丽乡村示范村，适合拍照打卡休息",
                "rating": "4.4",
            },
            {
                "id": "attr_6", "name": "骑龙巷",
                "lat": 29.603547, "lng": 119.044615, "day": 2,
                "address": "千岛湖镇排岭南路",
                "ticket": "免费",
                "duration": "1小时",
                "hours": "全天",
                "tips": "千岛湖镇最热闹的步行街，夜逛好去处，各种小吃特产，鱼味馆总店就在旁边",
                "rating": "4.2",
            },
            {
                "id": "attr_7", "name": "千岛湖秀水广场",
                "lat": 29.61409, "lng": 119.042279, "day": 2,
                "address": "千岛湖镇阳光路17号",
                "ticket": "免费",
                "duration": "0.5-1小时",
                "hours": "全天",
                "tips": "滨湖广场，湖景开阔，适合散步休息拍照",
                "rating": "4.3",
            },
        ]
    },
    {
        "name": "歙县（徽州古城）",
        "days": [1],
        "attractions": [
            {
                "id": "attr_8", "name": "徽州古城",
                "lat": 29.86602, "lng": 118.436772, "day": 1,
                "address": "黄山市歙县徽州路93号",
                "ticket": "古城免费，徽州府衙日游票44.5元/人",
                "duration": "1.5-2小时",
                "hours": "全天开放（府衙8:00-17:00）",
                "tips": "中国四大古城之一，许国石坊（八脚牌楼）全国罕见，斗山街古巷必逛，徽州府衙有沉浸式演出；早上8点前进入免门票",
                "rating": "4.2",
            },
            {
                "id": "attr_9", "name": "渔梁坝",
                "lat": 29.85649, "lng": 118.448628, "day": 1,
                "address": "黄山市歙县徽城镇渔梁村",
                "ticket": "免费",
                "duration": "1小时",
                "hours": "全天",
                "tips": "唐代水利工程，徽商发源地，坝上可玩水看日落，渔梁古镇保存完好，青石板路配粉墙黛瓦",
                "rating": "4.4",
            },
        ]
    },
    {
        "name": "新安江山水画廊",
        "days": [4],
        "attractions": [
            {
                "id": "attr_10", "name": "新安江山水画廊",
                "lat": 29.862743, "lng": 118.618285, "day": 4,
                "address": "黄山市歙县深渡镇黄山大道",
                "ticket": "门票+船票+九姓捕鱼 138元/人",
                "duration": "3小时（游船全程）",
                "hours": "9:00-15:00（建议9:00早班船）",
                "tips": "东方多瑙河，全程3小时游船，两岸徽派村落+山水如画；含九姓捕鱼表演；建议加30元升二层观景舱拍照；中途停靠漳潭村看千年古樟",
                "rating": "4.5",
            },
        ]
    },
]

# Intercity routes
trip_data["intercity_routes"] = [
    {
        "from": "合肥", "to": "千岛湖", "mode": "自驾", "day": 1,
        "distance_km": round(amap["routes"]["day1_full"]["distance_km"], 0),
        "duration_hours": round(amap["routes"]["day1_full"]["duration_min"] / 60, 1),
        "from_lat": hf_lat, "from_lng": hf_lng,
        "to_lat": qd_lat, "to_lng": qd_lng,
        "polyline": amap["routes"]["day1_full"]["polyline"],
        "waypoints": "徽州古城(午餐) → 渔梁坝",
        "charging_note": "全程约423km，建议在铜陵服务区（约200km处）充电30-40分钟",
    },
    {
        "from": "千岛湖", "to": "合肥", "mode": "自驾", "day": 4,
        "distance_km": round(dist_d4, 0),
        "duration_hours": round(dur_d4 / 60, 1),
        "from_lat": qd_lat, "from_lng": qd_lng,
        "to_lat": hf_lat, "to_lng": hf_lng,
        "polyline": poly_d4_full,
        "waypoints": "新安江山水画廊(游船) → 深渡镇(午餐)",
        "charging_note": f"全程约{dist_d4:.0f}km，建议在黄山/铜陵服务区充电",
    },
]

# Foods
trip_data["foods"] = [
    {
        "id": "food_1", "name": "千岛湖鱼味馆（排岭南路总店）",
        "lat": 29.603547, "lng": 119.044615, "day": 2,
        "type": "鱼头汤/湖鲜",
        "price": "人均120-150元",
        "signature": "砂锅浓汤鱼头、剁椒鱼头、清蒸白条",
        "address": "千岛湖镇排岭南路（骑龙巷旁）",
        "source": " ima旅游知识库 + 大众点评",
        "tips": "与有机鱼养殖基地直供，鱼头汤正宗，设大型停车场与包厢，本地老字号",
    },
    {
        "id": "food_2", "name": "淳安味道·千岛湖鱼头大排档",
        "lat": 29.609265, "lng": 119.061688, "day": 2,
        "type": "鱼头/本土菜",
        "price": "人均80-100元",
        "signature": "砂锅浓汤鱼头（一汤三吃）、酱爆螺蛳、淳安米羹、米粿",
        "address": "千岛湖镇新安北路42-6号",
        "source": "2026年美食榜单",
        "tips": "本地消费者占比72%，鲜辣浓醇全品类本土风味，融合徽菜与杭帮菜特色",
    },
    {
        "id": "food_3", "name": "鱼味无穷（新安东路）",
        "lat": 29.604125, "lng": 119.045825, "day": 3,
        "type": "家常鱼头/平价湖鲜",
        "price": "人均60-80元",
        "signature": "雪菜烧鱼头配鱼尾、一鱼两吃",
        "address": "千岛湖镇新安东路",
        "source": "ima旅游知识库",
        "tips": "本地人'日常食堂'，亲民实惠，性价比之王",
    },
    {
        "id": "food_4", "name": "淳圆外·寻味古村落",
        "lat": 29.599981, "lng": 119.05407, "day": 3,
        "type": "湖景鱼头/农家菜",
        "price": "人均80-100元",
        "signature": "古法鱼头汤（98元够3人）、鸡汤鱼滑豆腐、剁椒鱼头",
        "address": "千岛湖镇梦姑路近夜游码头",
        "source": "2026年美食攻略",
        "tips": "临湖景观餐厅，本地人常去，性价比高，节假日建议提前订座",
    },
    {
        "id": "food_5", "name": "鱼街餐饮带",
        "lat": 29.603346, "lng": 119.044073, "day": 1,
        "type": "湖鲜/排档",
        "price": "人均80-120元",
        "signature": "鱼头汤、葱油桂鱼、库区螺蛳、河虾",
        "address": "千岛湖镇排岭南路一带",
        "source": "ima旅游知识库",
        "tips": "多家湖鲜馆聚集，可货比三家，夜宵好去处，适合第一天到达后就近用餐",
    },
    {
        "id": "food_6", "name": "深渡镇包袱饺",
        "lat": 29.862743, "lng": 118.618285, "day": 4,
        "type": "徽州小吃",
        "price": "人均10-30元",
        "signature": "深渡包袱饺（蒸煎两吃）、石头粿",
        "address": "黄山市歙县深渡镇",
        "source": "携程攻略",
        "tips": "徽商赶船时的干粮，央视来拍过，外形像小包袱，10元一份",
    },
    {
        "id": "food_7", "name": "披云山庄（徽州古城店）",
        "lat": 29.86602, "lng": 118.436772, "day": 1,
        "type": "徽菜",
        "price": "人均80元",
        "signature": "臭鳜鱼、问政山笋、毛豆腐",
        "address": "歙县徽州古城附近",
        "source": "携程攻略",
        "tips": "本地人推荐，臭鳜鱼闻着臭吃着香，山笋鲜到舌尖跳舞",
    },
]

# Accommodations
trip_data["accommodations"] = [
    {
        "id": "hotel_1", "name": "景廷酒店（杭州千岛湖景区银泰城店）",
        "lat": 29.604076, "lng": 119.054386, "day": [1, 2, 3],
        "price_range": "350-450元",
        "rating": "4.5",
        "type": "商务酒店",
        "address": "淳安县千岛湖镇银泰城",
        "features": "近银泰城商圈，吃饭购物方便，距中心湖区码头约10分钟车程",
        "tips": "性价比高，房间较新，适合自驾入住",
    },
    {
        "id": "hotel_2", "name": "千岛湖山水宾馆",
        "lat": 29.601509, "lng": 119.051683, "day": [1, 2, 3],
        "price_range": "300-400元",
        "rating": "4.2",
        "type": "经济型酒店",
        "address": "淳安县千岛湖镇",
        "features": "城区中心位置，生活便利，周边餐饮多",
        "tips": "老牌宾馆，价格实惠，适合预算有限的旅客",
    },
    {
        "id": "hotel_3", "name": "汉庭酒店（千岛湖银泰广场店）",
        "lat": 29.604772, "lng": 119.054551, "day": [1, 2, 3],
        "price_range": "250-350元",
        "rating": "4.3",
        "type": "连锁经济型",
        "address": "淳安县千岛湖镇银泰广场",
        "features": "全国连锁品质统一，近银泰广场，停车方便",
        "tips": "性价比极高，连锁品牌有保障，适合追求稳定的旅客",
    },
    {
        "id": "hotel_4", "name": "千岛湖心悦酒店（千岛湖广场银泰城店）",
        "lat": 29.604, "lng": 119.054, "day": [1, 2, 3],
        "price_range": "350-450元",
        "rating": "4.4",
        "type": "精品酒店",
        "address": "淳安县千岛湖广场银泰城",
        "features": "近千岛湖广场，城中湖码头步行可达",
        "tips": "装修较新，服务好，位置佳",
    },
    {
        "id": "hotel_5", "name": "安鑫酒店（千岛湖风景区城中湖码头银泰城店）",
        "lat": 29.603, "lng": 119.055, "day": [1, 2, 3],
        "price_range": "300-400元",
        "rating": "4.3",
        "type": "商务酒店",
        "address": "淳安县千岛湖镇城中湖码头银泰城",
        "features": "紧邻城中湖码头，湖景房可选",
        "tips": "位置优越，步行可达码头和骑龙巷",
    },
    {
        "id": "hotel_6", "name": "山都酒店",
        "lat": 29.605, "lng": 119.052, "day": [1, 2, 3],
        "price_range": "280-380元",
        "rating": "4.1",
        "type": "经济型酒店",
        "address": "淳安县千岛湖镇",
        "features": "城区位置，交通便利",
        "tips": "价格亲民，适合4人出行分摊费用",
    },
]

# Daily Plan
trip_data["daily_plan"] = [
    # Day 1
    {
        "day": 1, "date": "2026-08-17", "wake_up": "7:00",
        "title": "合肥 → 徽州古城 → 千岛湖",
        "summary": f"全程约{amap['routes']['day1_full']['distance_km']:.0f}km，驾车约5小时，途经徽州古城午餐+游览",
        "schedule": [
            {"time": "7:00", "type": "wakeup", "title": "起床"},
            {"time": "7:30", "type": "breakfast", "title": "早餐", "location": "家中/路上解决", "duration_min": 30},
            {"time": "8:00", "type": "transport", "title": "合肥出发 → 徽州古城", "duration_min": 210, "mode": "自驾", "distance_km": 313, "note": "建议在铜陵服务区充电30分钟"},
            {"time": "11:30", "type": "attraction", "title": "徽州古城（许国石坊·徽州府衙·斗山街）", "duration_hours": 1.5, "ref": "attr_8", "lat": 29.86602, "lng": 118.436772},
            {"time": "13:00", "type": "lunch", "title": "披云山庄（臭鳜鱼·问政山笋）", "duration_min": 60, "ref": "food_7", "lat": 29.86602, "lng": 118.436772},
            {"time": "14:00", "type": "attraction", "title": "渔梁坝（唐代水利工程·渔梁古镇）", "duration_hours": 1, "ref": "attr_9", "lat": 29.85649, "lng": 118.448628},
            {"time": "15:00", "type": "transport", "title": "徽州古城 → 千岛湖镇", "duration_min": 150, "mode": "自驾", "distance_km": 170, "note": "可在深渡镇服务区充电"},
            {"time": "17:30", "type": "hotel", "title": "入住酒店（千岛湖镇）", "duration_min": 30},
            {"time": "18:00", "type": "dinner", "title": "鱼街餐饮带（鱼头汤·湖鲜）", "duration_min": 90, "ref": "food_5", "lat": 29.603346, "lng": 119.044073},
            {"time": "20:00", "type": "leisure", "title": "骑龙巷夜逛", "duration_min": 60, "lat": 29.603547, "lng": 119.044615},
        ],
    },
    # Day 2
    {
        "day": 2, "date": "2026-08-18", "wake_up": "7:00",
        "title": "千岛湖中心湖区 · 天屿山日落",
        "summary": "中心湖区游船（梅峰岛·渔乐岛·龙山岛）+ 天屿山观景台看日落",
        "schedule": [
            {"time": "7:00", "type": "wakeup", "title": "起床"},
            {"time": "7:30", "type": "breakfast", "title": "早餐", "location": "酒店", "duration_min": 30},
            {"time": "8:00", "type": "transport", "title": "前往中心湖区码头", "duration_min": 15, "mode": "自驾"},
            {"time": "8:15", "type": "attraction", "title": "中心湖区游船（梅峰岛→渔乐岛→龙山岛）", "duration_hours": 5, "ref": "attr_1", "lat": 29.596547, "lng": 119.005926, "note": "门票+游船195元/人，梅峰岛缆车60元可选"},
            {"time": "13:15", "type": "lunch", "title": "渔乐岛/码头附近午餐", "duration_min": 60, "location": "渔乐岛餐厅/码头"},
            {"time": "14:30", "type": "leisure", "title": "秀水广场滨湖散步", "duration_min": 60, "lat": 29.61409, "lng": 119.042279},
            {"time": "16:00", "type": "attraction", "title": "天屿山观景台（看日落）", "duration_hours": 2, "ref": "attr_2", "lat": 29.627268, "lng": 119.047662, "note": "门票+扶梯72元，最佳日落点"},
            {"time": "18:30", "type": "dinner", "title": "淳安味道·鱼头大排档", "duration_min": 90, "ref": "food_2", "lat": 29.609265, "lng": 119.061688},
            {"time": "20:30", "type": "leisure", "title": "千岛湖夜游（可选）", "duration_min": 60, "note": "游船含餐190元/人"},
        ],
    },
    # Day 3
    {
        "day": 3, "date": "2026-08-19", "wake_up": "7:00",
        "title": "东南湖区 · 环湖自驾",
        "summary": "东南湖区游船（黄山尖·天池岛）+ 下午环湖自驾（淳杨线·下姜村）",
        "schedule": [
            {"time": "7:00", "type": "wakeup", "title": "起床"},
            {"time": "7:30", "type": "breakfast", "title": "早餐", "location": "酒店", "duration_min": 30},
            {"time": "8:00", "type": "transport", "title": "前往东南湖区码头", "duration_min": 20, "mode": "自驾"},
            {"time": "8:20", "type": "attraction", "title": "东南湖区游船（黄山尖·天池岛·桂花岛）", "duration_hours": 4, "ref": "attr_3", "lat": 29.585378, "lng": 119.076233, "note": "门票+游船45.5元起，含缆车80.5元"},
            {"time": "12:20", "type": "lunch", "title": "码头附近午餐", "duration_min": 60},
            {"time": "13:30", "type": "transport", "title": "环湖自驾出发（淳杨线）", "duration_min": 30, "mode": "自驾", "note": "千岛湖最美自驾环线"},
            {"time": "14:00", "type": "attraction", "title": "环湖自驾（上江埠大桥·小金山观景台）", "duration_hours": 2, "ref": "attr_4", "lat": 29.5038, "lng": 118.95},
            {"time": "16:00", "type": "attraction", "title": "下姜村（《我和我的家乡》取景地）", "duration_hours": 1, "ref": "attr_5", "lat": 29.448, "lng": 118.88},
            {"time": "17:00", "type": "transport", "title": "返回千岛湖镇", "duration_min": 60, "mode": "自驾"},
            {"time": "18:30", "type": "dinner", "title": "鱼味无穷（雪菜烧鱼头·一鱼两吃）", "duration_min": 90, "ref": "food_3", "lat": 29.604125, "lng": 119.045825},
            {"time": "20:30", "type": "leisure", "title": "酒店休息/湖边散步", "duration_min": 60},
        ],
    },
    # Day 4
    {
        "day": 4, "date": "2026-08-20", "wake_up": "7:00",
        "title": "千岛湖 → 新安江山水画廊 → 合肥",
        "summary": f"返程途经新安江山水画廊游船（3h），全程约{dist_d4:.0f}km",
        "schedule": [
            {"time": "7:00", "type": "wakeup", "title": "起床"},
            {"time": "7:30", "type": "breakfast", "title": "早餐+退房", "location": "酒店", "duration_min": 30},
            {"time": "8:00", "type": "transport", "title": "千岛湖出发 → 新安江山水画廊（深渡镇）", "duration_min": 90, "mode": "自驾", "distance_km": 80},
            {"time": "9:30", "type": "attraction", "title": "新安江山水画廊游船（3h·九姓捕鱼）", "duration_hours": 3, "ref": "attr_10", "lat": 29.862743, "lng": 118.618285, "note": "门票+船票138元/人，建议升二层观景舱+30元"},
            {"time": "12:30", "type": "lunch", "title": "深渡镇包袱饺+石头粿", "duration_min": 45, "ref": "food_6", "lat": 29.862743, "lng": 118.618285},
            {"time": "13:15", "type": "transport", "title": "深渡镇 → 合肥", "duration_min": 240, "mode": "自驾", "distance_km": 350, "note": "建议在黄山/铜陵服务区充电"},
            {"time": "17:15", "type": "leisure", "title": "到达合肥，行程结束"},
        ],
    },
]

# Packing list
trip_data["packing"] = {
    "essential": [
        "身份证、驾驶证、行驶证", "车险保单（电子+纸质）", "银行卡、少量现金",
        "手机、充电器、充电宝", "行车记录仪（确认正常工作）", "车载充电器（Type-C/USB）",
        "肠胃药、感冒药、退烧药、创可贴", "晕车药（按需）", "洗漱用品、换洗衣物（3-4套）",
        "雨伞/雨衣", "纸巾、湿巾", "保温杯", "防晒霜（SPF50+）", "墨镜、帽子",
    ],
    "driving": [
        "新能源车充电卡/APP（国网e充电/特来电）", "备胎（确认胎压）、千斤顶、轮胎扳手",
        "三角警示牌、反光背心", "灭火器（有效期内）", "车载充气泵",
        "离线地图（提前下载皖南山区+浙西山区）", "玻璃水",
    ],
    "destination_specific": [
        "泳衣（千岛湖可游泳/水上项目）", "驱蚊液", "防水手机袋",
        "舒适步行鞋（岛上步行多）", "遮阳帽/防晒衣（湖区紫外线强）",
        "外套（早晚湖区温差，8月夜间约25°C）",
    ],
    "weather_note": "千岛湖8月17-20日：小雨转阴到多云，气温25-35°C，高温高湿。注意防暑降温、带雨具、避开正午户外暴晒。游船有遮阳棚但建议带防晒霜。",
}

# Save trip data
output_path = os.path.join(script_dir, "trip_data.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(trip_data, f, ensure_ascii=False, indent=2)
print(f"\n✅ 旅行数据已保存: {output_path}")
print(f"   景点: {sum(len(c['attractions']) for c in trip_data['cities'])} 个")
print(f"   美食: {len(trip_data['foods'])} 家")
print(f"   住宿: {len(trip_data['accommodations'])} 家")
print(f"   天数: {len(trip_data['daily_plan'])} 天")
print(f"   城际路线: {len(trip_data['intercity_routes'])} 条")
