import pandas as pd
import json
import re
import numpy as np
from pathlib import Path


# ============================================================
# 0. 기본 설정
# ============================================================

TARGET_NAME = "예술스포츠여가서비스업"

SHOP_FILE = Path(
    r"C:\workspace\fcha_data\data\전국상가정보_예술스포츠여가서비스업_202610\records.csv"
)

# 공정위 브랜드 기본정보 2024 / 2025 / 2026
BRAND_FILES = [
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2024\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2025\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2026\records.csv"),
]

REGION_FILE = Path(
    r"C:\workspace\fcha_data\data\브랜드지역현황_v5\processed\brand_region_raw.json"
)

OUTPUT_DIR = Path(
    r"C:\workspace\fcha_data\output\franchise_matching"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / f"{TARGET_NAME}_프랜차이즈_최종매칭_v2.xlsx"
)


# ============================================================
# 1. 공정위 업종 필터
# ============================================================

TARGET_MAJOR_INDUSTRY = "서비스"

TARGET_MIDDLE_INDUSTRIES = [
    "스포츠 관련",
    "오락",
    "PC방",
    "기타 서비스",
    "유아 관련 (교육 외)",
    "기타 교육",
    "임대",
]


# ============================================================
# 2. 문자열 정리 함수
# ============================================================

def clean_name(name):

    if pd.isna(name):
        return ""

    name = str(name).strip().upper()

    name = re.sub(
        r"\s+",
        "",
        name
    )

    name = re.sub(
        r"[^가-힣A-Z0-9]",
        "",
        name
    )

    return name


# ============================================================
# 3. 지역명 정규화
# ============================================================

REGION_MAP = {

    "서울특별시": "서울",
    "서울": "서울",

    "부산광역시": "부산",
    "부산": "부산",

    "대구광역시": "대구",
    "대구": "대구",

    "인천광역시": "인천",
    "인천": "인천",

    "광주광역시": "광주",
    "광주": "광주",

    "대전광역시": "대전",
    "대전": "대전",

    "울산광역시": "울산",
    "울산": "울산",

    "세종특별자치시": "세종",
    "세종": "세종",

    "경기도": "경기",
    "경기": "경기",

    "강원특별자치도": "강원",
    "강원도": "강원",
    "강원": "강원",

    "충청북도": "충북",
    "충북": "충북",

    "충청남도": "충남",
    "충남": "충남",

    "전북특별자치도": "전북",
    "전라북도": "전북",
    "전북": "전북",

    "전라남도": "전남",
    "전남": "전남",

    "경상북도": "경북",
    "경북": "경북",

    "경상남도": "경남",
    "경남": "경남",

    "제주특별자치도": "제주",
    "제주": "제주",
}


def normalize_region(region):

    if pd.isna(region):
        return None

    region = str(region).strip()

    # 2026 행정구역
    if region == "전남광주통합특별시":
        return "전남광주통합"

    return REGION_MAP.get(
        region,
        region
    )


# ============================================================
# 4. 전국상가정보 읽기
# ============================================================

print()
print("========================================")
print("1. 전국상가정보 읽기")
print("========================================")

shop_df = pd.read_csv(
    SHOP_FILE,
    encoding="utf-8"
)


shop_cols = [
    "bizesId",
    "bizesNm",
    "brchNm",

    "indsLclsCd",
    "indsLclsNm",

    "indsMclsCd",
    "indsMclsNm",

    "indsSclsCd",
    "indsSclsNm",

    "ctprvnCd",
    "ctprvnNm",

    "signguCd",
    "signguNm",

    "rdnmAdr",

    "lon",
    "lat"
]


shop_df = (
    shop_df[
        shop_cols
    ]
    .copy()
)


shop_df[
    "cleaned_store_name"
] = (
    shop_df[
        "bizesNm"
    ]
    .apply(
        clean_name
    )
)


shop_df[
    "normalized_region"
] = (
    shop_df[
        "ctprvnNm"
    ]
    .apply(
        normalize_region
    )
)


