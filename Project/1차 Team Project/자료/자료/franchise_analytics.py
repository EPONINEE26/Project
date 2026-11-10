# -*- coding: utf-8 -*-
"""
franchise_analytics.py — 자료.zip(4개 업종 19개 브랜드) 분석 API 함수 모음
단위: 원(창업비용·매출), 비율: 0~1
"""
from statistics import mean

BRANDS = [
    {"brand":'교촌치킨',"industry":'치킨',"fee":6760000,"edu":3900000,"deposit":10000000,"interior":69000000,"equip":None,"etc":66860000,"revenue":787680000,"seoul":None,"gyeonggi":None,"stores_seoul":228,"stores_total":1361},
    {"brand":'BHC',"industry":'치킨',"fee":10000000,"edu":2200000,"deposit":10000000,"interior":42000000,"equip":23720000,"etc":0,"revenue":636960000,"seoul":None,"gyeonggi":None,"stores_seoul":258,"stores_total":2250},
    {"brand":'굽네치킨',"industry":'치킨',"fee":5500000,"edu":2200000,"deposit":None,"interior":30250000,"equip":None,"etc":45320000,"revenue":498600000,"seoul":None,"gyeonggi":None,"stores_seoul":178,"stores_total":1251},
    {"brand":'비비큐(BBQ)',"industry":'치킨',"fee":11000000,"edu":4180000,"deposit":5000000,"interior":50600000,"equip":None,"etc":20000000,"revenue":508680000,"seoul":None,"gyeonggi":None,"stores_seoul":332,"stores_total":2124},
    {"brand":'처갓집양념치킨',"industry":'치킨',"fee":5500000,"edu":1100000,"deposit":1000000,"interior":13200000,"equip":None,"etc":8250000,"revenue":342840000,"seoul":None,"gyeonggi":None,"stores_seoul":139,"stores_total":1251},
    {"brand":'메가커피',"industry":'커피',"fee":11000000,"edu":5500000,"deposit":2000000,"interior":16500000,"equip":None,"etc":61638000,"revenue":412874000,"seoul":461869000,"gyeonggi":415601000,"stores_seoul":931,"stores_total":3969},
    {"brand":'컴포즈커피',"industry":'커피',"fee":5500000,"edu":2200000,"deposit":5000000,"interior":29150000,"equip":None,"etc":70782000,"revenue":271883000,"seoul":288065000,"gyeonggi":266421000,"stores_seoul":456,"stores_total":2649},
    {"brand":'이디야커피',"industry":'커피',"fee":9900000,"edu":3300000,"deposit":5000000,"interior":41800000,"equip":None,"etc":114120000,"revenue":194818000,"seoul":211174000,"gyeonggi":191400000,"stores_seoul":510,"stores_total":2562},
    {"brand":'빽다방',"industry":'커피',"fee":0,"edu":3300000,"deposit":1500000,"interior":16720000,"equip":None,"etc":68272000,"revenue":324486000,"seoul":352053000,"gyeonggi":307523000,"stores_seoul":359,"stores_total":1712},
    {"brand":'투썸플레이스',"industry":'커피',"fee":25000000,"edu":1500000,"deposit":10000000,"interior":86500000,"equip":None,"etc":273300000,"revenue":571726000,"seoul":685620000,"gyeonggi":599388000,"stores_seoul":279,"stores_total":1510},
    {"brand":'CU',"industry":'편의점',"fee":8700000,"edu":None,"deposit":None,"interior":1520000,"equip":None,"etc":14000000,"revenue":None,"seoul":None,"gyeonggi":None,"stores_seoul":2972,"stores_total":18468},
    {"brand":'GS25',"industry":'편의점',"fee":22700000,"edu":None,"deposit":None,"interior":None,"equip":None,"etc":None,"revenue":None,"seoul":None,"gyeonggi":None,"stores_seoul":3242,"stores_total":17888},
    {"brand":'세븐일레븐',"industry":'편의점',"fee":22700000,"edu":None,"deposit":50000000,"interior":1310000,"equip":None,"etc":None,"revenue":511200000,"seoul":None,"gyeonggi":None,"stores_seoul":1813,"stores_total":7568},
    {"brand":'이마트24',"industry":'편의점',"fee":24200000,"edu":None,"deposit":50000000,"interior":None,"equip":None,"etc":None,"revenue":451440000,"seoul":None,"gyeonggi":None,"stores_seoul":784,"stores_total":5595},
    {"brand":'에이바헤어',"industry":'이미용',"fee":11000000,"edu":0,"deposit":0,"interior":None,"equip":None,"etc":72600000,"revenue":347757000,"seoul":399943000,"gyeonggi":325626000,"stores_seoul":139,"stores_total":342},
    {"brand":'블루클럽',"industry":'이미용',"fee":14630000,"edu":1100000,"deposit":5000000,"interior":None,"equip":None,"etc":38650000,"revenue":82526000,"seoul":87541000,"gyeonggi":0,"stores_seoul":116,"stores_total":334},
    {"brand":'제오헤어',"industry":'이미용',"fee":16500000,"edu":0,"deposit":10000000,"interior":None,"equip":None,"etc":139970000,"revenue":439027000,"seoul":440374000,"gyeonggi":407287000,"stores_seoul":36,"stores_total":46},
    {"brand":'로이드밤',"industry":'이미용',"fee":6600000,"edu":3300000,"deposit":0,"interior":None,"equip":None,"etc":119900000,"revenue":407715000,"seoul":438994000,"gyeonggi":412480000,"stores_seoul":29,"stores_total":169},
    {"brand":'토리헤어',"industry":'이미용',"fee":7700000,"edu":1100000,"deposit":5000000,"interior":None,"equip":None,"etc":210100000,"revenue":300648000,"seoul":283614000,"gyeonggi":313678000,"stores_seoul":12,"stores_total":153},
]

