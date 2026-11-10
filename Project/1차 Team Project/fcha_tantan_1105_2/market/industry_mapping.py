"""Project preview correspondence; never an official classification verification."""
from django.db.models import Q

SYSTEM = 'local-sbiz-small-20261103'
CATEGORY_CODES = {
    "카페": [
        "I21201"
    ],
    "아이스크림/빙수": [
        "I21008"
    ],
    "제과제빵": [
        "I21001",
        "I21002"
    ],
    "한식": [
        "I20101",
        "I20102",
        "I20103",
        "I20104",
        "I20105",
        "I20106",
        "I20107",
        "I20108",
        "I20109",
        "I20110",
        "I20111",
        "I20112",
        "I20113",
        "I20199"
    ],
    "중식": [
        "I20201",
        "I20202"
    ],
    "일식": [
        "I20301",
        "I20302",
        "I20303",
        "I20399"
    ],
    "서양식": [
        "I20401",
        "I20402",
        "I20403",
        "I20499"
    ],
    "기타 외국식": [
        "I20501",
        "I20599",
        "I20601"
    ],
    "주점": [
        "I21101",
        "I21102",
        "I21103",
        "I21104"
    ],
    "치킨": [
        "I21006"
    ],
    "피자": [
        "I21003"
    ],
    "분식": [
        "I21007"
    ],
    "패스트푸드": [
        "I21004",
        "I21005"
    ],
    "편의점": [
        "G20405"
    ],
    "화장품": [
        "G21503"
    ],
    "미용실": [
        "S20701"
    ],
    "교육 (교과)": [
        "P10501"
    ],
    "교육 (외국어)": [
        "P10615"
    ],
    "PC방": [
        "R10406"
    ],
    "세탁": [
        "S20901",
        "S20902"
    ],
    "안경": [
        "G21602"
    ],
    "약국": [
        "G21501"
    ],
    "부동산 중개": [
        "L10203"
    ]
}


def category_filter(category):
    category = category.strip()
    if category in ('', '전체'):
        return Q(), 'all'
    codes = CATEGORY_CODES.get(category, [])
    # Explicit reviewed DB mappings can extend the preview correspondence.
    predicate = Q(industry__brand_category=category, industry__verified=True)
    if codes:
        predicate |= Q(industry__system=SYSTEM, industry__code__in=codes)
    return predicate, 'preview' if codes else 'unmapped'