print(
    "전체 상가 :",
    len(shop_df)
)


# ============================================================
# 5. 공정위 브랜드 기본정보 읽기
# ============================================================

print()
print("========================================")
print("2. 공정위 브랜드 기본정보 읽기")
print("========================================")

brand_list = []


for file in BRAND_FILES:

    temp = pd.read_csv(
        file,
        encoding="utf-8"
    )

    print(
        file,
        ":",
        len(temp),
        "건"
    )

    brand_list.append(
        temp
    )


brand_df = pd.concat(
    brand_list,
    ignore_index=True
)


brand_df = brand_df[
    [
        "jngBizCrtraYr",
        "brandMnno",
        "brandNm",
        "indutyLclasNm",
        "indutyMlsfcNm",
        "corpNm"
    ]
].copy()


brand_df = brand_df[
    brand_df[
        "brandNm"
    ].notna()
].copy()


brand_df[
    "cleaned_brand_name"
] = (
    brand_df[
        "brandNm"
    ]
    .apply(
        clean_name
    )
)


brand_df[
    "brand_name_length"
] = (
    brand_df[
        "cleaned_brand_name"
    ]
    .str.len()
)


# ============================================================
# 6. 대상 공정위 브랜드 필터링
# ============================================================

target_brand_df = (
    brand_df[
        (
            brand_df[
                "indutyLclasNm"
            ]
            == TARGET_MAJOR_INDUSTRY
        )
        &
        (
            brand_df[
                "indutyMlsfcNm"
            ]
            .isin(
                TARGET_MIDDLE_INDUSTRIES
            )
        )
    ]
    .copy()
)


# 브랜드별 최신 정보 사용
target_brand_df = (
    target_brand_df
    .sort_values(
        "jngBizCrtraYr",
        ascending=False
    )
    .drop_duplicates(
        subset=[
            "brandMnno"
        ],
        keep="first"
    )
    .reset_index(
        drop=True
    )
)


print()
print(
    "공식 브랜드 후보 :",
    len(target_brand_df)
)


print()
print("중분류별 공식 브랜드 수")

print(
    target_brand_df[
        "indutyMlsfcNm"
    ]
    .value_counts()
)


# ============================================================
# 7. 정확 일치 사전 생성
# ============================================================

exact_map = {}


for _, row in target_brand_df.iterrows():

    cleaned = row[
        "cleaned_brand_name"
    ]

    if cleaned == "":
        continue

    if cleaned not in exact_map:

        exact_map[
            cleaned
        ] = []

    exact_map[
        cleaned
    ].append(
        {
            "brandMnno":
            row["brandMnno"],

            "brandNm":
            row["brandNm"],

            "corpNm":
            row["corpNm"],

            "indutyMlsfcNm":
            row["indutyMlsfcNm"]
        }
    )


# ============================================================
# 8. 정확 일치
# ============================================================

def exact_match(name):

    matches = exact_map.get(
        name
    )

    if matches is None:

        return pd.Series(
            [
                None,
                None,
                None,
                None,
                None,
                None
            ]
        )


    if len(matches) == 1:

        m = matches[0]

        return pd.Series(
            [
                m["brandMnno"],
                m["brandNm"],
                m["corpNm"],
                m["indutyMlsfcNm"],
                "exact",
                "HIGH"
            ]
        )


    return pd.Series(
        [
            None,
            None,
            None,
            None,
            "duplicate_brand_name",
            "REVIEW"
        ]
    )


shop_df[
    [
        "brandMnno",
        "matched_brandNm",
        "matched_corpNm",
        "matched_brand_industry",
        "match_type",
        "match_confidence"
    ]
] = (
    shop_df[
        "cleaned_store_name"
    ]
    .apply(
        exact_match
    )
)


print()
print(
    "정확 일치 :",
    (
        shop_df[
            "match_type"
        ]
        == "exact"
    ).sum()
)


# ============================================================
# 9. 포함 검색 준비
# ============================================================

