#!/usr/bin/env python3
"""千岛湖自驾方案 - 高德API数据抓取脚本"""
import json
import urllib.request
import urllib.parse
import sys
import os

AMAP_KEY = "77434027b606e7d7535716364c2a5d75"
BASE = "https://restapi.amap.com/v3"

def amap_get(path, params):
    params["key"] = AMAP_KEY
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def geo(address, city=None):
    params = {"address": address}
    if city:
        params["city"] = city
    d = amap_get("geocode/geo", params)
    if d.get("geocodes"):
        r = d["geocodes"][0]
        loc = r["location"]
        lng, lat = loc.split(",")
        return {"lat": float(lat), "lng": float(lng), "district": r.get("district", ""),
                "formatted": r.get("formatted_address", "")}
    return None

def driving(origin_lng, origin_lat, dest_lng, dest_lat, waypoint=None):
    params = {
        "origin": f"{origin_lng},{origin_lat}",
        "destination": f"{dest_lng},{dest_lat}",
        "extensions": "all",
        "strategy": 2,  # 速度优先
    }
    if waypoint:
        params["waypoints"] = waypoint
    return amap_get("direction/driving", params)

def extract_polyline(driving_result, sample_step=5):
    """从driving结果中提取完整polyline坐标点，降采样"""
    pts = []
    for step in driving_result.get("route", {}).get("paths", [{}])[0].get("steps", []):
        poly = step.get("polyline", "")
        for seg in poly.split(";"):
            if "," in seg:
                lng, lat = seg.split(",")
                pts.append([float(lat), float(lng)])  # [lat, lng]
    # 降采样：每N个点取1个
    if sample_step > 1 and len(pts) > sample_step:
        sampled = pts[::sample_step]
        if sampled[-1] != pts[-1]:
            sampled.append(pts[-1])
        return sampled
    return pts

def text_search(keywords, city, types=None, limit=10):
    params = {"keywords": keywords, "city": city, "offset": limit, "page": 1}
    if types:
        params["types"] = types
    d = amap_get("place/text", params)
    pois = d.get("pois", [])
    result = []
    for p in pois[:limit]:
        loc = p.get("location", "")
        if "," in loc:
            lng, lat = loc.split(",")
            result.append({
                "name": p.get("name", ""),
                "lat": float(lat), "lng": float(lng),
                "address": p.get("address", ""),
                "type": p.get("type", ""),
                "tel": p.get("tel", ""),
                "poi_id": p.get("id", ""),
                "district": p.get("adname", ""),
            })
    return result

def weather(city_code):
    d = amap_get("weather/weatherInfo", {"city": city_code, "extensions": "all"})
    return d

def search_detail(poi_id):
    d = amap_get("place/detail", {"id": poi_id})
    return d

# ============ Main ============
print("=" * 60)
print("千岛湖自驾方案 - 高德API数据抓取")
print("=" * 60)

# 1. Geo coding
print("\n[1] 地理编码...")
hefei = geo("合肥")
print(f"  合肥: {hefei['lng']},{hefei['lat']} ({hefei['district']})")

qiandao = geo("千岛湖风景区", city="杭州")
print(f"  千岛湖: {qiandao['lng']},{qiandao['lat']} ({qiandao['district']})")

huizhou = geo("徽州古城", city="黄山")
if not huizhou:
    huizhou = geo("歙县徽州古城")
print(f"  徽州古城: {huizhou['lng']},{huizhou['lat']} ({huizhou['district']})")

xinanjing = geo("新安江山水画廊", city="黄山")
if not xinanjing:
    xinanjing = geo("新安江山水画廊")
print(f"  新安江山水画廊: {xinanjing['lng']},{xinanjing['lat']} ({xinanjing['district']})")

jiande = geo("建德", city="杭州")
print(f"  建德: {jiande['lng']},{jiande['lat']} ({jiande['district']})")