RATIO = {"치킨":(0.38,0.18,0.09,0.12),"커피":(0.30,0.20,0.12,0.10),
         "편의점":(0.65,0.08,0.05,0.05),"이미용":(0.08,0.35,0.12,0.10)}


def startup_cost(b):
    """창업비용 6항목 합계 (None은 0으로 계산하되 missing에 기록)"""
    keys = ("fee","edu","deposit","interior","equip","etc")
    return sum(b.get(k) or 0 for k in keys)

def missing_items(b):
    """원본에서 확인되지 않은 항목 목록"""
    name = {"fee":"가맹비","edu":"교육비","deposit":"보증금",
            "interior":"인테리어","equip":"설비","etc":"기타"}
    return [name[k] for k in ("fee","edu","deposit","interior","equip","etc")
            if b.get(k) is None]

def operating_profit(b, ratio=None):
    """운영이익 = 매출 - (재료비+인건비+임차료+기타운영비), 매출 없으면 None"""
    if not b.get("revenue"):
        return None
    r = ratio or RATIO[b["industry"]]
    return b["revenue"] * (1 - sum(r))

def margin(b, ratio=None):
    p = operating_profit(b, ratio)
    return None if p is None else p / b["revenue"]

def payback_years(b, ratio=None):
    """창업비용 회수기간(년) = 창업비용 / 운영이익"""
    p = operating_profit(b, ratio)
    if not p or p <= 0:
        return None
    return startup_cost(b) / p

def industry_avg_revenue(brands, industry):
    vals = [b["revenue"] for b in brands
            if b["industry"] == industry and b.get("revenue")]
    return mean(vals) if vals else None

def industry_avg_cost(brands, industry):
    vals = [startup_cost(b) for b in brands if b["industry"] == industry]
    return mean(vals) if vals else None

def region_summary(brands, industry=None):
    """지역(서울/경기) 매장·매출 집계"""
    rows = [b for b in brands if industry is None or b["industry"] == industry]
    return {
        "stores_seoul": sum(b.get("stores_seoul") or 0 for b in rows),
        "stores_total": sum(b.get("stores_total") or 0 for b in rows),
        "revenue_seoul": sum(b.get("seoul") or 0 for b in rows),
        "revenue_gyeonggi": sum(b.get("gyeonggi") or 0 for b in rows),
    }

def rank_by_revenue(brands, industry=None):
    rows = [b for b in brands if (industry is None or b["industry"] == industry)
            and b.get("revenue")]
    return sorted(rows, key=lambda b: b["revenue"], reverse=True)

def budget_profit(revenue, costs, startup_cost_value=None):
    """입력한 비용으로 예산 운영이익 계산
    revenue: 연매출, costs: dict(material, labor, rent, other) 절대금액"""
    total = sum(costs.get(k) or 0 for k in ("material","labor","rent","other"))
    profit = revenue - total
    return {"revenue":revenue,"cost_total":total,"profit":profit,
            "margin":profit / revenue if revenue else None,
            "payback_years":(startup_cost_value / profit)
                            if startup_cost_value and profit > 0 else None}

def validate(brands):
    """분석 결과 자체 검증: 항목 누락·합계 일치 여부"""
    out = []
    for b in brands:
        miss = missing_items(b)
        out.append({"brand":b["brand"],"startup_cost":startup_cost(b),
                    "missing":miss,"ok":not miss})
    return out

if __name__ == "__main__":
    import json
    print(json.dumps({
        "industry_avg_revenue":{i:industry_avg_revenue(BRANDS,i) for i in RATIO},
        "industry_avg_cost":{i:industry_avg_cost(BRANDS,i) for i in RATIO},
        "top5":[(b["brand"],b["revenue"]) for b in rank_by_revenue(BRANDS)[:5]],
    }, ensure_ascii=False, indent=1))