contains_brand_df = (
    target_brand_df[
        target_brand_df[
            "brand_name_length"
        ] >= 3
    ]
    .copy()
)


brand_name_counts = (
    contains_brand_df[
        "cleaned_brand_name"
    ]
    .value_counts()
)


duplicate_names = set(
    brand_name_counts[
        brand_name_counts > 1
    ].index
)


brand_names = (
    contains_brand_df[
        "cleaned_brand_name"
    ]
    .dropna()
    .drop_duplicates()
    .tolist()
)


brand_names = sorted(
    brand_names,
    key=len,
    reverse=True
)


pattern = (
    "("
    +
    "|".join(
        re.escape(name)
        for name in brand_names
        if name
    )
    +
    ")"
)


# ============================================================
# 10. 포함 검색
# ============================================================

print()
print("========================================")
print("3. 포함 검색")
print("========================================")


no_match_mask = (
    shop_df[
        "match_type"
    ].isna()
)


extracted = (
    shop_df.loc[
        no_match_mask,
        "cleaned_store_name"
    ]
    .str.extract(
        pattern,
        expand=False
    )
)


brand_lookup = {}


for _, row in contains_brand_df.iterrows():

    cleaned = row[
        "cleaned_brand_name"
    ]

    if cleaned in duplicate_names:
        continue

    brand_lookup[
        cleaned
    ] = {
        "brandMnno":
        row["brandMnno"],

        "brandNm":
        row["brandNm"],

        "corpNm":
        row["corpNm"],

        "indutyMlsfcNm":
        row["indutyMlsfcNm"]
    }


for index, cleaned_brand in extracted.items():

    if pd.isna(
        cleaned_brand
    ):
        continue


    if cleaned_brand in duplicate_names:

        shop_df.at[
            index,
            "match_type"
        ] = "duplicate_brand_name"

        shop_df.at[
            index,
            "match_confidence"
        ] = "REVIEW"

        continue


    info = brand_lookup.get(
        cleaned_brand
    )


    if info is None:
        continue


    shop_df.at[
        index,
        "brandMnno"
    ] = info[
        "brandMnno"
    ]

    shop_df.at[
        index,
        "matched_brandNm"
    ] = info[
        "brandNm"
    ]

    shop_df.at[
        index,
        "matched_corpNm"
    ] = info[
        "corpNm"
    ]

    shop_df.at[
        index,
        "matched_brand_industry"
    ] = info[
        "indutyMlsfcNm"
    ]

    shop_df.at[
        index,
        "match_type"
    ] = "contains"

    shop_df.at[
        index,
        "match_confidence"
    ] = "MEDIUM"


print(
    "포함 일치 :",
    (
        shop_df[
            "match_type"
        ]
        == "contains"
    ).sum()
)


# ============================================================
# 11. 이름 매칭 상태 생성
# ============================================================

status_map = {

    "HIGH":
    "자동확정",

    "MEDIUM":
    "프랜차이즈후보",

    "REVIEW":
    "검토필요"
}


shop_df[
    "match_status"
] = (
    shop_df[
        "match_confidence"
    ]
    .map(
        status_map
    )
    .fillna(
        "미매칭"
    )
)


# ============================================================
# 12. 브랜드 지역현황 읽기
# ============================================================

print()
print("========================================")
print("4. 브랜드 지역현황 읽기")
print("========================================")


with open(
    REGION_FILE,
    "r",
    encoding="utf-8"
) as f:

    region_df = pd.DataFrame(
        json.load(f)
    )


for col in [
    "frcsCnt",
    "dmsCnt",
    "allFrcsDmsCnt"
]:

    region_df[
        col
    ] = pd.to_numeric(
        region_df[
            col
        ],
        errors="coerce"
    )


region_df[
    "jngBizCrtraYr_num"
] = pd.to_numeric(
    region_df[
        "jngBizCrtraYr"
    ],
    errors="coerce"
)


region_df[
    "acntgYr_num"
] = pd.to_numeric(
    region_df[
        "acntgYr"
    ],
    errors="coerce"
)


