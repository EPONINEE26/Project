import pandas as pd
import json
import re
import numpy as np
from pathlib import Path


# ============================================================
# 0. 이번 실행에서 수정하는 설정값
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
    OUTPUT_DIR /
    f"{TARGET_NAME}_프랜차이즈_최종매칭.xlsx"
)


# ============================================================
# 1. 공정위에서 사용할 업종
# ============================================================
#
# 처음에는 넓게 서비스업 전체를 후보로 가져온다.
# 이후 실제 결과를 보고 중분류를 좁힌다.
# ============================================================

TARGET_MAJOR_INDUSTRY = "서비스"

TARGET_MIDDLE_INDUSTRIES = None


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
# 3. 지역명 정리
# ============================================================

REGION_MAP = {

    "서울특별시": "서울",
    "부산광역시": "부산",
    "대구광역시": "대구",
    "인천광역시": "인천",
    "광주광역시": "광주",
    "대전광역시": "대전",
    "울산광역시": "울산",
    "세종특별자치시": "세종",

    "경기도": "경기",

    "강원특별자치도": "강원",
    "강원도": "강원",

    "충청북도": "충북",
    "충청남도": "충남",

    "전북특별자치도": "전북",
    "전라북도": "전북",

    "전라남도": "전남",

    "경상북도": "경북",
    "경상남도": "경남",

    "제주특별자치도": "제주",
}


def normalize_region(region):

    if pd.isna(region):
        return None

    region = str(region).strip()

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
# 5. 공정위 브랜드 정보 통합
# ============================================================

print()
print("========================================")
print("2. 공정위 브랜드 정보 읽기")
print("========================================")


brand_list = []


for file in BRAND_FILES:

    temp = pd.read_csv(
        file,
        encoding="utf-8"
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
# 6. 대상 업종 브랜드만 추출
# ============================================================

target_brand_df = brand_df[
    brand_df[
        "indutyLclasNm"
    ] == TARGET_MAJOR_INDUSTRY
].copy()


if TARGET_MIDDLE_INDUSTRIES is not None:

    target_brand_df = (
        target_brand_df[
            target_brand_df[
                "indutyMlsfcNm"
            ]
            .isin(
                TARGET_MIDDLE_INDUSTRIES
            )
        ]
        .copy()
    )


# 최신 브랜드 정보 우선
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


print(
    "공식 브랜드 후보 :",
    len(target_brand_df)
)


print()
print(
    "중분류 현황"
)

print(
    target_brand_df[
        "indutyMlsfcNm"
    ]
    .value_counts()
)


# ============================================================
# 7. 정확 일치 사전
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
# 9. 포함 검색
# ============================================================

contains_brand_df = (
    target_brand_df[
        target_brand_df[
            "brand_name_length"
        ] >= 3
    ]
    .copy()
)


name_counts = (
    contains_brand_df[
        "cleaned_brand_name"
    ]
    .value_counts()
)


duplicate_names = set(
    name_counts[
        name_counts > 1
    ].index
)


brand_names = (
    contains_brand_df[
        "cleaned_brand_name"
    ]
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
        re.escape(x)
        for x in brand_names
        if x
    )
    +
    ")"
)


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

    name = row[
        "cleaned_brand_name"
    ]

    if name in duplicate_names:
        continue

    brand_lookup[
        name
    ] = row


for index, brand_clean in extracted.items():

    if pd.isna(
        brand_clean
    ):
        continue


    if brand_clean in duplicate_names:

        shop_df.at[
            index,
            "match_type"
        ] = "duplicate_brand_name"

        shop_df.at[
            index,
            "match_confidence"
        ] = "REVIEW"

        continue


    row = brand_lookup.get(
        brand_clean
    )


    if row is None:
        continue


    shop_df.at[
        index,
        "brandMnno"
    ] = row[
        "brandMnno"
    ]

    shop_df.at[
        index,
        "matched_brandNm"
    ] = row[
        "brandNm"
    ]

    shop_df.at[
        index,
        "matched_corpNm"
    ] = row[
        "corpNm"
    ]

    shop_df.at[
        index,
        "matched_brand_industry"
    ] = row[
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


# ============================================================
# 10. 2차 상태
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


print()
print(
    "2차 자동확정 :",
    (
        shop_df[
            "match_status"
        ]
        == "자동확정"
    ).sum()
)


print(
    "2차 후보 :",
    (
        shop_df[
            "match_status"
        ]
        == "프랜차이즈후보"
    ).sum()
)


# ============================================================
# 11. 지역현황 읽기
# ============================================================

print()
print("========================================")
print("3. 브랜드 지역현황 읽기")
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


# ============================================================
# 12. 브랜드별 최신 연도 fallback
# ============================================================

latest_year = (
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
        latest_year,
        on="brandMnno"
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


latest_region_df[
    "normalized_region"
] = (
    latest_region_df[
        "areaNm"
    ]
)


# ============================================================
# 13. 지역 / 전국 분리
# ============================================================

regional = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ] != "전체"
    ]
    .copy()
)


national = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ] == "전체"
    ]
    .copy()
)


# ============================================================
# 14. 전남 + 광주 통합 비교
# ============================================================