# 2. Driving routes
print("\n[2] 驾车路线...")
# Day 1: 合肥 → 徽州古城 (途经)
route1 = driving(hefei["lng"], hefei["lat"], huizhou["lng"], huizhou["lat"])
path1 = route1["route"]["paths"][0]
poly1 = extract_polyline(route1, sample_step=5)
print(f"  合肥→徽州古城: {float(path1['distance'])/1000:.0f}km, {int(path1['duration'])//60}min, {len(poly1)} points")

# 徽州古城 → 新安江山水画廊
route2 = driving(huizhou["lng"], huizhou["lat"], xinanjing["lng"], xinanjing["lat"])
path2 = route2["route"]["paths"][0]
poly2 = extract_polyline(route2, sample_step=5)
print(f"  徽州古城→新安江: {float(path2['distance'])/1000:.0f}km, {int(path2['duration'])//60}min, {len(poly2)} points")

# 新安江山水画廊 → 千岛湖
route3 = driving(xinanjing["lng"], xinanjing["lat"], qiandao["lng"], qiandao["lat"])
path3 = route3["route"]["paths"][0]
poly3 = extract_polyline(route3, sample_step=5)
print(f"  新安江→千岛湖: {float(path3['distance'])/1000:.0f}km, {int(path3['duration'])//60}min, {len(poly3)} points")

# 合并 Day1 完整路线 (合肥→千岛湖，途经徽州古城和新安江)
waypoint = f"{huizhou['lng']},{huizhou['lat']}|{xinanjing['lng']},{xinanjing['lat']}"
route_full = driving(hefei["lng"], hefei["lat"], qiandao["lng"], qiandao["lat"], waypoint=waypoint)
path_full = route_full["route"]["paths"][0]
poly_full = extract_polyline(route_full, sample_step=5)
print(f"  合肥→千岛湖(全程途经): {float(path_full['distance'])/1000:.0f}km, {int(path_full['duration'])//60}min, {len(poly_full)} points")

# Day 4: 千岛湖 → 合肥 (返程直达)
route_back = driving(qiandao["lng"], qiandao["lat"], hefei["lng"], hefei["lat"])
path_back = route_back["route"]["paths"][0]
poly_back = extract_polyline(route_back, sample_step=5)
print(f"  千岛湖→合肥(返程): {float(path_back['distance'])/1000:.0f}km, {int(path_back['duration'])//60}min, {len(poly_back)} points")

# 3. POI搜索 - 千岛湖景点
print("\n[3] 千岛湖景点搜索...")
attractions_qdh = text_search("千岛湖 景点", "杭州", limit=15)
print(f"  找到 {len(attractions_qdh)} 个景点")
for a in attractions_qdh[:8]:
    print(f"    - {a['name']} ({a['district']})")

# 沿途景点 - 徽州古城
print("\n[4] 徽州古城景点搜索...")
attractions_hz = text_search("徽州古城 景点", "黄山", limit=10)
print(f"  找到 {len(attractions_hz)} 个景点")
for a in attractions_hz[:5]:
    print(f"    - {a['name']} ({a['district']})")

# 新安江景点
print("\n[5] 新安江山水画廊搜索...")
attractions_xaj = text_search("新安江山水画廊", "黄山", limit=8)
print(f"  找到 {len(attractions_xaj)} 个景点")
for a in attractions_xaj[:5]:
    print(f"    - {a['name']} ({a['district']})")

# 建德景点
print("\n[6] 建德景点搜索...")
attractions_jd = text_search("建德 景点", "杭州", limit=8)
print(f"  找到 {len(attractions_jd)} 个景点")
for a in attractions_jd[:5]:
    print(f"    - {a['name']} ({a['district']})")

# 4. 美食搜索
print("\n[7] 千岛湖美食搜索...")
foods = text_search("千岛湖 鱼头 美食", "杭州", limit=12)
print(f"  找到 {len(foods)} 家餐厅")
for f in foods[:6]:
    print(f"    - {f['name']} ({f['address'][:30]})")