# ============================================================
# 13. 브랜드별 최신 지역현황 선택
# ============================================================

latest_year_per_brand = (
    region_df
    .groupby(
        "brandMnno"
    )[
        "jngBizCrtraYr_num"
    ]
    .max()
    .reset_index()
    .rename(
        columns={
            "jngBizCrtraYr_num":
            "selected_year"
        }
    )
)


latest_region_df = (
    region_df
    .merge(
        latest_year_per_brand,
        on="brandMnno",
        how="inner"
    )
)


latest_region_df = (
    latest_region_df[
        latest_region_df[
            "jngBizCrtraYr_num"
        ]
        ==
        latest_region_df[
            "selected_year"
        ]
    ]
    .copy()
)


def year_source(year):

    if year == 2026:
        return "2026최신"

    if year == 2025:
        return "2026없음_2025사용"

    if year == 2024:
        return "2026_2025없음_2024사용"

    return "기타연도"


latest_region_df[
    "region_year_source"
] = (
    latest_region_df[
        "selected_year"
    ]
    .apply(
        year_source
    )
)


latest_region_df[
    "normalized_region"
] = (
    latest_region_df[
        "areaNm"
    ]
)


# ============================================================
# 14. 전국 / 지역 분리
# ============================================================

national_region_df = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ] == "전체"
    ]
    .copy()
)


regional_df = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ] != "전체"
    ]
    .copy()
)


# ============================================================
# 15. 공식 지역 데이터 정리
# ============================================================

official_region = (
    regional_df[
        [
            "brandMnno",

            "jngBizCrtraYr",
            "acntgYr",

            "selected_year",
            "region_year_source",

            "normalized_region",

            "frcsCnt",
            "dmsCnt",
            "allFrcsDmsCnt"
        ]
    ]
    .copy()
)


official_region = (
    official_region
    .rename(
        columns={

            "frcsCnt":
            "official_franchise_count",

            "dmsCnt":
            "official_direct_count",

            "allFrcsDmsCnt":
            "official_total_count"

        }
    )
)


# ============================================================
# 16. 전남 + 광주 통합 비교값
# ============================================================

south_gwangju = (
    official_region[
        official_region[
            "normalized_region"
        ]
        .isin(
            [
                "광주",
                "전남"
            ]
        )
    ]
    .groupby(
        [
            "brandMnno",

            "jngBizCrtraYr",
            "acntgYr",

            "selected_year",
            "region_year_source"
        ],
        dropna=False
    )
    .agg(

        official_franchise_count=(
            "official_franchise_count",
            lambda x:
            x.sum(
                min_count=1
            )
        ),

        official_direct_count=(
            "official_direct_count",
            lambda x:
            x.sum(
                min_count=1
            )
        ),

        official_total_count=(
            "official_total_count",
            lambda x:
            x.sum(
                min_count=1
            )
        )
    )
    .reset_index()
)


south_gwangju[
    "normalized_region"
] = "전남광주통합"


official_region = (
    pd.concat(
        [
            official_region,
            south_gwangju
        ],
        ignore_index=True
    )
)


# ============================================================
# 17. 브랜드 매칭된 상가 추출
# ============================================================

matched_df = (
    shop_df[
        shop_df[
            "brandMnno"
        ].notna()
    ]
    .copy()
)


print(
    "브랜드 매칭 상가 :",
    len(matched_df)
)


# ============================================================
# 18. 브랜드 + 지역별 상가 수
# ============================================================

shop_region_count = (
    matched_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm",
            "normalized_region"
        ],
        dropna=False
    )
    .agg(

        shop_store_count=(
            "bizesId",
            "count"
        ),

        exact_count=(
            "match_type",
            lambda x:
            (x == "exact").sum()
        ),

        contains_count=(
            "match_type",
            lambda x:
            (x == "contains").sum()
        )
    )
    .reset_index()
)


# ============================================================
# 19. 지역현황 연결
# ============================================================