south_gwangju = (
    regional[
        regional[
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
        "brandMnno"
    )
    .agg(
        frcsCnt=(
            "frcsCnt",
            lambda x:
            x.sum(
                min_count=1
            )
        ),

        dmsCnt=(
            "dmsCnt",
            lambda x:
            x.sum(
                min_count=1
            )
        ),

        allFrcsDmsCnt=(
            "allFrcsDmsCnt",
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


regional = pd.concat(
    [
        regional,
        south_gwangju
    ],
    ignore_index=True
)


# ============================================================
# 15. 상가 브랜드 + 지역 집계
# ============================================================

matched_df = (
    shop_df[
        shop_df[
            "brandMnno"
        ].notna()
    ]
    .copy()
)


shop_region_count = (
    matched_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm",
            "normalized_region"
        ]
    )
    .size()
    .reset_index(
        name="shop_store_count"
    )
)


# ============================================================
# 16. 지역현황 연결
# ============================================================

official_region = (
    regional[
        [
            "brandMnno",
            "normalized_region",
            "frcsCnt",
            "dmsCnt",
            "allFrcsDmsCnt",
            "selected_year"
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
# 17. 비율 계산
# ============================================================

validation_df[
    "ratio"
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
# 18. 지역 판정
# ============================================================

def validate_region(row):

    shop_count = row[
        "shop_store_count"
    ]

    official = row[
        "official_total_count"
    ]

    ratio = row[
        "ratio"
    ]


    if pd.isna(
        official
    ):
        return "공식지역정보없음"


    if official == 0:

        if shop_count <= 2:
            return "신규가능성"

        if shop_count <= 5:
            return "검토필요"

        return "강한검토필요"


    if (
        0.5
        <= ratio
        <= 1.5
    ):
        return "양호"


    if (
        0.2
        <= ratio
        <= 2
    ):
        return "유력"


    if ratio > 2:
        return "과다매칭검토"


    return "누락가능성"


validation_df[
    "region_validation"
] = (
    validation_df.apply(
        validate_region,
        axis=1
    )
)


# ============================================================
# 19. 지역 점수
# ============================================================

score_map = {

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
        score_map
    )
    .fillna(0)
)


# ============================================================
# 20. 브랜드 단위 검증
# ============================================================

brand_validation = (
    validation_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm"
        ]
    )
    .agg(

        store_count=(
            "shop_store_count",
            "sum"
        ),

        good_regions=(
            "region_validation",
            lambda x:
            x.isin(
                [
                    "양호",
                    "유력"
                ]
            ).sum()
        ),

        review_regions=(
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

        region_score=(
            "region_score",
            "sum"
        )

    )
    .reset_index()
)


def brand_status(row):

    if (
        row[
            "good_regions"
        ] >= 3
        and
        row[
            "review_regions"
        ] == 0
        and
        row[
            "region_score"
        ] >= 6
    ):
        return "지역검증우수"


    if (
        row[
            "good_regions"
        ] >= 1
        and
        row[
            "region_score"
        ] > 0
        and
        row[
            "review_regions"
        ] == 0
    ):
        return "지역검증유력"


    if (
        row[
            "review_regions"
        ] > 0
    ):
        return "지역검토필요"


    return "정보부족"


brand_validation[
    "brand_region_status"
] = (
    brand_validation.apply(
        brand_status,
        axis=1
    )
)


# ============================================================
# 21. 개별 상가에 지역검증 결과 연결
# ============================================================

shop_df = (
    shop_df
    .merge(
        brand_validation[
            [
                "brandMnno",
                "brand_region_status"
            ]
        ],
        on="brandMnno",
        how="left"
    )
)


# ============================================================
# 22. 최종 상태
# ============================================================

def final_status(row):

    name_status = row[
        "match_status"
    ]

    region_status = row[
        "brand_region_status"
    ]


    if (
        name_status
        == "자동확정"
        and
        region_status
        == "지역검증우수"
    ):
        return "확정"


    if (
        name_status
        == "자동확정"
        and
        region_status
        == "지역검증유력"
    ):
        return "확정유력"


    if (
        name_status
        == "프랜차이즈후보"
        and
        region_status
        == "지역검증우수"
    ):
        return "유력"


    if (
        name_status
        == "프랜차이즈후보"
        and
        region_status
        == "지역검증유력"
    ):
        return "유력"


    if (
        region_status
        == "지역검토필요"
    ):
        return "검토필요"


    if (
        name_status
        == "검토필요"
    ):
        return "검토필요"


    return "정보부족"


shop_df[
    "final_match_status"
] = (
    shop_df.apply(
        final_status,
        axis=1
    )
)


# ============================================================
# 23. 프로젝트 활용 데이터
# ============================================================

project_ready = (
    shop_df[
        shop_df[
            "final_match_status"
        ].isin(
            [
                "확정",
                "확정유력",
                "유력"
            ]
        )
    ]
    .copy()
)


review_df = (
    shop_df[
        shop_df[
            "final_match_status"
        ] == "검토필요"
    ]
    .copy()
)


# ============================================================
# 24. 분석 요약
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

            "검토필요",

            "프로젝트활용후보"
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
                == "검토필요"
            ).sum(),

            len(
                project_ready
            )
        ]
    }
)


print()
print("========================================")
print("최종 결과")
print("========================================")

print(
    summary_df.to_string(
        index=False
    )
)


# ============================================================
# 25. 엑셀 저장
# ============================================================

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


    brand_validation.to_excel(
        writer,
        sheet_name="브랜드지역요약",
        index=False
    )


    project_ready.to_excel(
        writer,
        sheet_name="프로젝트활용후보",
        index=False
    )


    review_df.to_excel(
        writer,
        sheet_name="검토필요",
        index=False
    )


print()
print("========================================")
print("저장 완료")
print("========================================")

print(
    OUTPUT_FILE
)