# 歙县美食
foods_sx = text_search("歙县 美食", "黄山", limit=8)
print(f"  歙县找到 {len(foods_sx)} 家餐厅")

# 5. 住宿搜索
print("\n[8] 千岛湖住宿搜索...")
hotels = text_search("千岛湖 酒店", "杭州", limit=15)
print(f"  找到 {len(hotels)} 家酒店")
for h in hotels[:6]:
    print(f"    - {h['name']} ({h['district']})")

# 6. 充电桩搜索
print("\n[9] 充电桩搜索...")
# 合肥出发沿途充电桩
charge_hf = text_search("充电站", "合肥", limit=5)
charge_tr = text_search("充电站", "铜陵", limit=3)
charge_hs = text_search("充电站", "黄山", limit=5)
charge_qdh = text_search("充电站", "淳安", limit=5)
print(f"  合肥充电站: {len(charge_hf)}, 铜陵: {len(charge_tr)}, 黄山: {len(charge_hs)}, 淳安: {len(charge_qdh)}")

# 7. 天气
print("\n[10] 天气查询...")
# 千岛湖在淳安县，城市编码需要查询
weather_hz = weather("330127")  # 淳安县
if weather_hz.get("forecasts"):
    for cast in weather_hz["forecasts"][0].get("casts", []):
        print(f"  {cast['date']} {cast['dayweather']} {cast['daytemp']}°C/{cast['nighttemp']}°C {cast['daywind']}风{cast['daypower']}")
else:
    print(f"  天气查询结果: {json.dumps(weather_hz, ensure_ascii=False)[:200]}")

weather_hf = weather("340100")  # 合肥
if weather_hf.get("forecasts"):
    for cast in weather_hf["forecasts"][0].get("casts", [])[:2]:
        print(f"  合肥 {cast['date']} {cast['dayweather']} {cast['daytemp']}°C/{cast['nighttemp']}°C")

# ============ Save all data ============
output = {
    "geo": {
        "hefei": hefei,
        "qiandao": qiandao,
        "huizhou": huizhou,
        "xinanjing": xinanjing,
        "jiande": jiande,
    },
    "routes": {
        "day1_hefei_to_huizhou": {
            "polyline": poly1,
            "distance_km": float(path1["distance"]) / 1000,
            "duration_min": int(path1["duration"]) // 60,
        },
        "huizhou_to_xinanjing": {
            "polyline": poly2,
            "distance_km": float(path2["distance"]) / 1000,
            "duration_min": int(path2["duration"]) // 60,
        },
        "xinanjing_to_qiandao": {
            "polyline": poly3,
            "distance_km": float(path3["distance"]) / 1000,
            "duration_min": int(path3["duration"]) // 60,
        },
        "day1_full": {
            "polyline": poly_full,
            "distance_km": float(path_full["distance"]) / 1000,
            "duration_min": int(path_full["duration"]) // 60,
        },
        "day4_back": {
            "polyline": poly_back,
            "distance_km": float(path_back["distance"]) / 1000,
            "duration_min": int(path_back["duration"]) // 60,
        },
    },
    "attractions_qdh": attractions_qdh,
    "attractions_hz": attractions_hz,
    "attractions_xaj": attractions_xaj,
    "attractions_jd": attractions_jd,
    "foods": foods,
    "foods_sx": foods_sx,
    "hotels": hotels,
    "charge_stations": {
        "hefei": charge_hf,
        "tongling": charge_tr,
        "huangshan": charge_hs,
        "chunan": charge_qdh,
    },
    "weather": weather_hz,
    "weather_hefei": weather_hf,
}

script_dir = os.path.dirname(os.path.abspath(__file__))
output_path = os.path.join(script_dir, "amap_data.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n✅ 所有数据已保存到: {output_path}")
print(f"   文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