validation_df = (
    shop_region_count
    .merge(

        official_region,

        on=[
            "brandMnno",
            "normalized_region"
        ],

        how="left"
    )
)


# ============================================================
# 20. 지역 비교 차이 / 비율 계산
# ============================================================

validation_df[
    "count_difference"
] = (
    validation_df[
        "shop_store_count"
    ]
    -
    validation_df[
        "official_total_count"
    ]
)


validation_df[
    "abs_difference"
] = (
    validation_df[
        "count_difference"
    ]
    .abs()
)


validation_df[
    "shop_official_ratio"
] = np.where(

    validation_df[
        "official_total_count"
    ] > 0,

    (
        validation_df[
            "shop_store_count"
        ]
        /
        validation_df[
            "official_total_count"
        ]
    ),

    np.nan
)


# ============================================================
# 21. 지역 검증 판정
# ============================================================

def region_validation(row):

    shop_count = row[
        "shop_store_count"
    ]

    official = row[
        "official_total_count"
    ]

    ratio = row[
        "shop_official_ratio"
    ]


    if pd.isna(
        official
    ):
        return "공식지역정보없음"


    if official == 0:

        if shop_count == 0:
            return "일치"

        if shop_count <= 2:
            return "신규가능성"

        if shop_count <= 5:
            return "검토필요"

        return "강한검토필요"


    if pd.isna(
        ratio
    ):
        return "검토필요"


    if (
        0.5
        <= ratio
        <= 1.5
    ):
        return "양호"


    if (
        0.2
        <= ratio
        <= 2.0
    ):
        return "유력"


    if ratio > 2.0:
        return "과다매칭검토"


    return "누락가능성"


validation_df[
    "region_validation"
] = (
    validation_df
    .apply(
        region_validation,
        axis=1
    )
)


# ============================================================
# 22. 지역 점수
# ============================================================

REGION_SCORE_MAP = {

    "일치": 3,
    "양호": 3,
    "유력": 2,
    "신규가능성": 1,
    "누락가능성": 1,

    "공식지역정보없음": 0,
    "검토필요": 0,

    "과다매칭검토": -2,
    "강한검토필요": -3,
}


validation_df[
    "region_score"
] = (
    validation_df[
        "region_validation"
    ]
    .map(
        REGION_SCORE_MAP
    )
    .fillna(0)
)


# ============================================================
# 23. 브랜드 단위 지역검증 요약
# ============================================================

brand_validation_df = (
    validation_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm"
        ],
        dropna=False
    )
    .agg(

        matched_store_count=(
            "shop_store_count",
            "sum"
        ),

        matched_region_count=(
            "normalized_region",
            "nunique"
        ),

        good_region_count=(
            "region_validation",
            lambda x:
            x.isin(
                [
                    "일치",
                    "양호",
                    "유력"
                ]
            ).sum()
        ),

        new_possible_count=(
            "region_validation",
            lambda x:
            (
                x
                == "신규가능성"
            ).sum()
        ),

        missing_possible_count=(
            "region_validation",
            lambda x:
            (
                x
                == "누락가능성"
            ).sum()
        ),

        review_region_count=(
            "region_validation",
            lambda x:
            x.isin(
                [
                    "검토필요",
                    "과다매칭검토",
                    "강한검토필요"
                ]
            ).sum()
        ),

        no_official_info_count=(
            "region_validation",
            lambda x:
            (
                x
                == "공식지역정보없음"
            ).sum()
        ),

        region_score_sum=(
            "region_score",
            "sum"
        )

    )
    .reset_index()
)


# ============================================================
# 24. 브랜드 검증 상태
# ============================================================

def brand_region_status(row):

    good = row[
        "good_region_count"
    ]

    new_possible = row[
        "new_possible_count"
    ]

    review = row[
        "review_region_count"
    ]

    no_info = row[
        "no_official_info_count"
    ]

    score = row[
        "region_score_sum"
    ]


    if (
        good >= 3
        and
        review == 0
        and
        score >= 6
    ):
        return "지역검증우수"


    if (
        good >= 1
        and
        score > 0
        and
        review == 0
    ):
        return "지역검증유력"


    if review >= 1:
        return "지역검토필요"


    if (
        no_info > 0
        and
        good == 0
    ):
        return "공식정보부족"


    if new_possible > 0:
        return "신규가능성포함"


    return "정보부족"


brand_validation_df[
    "brand_region_status"
] = (
    brand_validation_df
    .apply(
        brand_region_status,
        axis=1
    )
)


# ============================================================
# 25. 전국 단위 비교
# ============================================================

national_official_df = (
    national_region_df[
        [
            "brandMnno",

            "selected_year",
            "acntgYr",
            "region_year_source",

            "frcsCnt",
            "dmsCnt",
            "allFrcsDmsCnt"
        ]
    ]
    .copy()
)


national_official_df = (
    national_official_df
    .rename(
        columns={

            "frcsCnt":
            "national_official_franchise",

            "dmsCnt":
            "national_official_direct",

            "allFrcsDmsCnt":
            "national_official_total"

        }
    )
)


national_shop_df = (
    matched_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm"
        ]
    )
    .size()
    .reset_index(
        name="national_shop_count"
    )
)


national_compare_df = (
    national_shop_df
    .merge(
        national_official_df,
        on="brandMnno",
        how="left"
    )
)


national_compare_df[
    "national_difference"
] = (
    national_compare_df[
        "national_shop_count"
    ]
    -
    national_compare_df[
        "national_official_total"
    ]
)


national_compare_df[
    "national_ratio"
] = np.where(

    national_compare_df[
        "national_official_total"
    ] > 0,

    (
        national_compare_df[
            "national_shop_count"
        ]
        /
        national_compare_df[
            "national_official_total"
        ]
    ),

    np.nan
)


# ============================================================
# 26. 개별 상가에 브랜드 지역상태 붙이기
# ============================================================

shop_df = (
    shop_df
    .merge(

        brand_validation_df[
            [
                "brandMnno",
                "brand_region_status",
                "region_score_sum",
                "good_region_count",
                "new_possible_count",
                "review_region_count",
                "no_official_info_count"
            ]
        ],

        on="brandMnno",

        how="left"
    )
)


# ============================================================
# 27. 최종 판정
# ============================================================

def final_status(row):

    name_status = row[
        "match_status"
    ]

    region_status = row[
        "brand_region_status"
    ]


    # 이름 정확일치
    if name_status == "자동확정":

        if region_status == "지역검증우수":
            return "확정"

        if region_status == "지역검증유력":
            return "확정유력"

        if region_status == "신규가능성포함":
            return "확정유력"

        if region_status == "지역검토필요":
            return "검토필요"

        if region_status == "공식정보부족":
            return "공식정보부족"


    # 이름 포함일치
    if name_status == "프랜차이즈후보":

        if region_status == "지역검증우수":
            return "유력"

        if region_status == "지역검증유력":
            return "유력"

        if region_status == "신규가능성포함":
            return "후보"

        if region_status == "지역검토필요":
            return "검토필요"

        if region_status == "공식정보부족":
            return "공식정보부족"


    # 2차에서부터 검토
    if name_status == "검토필요":
        return "검토필요"


    return "정보부족"


shop_df[
    "final_match_status"
] = (
    shop_df
    .apply(
        final_status,
        axis=1
    )
)


# ============================================================
# 28. 최종 점수
# ============================================================

FINAL_SCORE_MAP = {

    "확정": 5,

    "확정유력": 4,

    "유력": 3,

    "후보": 2,

    "검토필요": 1,

    "공식정보부족": 0,

    "정보부족": 0,
}


shop_df[
    "final_score"
] = (
    shop_df[
        "final_match_status"
    ]
    .map(
        FINAL_SCORE_MAP
    )
    .fillna(0)
)


# ============================================================
# 29. 결과 분리
# ============================================================

confirmed_df = (
    shop_df[
        shop_df[
            "final_match_status"
        ]
        .isin(
            [
                "확정",
                "확정유력"
            ]
        )
    ]
    .copy()
)


likely_df = (
    shop_df[
        shop_df[
            "final_match_status"
        ]
        .isin(
            [
                "유력",
                "후보"
            ]
        )
    ]
    .copy()
)


review_df = (
    shop_df[
        shop_df[
            "final_match_status"
        ]
        == "검토필요"
    ]
    .copy()
)


no_info_df = (
    shop_df[
        shop_df[
            "final_match_status"
        ]
        == "공식정보부족"
    ]
    .copy()
)


# ============================================================
# 30. 프로젝트 우선 활용 데이터
# ============================================================

project_ready_df = (
    shop_df[
        shop_df[
            "final_match_status"
        ]
        .isin(
            [
                "확정",
                "확정유력",
                "유력"
            ]
        )
    ]
    .copy()
)


# ============================================================
# 31. 분석 요약
# ============================================================

summary_df = pd.DataFrame(
    {

        "항목": [

            "전체 상가",

            "공식 브랜드 후보",

            "브랜드 매칭",

            "확정",

            "확정유력",

            "유력",

            "후보",

            "검토필요",

            "공식정보부족",

            "정보부족",

            "프로젝트 우선 활용 가능",

            "지역검증 브랜드 수"
        ],

        "건수": [

            len(
                shop_df
            ),

            len(
                target_brand_df
            ),

            shop_df[
                "brandMnno"
            ]
            .notna()
            .sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "확정"
            ).sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "확정유력"
            ).sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "유력"
            ).sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "후보"
            ).sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "검토필요"
            ).sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "공식정보부족"
            ).sum(),

            (
                shop_df[
                    "final_match_status"
                ]
                == "정보부족"
            ).sum(),

            len(
                project_ready_df
            ),

            len(
                brand_validation_df
            )
        ]
    }
)


# ============================================================
# 32. 콘솔 출력
# ============================================================

print()
print("========================================")
print("5. 최종 결과")
print("========================================")

print(
    summary_df.to_string(
        index=False
    )
)


print()
print("========================================")
print("지역 검증 상태")
print("========================================")

print(
    validation_df[
        "region_validation"
    ]
    .value_counts(
        dropna=False
    )
)


print()
print("========================================")
print("브랜드 지역 검증 상태")
print("========================================")

print(
    brand_validation_df[
        "brand_region_status"
    ]
    .value_counts(
        dropna=False
    )
)


# ============================================================
# 33. 엑셀 저장
# ============================================================

print()
print("========================================")
print("6. 엑셀 저장")
print("========================================")


with pd.ExcelWriter(
    OUTPUT_FILE,
    engine="openpyxl"
) as writer:


    summary_df.to_excel(
        writer,
        sheet_name="분석요약",
        index=False
    )


    target_brand_df.to_excel(
        writer,
        sheet_name="공식브랜드후보",
        index=False
    )


    shop_df.to_excel(
        writer,
        sheet_name="전체매칭결과",
        index=False
    )


    validation_df.to_excel(
        writer,
        sheet_name="지역별검증",
        index=False
    )


    brand_validation_df.to_excel(
        writer,
        sheet_name="브랜드지역요약",
        index=False
    )


    national_compare_df.to_excel(
        writer,
        sheet_name="전국비교",
        index=False
    )


    confirmed_df.to_excel(
        writer,
        sheet_name="확정데이터",
        index=False
    )


    likely_df.to_excel(
        writer,
        sheet_name="유력후보",
        index=False
    )


    review_df.to_excel(
        writer,
        sheet_name="검토필요",
        index=False
    )


    no_info_df.to_excel(
        writer,
        sheet_name="공식정보부족",
        index=False
    )


    project_ready_df.to_excel(
        writer,
        sheet_name="프로젝트활용후보",
        index=False
    )


print()
print("========================================")
print("저장 완료")
print("========================================")

print(
    OUTPUT_FILE
)