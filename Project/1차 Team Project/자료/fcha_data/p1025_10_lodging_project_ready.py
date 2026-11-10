import pandas as pd
import numpy as np
import json
import re
from pathlib import Path


# ============================================================
# 0. 기본 설정
# ============================================================

TARGET_NAME = "숙박업"

# ------------------------------------------------------------
# 전국상가정보
# 실제 폴더명이 다르면 이 부분만 수정
# ------------------------------------------------------------

SHOP_FILE = Path(
    r"C:\workspace\fcha_data\data\전국상가정보_숙박업_202610\records.csv"
)


# ------------------------------------------------------------
# 공정위 브랜드 기본정보
# ※ 이전에 정상 실행된 실제 경로를 그대로 넣어야 함
# ------------------------------------------------------------

# 공정위 브랜드 기본정보 2024 / 2025 / 2026
BRAND_FILES = [
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2024\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2025\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2026\records.csv"),
]


# ------------------------------------------------------------
# 브랜드 지역현황
# ------------------------------------------------------------

REGION_FILE = Path(
    r"C:\workspace\fcha_data\data\브랜드지역현황_v5\processed\brand_region_raw.json"
)


# ------------------------------------------------------------
# 결과 저장
# ------------------------------------------------------------

OUTPUT_DIR = Path(
    r"C:\workspace\fcha_data\output\project_ready"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "숙박업_프로젝트실제투입본.xlsx"
)


HOLD_CSV_FILE = (
    OUTPUT_DIR
    / "숙박업_보류후보.csv"
)


# ============================================================
# 1. 공정위 대상 업종
# ============================================================

TARGET_MAJOR_INDUSTRY = "서비스"

TARGET_MIDDLE_INDUSTRIES = [
    "숙박"
]


# ============================================================
# 2. 문자열 정리 함수
# ============================================================

def clean_name(name):

    if pd.isna(name):
        return ""

    name = str(name).strip().upper()

    # 공백 제거
    name = re.sub(
        r"\s+",
        "",
        name
    )

    # 한글 / 영문 / 숫자만 유지
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

    if region == "전남광주통합특별시":
        return "전남광주통합"

    return REGION_MAP.get(
        region,
        region
    )


# ============================================================
# 4. 입력 파일 존재 확인
# ============================================================

print()
print("========================================")
print("입력 파일 확인")
print("========================================")


if not SHOP_FILE.exists():

    raise FileNotFoundError(
        f"\n전국상가정보 파일을 찾을 수 없습니다.\n"
        f"{SHOP_FILE}\n"
        f"SHOP_FILE 경로를 확인해주세요."
    )


for file in BRAND_FILES:

    if not file.exists():

        raise FileNotFoundError(
            f"\n브랜드 기본정보 파일을 찾을 수 없습니다.\n"
            f"{file}\n"
            f"BRAND_FILES 경로를 확인해주세요."
        )


if not REGION_FILE.exists():

    raise FileNotFoundError(
        f"\n브랜드 지역현황 파일을 찾을 수 없습니다.\n"
        f"{REGION_FILE}"
    )


print("모든 입력 파일 확인 완료")


# ============================================================
# 5. 전국상가정보 읽기
# ============================================================

print()
print("========================================")
print("1. 전국상가 숙박업 읽기")
print("========================================")


shop_df = pd.read_csv(
    SHOP_FILE,
    encoding="utf-8"
)


SHOP_COLUMNS = [

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


SHOP_COLUMNS = [
    col
    for col in SHOP_COLUMNS
    if col in shop_df.columns
]


shop_df = (
    shop_df[
        SHOP_COLUMNS
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
    "전체 숙박 상가 :",
    len(shop_df)
)


# ============================================================
# 6. 공정위 브랜드 기본정보 읽기
# ============================================================

print()
print("========================================")
print("2. 공정위 숙박 브랜드 읽기")
print("========================================")


brand_list = []


for file in BRAND_FILES:

    temp = pd.read_csv(
        file,
        encoding="utf-8"
    )

    print(
        file.name,
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


# ============================================================
# 7. 숙박 브랜드만 필터
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


target_brand_df[
    "jngBizCrtraYr_num"
] = pd.to_numeric(
    target_brand_df[
        "jngBizCrtraYr"
    ],
    errors="coerce"
)


target_brand_df = (
    target_brand_df
    .sort_values(
        "jngBizCrtraYr_num",
        ascending=False
    )
    .drop_duplicates(
        subset="brandMnno",
        keep="first"
    )
    .reset_index(
        drop=True
    )
)


target_brand_df[
    "brand_length"
] = (
    target_brand_df[
        "cleaned_brand_name"
    ]
    .str.len()
)


print(
    "공정위 숙박 브랜드 후보 :",
    len(target_brand_df)
)


# ============================================================
# 8. 중복 정규화 브랜드명 확인
# ============================================================

brand_name_counts = (
    target_brand_df[
        "cleaned_brand_name"
    ]
    .value_counts()
)


duplicate_brand_names = set(
    brand_name_counts[
        brand_name_counts > 1
    ].index
)


# ============================================================
# 9. 정확 일치 사전
# ============================================================

exact_lookup = {}


for _, row in target_brand_df.iterrows():

    clean_brand = row[
        "cleaned_brand_name"
    ]


    if not clean_brand:
        continue


    if clean_brand in duplicate_brand_names:
        continue


    exact_lookup[
        clean_brand
    ] = {

        "brandMnno":
        row["brandMnno"],

        "brandNm":
        row["brandNm"],

        "corpNm":
        row["corpNm"],

        "industry":
        row["indutyMlsfcNm"]
    }


# ============================================================
# 10. 정확 일치
# ============================================================

shop_df[
    "brandMnno"
] = None

shop_df[
    "matched_brandNm"
] = None

shop_df[
    "matched_corpNm"
] = None

shop_df[
    "matched_brand_industry"
] = None

shop_df[
    "match_type"
] = None


for index, store_name in shop_df[
    "cleaned_store_name"
].items():


    if store_name in exact_lookup:

        info = exact_lookup[
            store_name
        ]

        shop_df.at[
            index,
            "brandMnno"
        ] = info["brandMnno"]

        shop_df.at[
            index,
            "matched_brandNm"
        ] = info["brandNm"]

        shop_df.at[
            index,
            "matched_corpNm"
        ] = info["corpNm"]

        shop_df.at[
            index,
            "matched_brand_industry"
        ] = info["industry"]

        shop_df.at[
            index,
            "match_type"
        ] = "exact"


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
# 11. PREFIX 후보 매칭
# ============================================================
#
# 단순 contains는 프로젝트 실제 투입에 사용하지 않는다.
#
# 상호가 공식 브랜드명으로 시작할 때만 후보로 만든다.
#
# ============================================================

prefix_brand_df = (
    target_brand_df[
        target_brand_df[
            "brand_length"
        ] >= 4
    ]
    .copy()
)


prefix_brand_df = (
    prefix_brand_df[
        ~prefix_brand_df[
            "cleaned_brand_name"
        ]
        .isin(
            duplicate_brand_names
        )
    ]
)


prefix_brand_df = (
    prefix_brand_df
    .sort_values(
        "brand_length",
        ascending=False
    )
)


prefix_records = (
    prefix_brand_df[
        [
            "brandMnno",
            "brandNm",
            "corpNm",
            "indutyMlsfcNm",
            "cleaned_brand_name"
        ]
    ]
    .to_dict(
        "records"
    )
)


no_match_indexes = (
    shop_df[
        shop_df[
            "brandMnno"
        ]
        .isna()
    ]
    .index
)


for index in no_match_indexes:

    store_name = shop_df.at[
        index,
        "cleaned_store_name"
    ]


    if not store_name:
        continue


    for brand in prefix_records:

        brand_name = brand[
            "cleaned_brand_name"
        ]


        if store_name.startswith(
            brand_name
        ):

            shop_df.at[
                index,
                "brandMnno"
            ] = brand[
                "brandMnno"
            ]

            shop_df.at[
                index,
                "matched_brandNm"
            ] = brand[
                "brandNm"
            ]

            shop_df.at[
                index,
                "matched_corpNm"
            ] = brand[
                "corpNm"
            ]

            shop_df.at[
                index,
                "matched_brand_industry"
            ] = brand[
                "indutyMlsfcNm"
            ]

            shop_df.at[
                index,
                "match_type"
            ] = "prefix"

            break


print(
    "PREFIX 일치 :",
    (
        shop_df[
            "match_type"
        ]
        == "prefix"
    ).sum()
)


# ============================================================
# 12. 지역현황 읽기
# ============================================================

print()
print("========================================")
print("3. 공정위 지역현황 검증")
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
# 13. 브랜드별 최신 지역자료 선택
# ============================================================

latest_year_df = (
    region_df
    .groupby(
        "brandMnno"
    )[
        "jngBizCrtraYr_num"
    ]
    .max()
    .reset_index(
        name="selected_year"
    )
)


latest_region_df = (
    region_df
    .merge(
        latest_year_df,
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


latest_region_df[
    "normalized_region"
] = (
    latest_region_df[
        "areaNm"
    ]
)


regional_df = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ]
        != "전체"
    ]
    .copy()
)


official_region = (
    regional_df[
        [
            "brandMnno",
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
# 14. 광주 + 전남 통합 비교
# ============================================================

gwangju_jeonnam = (
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
        "brandMnno",
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


gwangju_jeonnam[
    "normalized_region"
] = "전남광주통합"


official_region = pd.concat(
    [
        official_region,
        gwangju_jeonnam
    ],
    ignore_index=True
)


# ============================================================
# 15. 매칭된 상가만 지역별 집계
# ============================================================

matched_df = (
    shop_df[
        shop_df[
            "brandMnno"
        ]
        .notna()
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
        ],
        dropna=False
    )
    .size()
    .reset_index(
        name="shop_store_count"
    )
)


# ============================================================
# 16. 공식 지역수 연결
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
# 17. 지역 판정
# ============================================================

def region_validation(row):

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


    if 0.5 <= ratio <= 1.5:
        return "양호"


    if 0.2 <= ratio <= 2.0:
        return "유력"


    if ratio > 2.0:
        return "과다매칭검토"


    return "누락가능성"


validation_df[
    "region_validation"
] = (
    validation_df.apply(
        region_validation,
        axis=1
    )
)


# ============================================================
# 18. 지역 점수
# ============================================================

SCORE_MAP = {

    "양호": 3,
    "유력": 2,
    "누락가능성": 1,
    "신규가능성": 1,

    "공식지역정보없음": 0,
    "검토필요": 0,

    "과다매칭검토": -2,
    "강한검토필요": -3
}


validation_df[
    "region_score"
] = (
    validation_df[
        "region_validation"
    ]
    .map(
        SCORE_MAP
    )
    .fillna(0)
)


# ============================================================
# 19. 브랜드별 지역 검증 요약
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

        good_region_count=(
            "region_validation",
            lambda x:
            x.isin(
                [
                    "양호",
                    "유력"
                ]
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

        new_possible_count=(
            "region_validation",
            lambda x:
            (
                x
                == "신규가능성"
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
# 20. 브랜드 지역상태
# ============================================================

def brand_region_status(row):

    good = row[
        "good_region_count"
    ]

    review = row[
        "review_region_count"
    ]

    no_info = row[
        "no_official_info_count"
    ]

    new_count = row[
        "new_possible_count"
    ]

    score = row[
        "region_score_sum"
    ]


    if (
        good >= 3
        and
        review == 0
        and
        no_info == 0
        and
        score >= 6
    ):
        return "지역검증우수"


    if review > 0:
        return "지역검토필요"


    if no_info > 0:
        return "공식정보부족"


    if new_count > 0:
        return "신규가능성포함"


    return "지역검증부족"


brand_validation_df[
    "brand_region_status"
] = (
    brand_validation_df.apply(
        brand_region_status,
        axis=1
    )
)


# ============================================================
# 21. 상가 데이터에 지역검증 붙이기
# ============================================================

shop_df = (
    shop_df
    .merge(
        brand_validation_df,
        on=[
            "brandMnno",
            "matched_brandNm"
        ],
        how="left"
    )
)


# ============================================================
# 22. 프로젝트 실제 투입 기준
# ============================================================
#
# 매우 보수적
#
# 1. EXACT + 지역검증우수
# 또는
# 2. 4글자 이상 PREFIX + 지역검증우수
#
# 검토지역 0
# 공식정보 부족 0
#
# ============================================================

shop_df[
    "matched_brand_length"
] = (
    shop_df[
        "matched_brandNm"
    ]
    .apply(
        clean_name
    )
    .str.len()
)


exact_condition = (

    (
        shop_df[
            "match_type"
        ]
        == "exact"
    )

    &

    (
        shop_df[
            "brand_region_status"
        ]
        == "지역검증우수"
    )

    &

    (
        shop_df[
            "review_region_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        shop_df[
            "no_official_info_count"
        ]
        .fillna(0)
        == 0
    )
)


prefix_condition = (

    (
        shop_df[
            "match_type"
        ]
        == "prefix"
    )

    &

    (
        shop_df[
            "matched_brand_length"
        ]
        >= 4
    )

    &

    (
        shop_df[
            "brand_region_status"
        ]
        == "지역검증우수"
    )

    &

    (
        shop_df[
            "review_region_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        shop_df[
            "no_official_info_count"
        ]
        .fillna(0)
        == 0
    )
)


shop_df[
    "project_ready"
] = (
    exact_condition
    |
    prefix_condition
)


# ============================================================
# 23. 실제 투입 근거
# ============================================================

def project_reason(row):

    if not row[
        "project_ready"
    ]:
        return None


    if row[
        "match_type"
    ] == "exact":

        return "공식브랜드정확일치+지역검증우수"


    return "4글자이상PREFIX+지역검증우수"


shop_df[
    "project_reason"
] = (
    shop_df.apply(
        project_reason,
        axis=1
    )
)


# ============================================================
# 24. 보류 사유
# ============================================================

def hold_reason(row):

    if row[
        "project_ready"
    ]:
        return None


    if pd.isna(
        row[
            "brandMnno"
        ]
    ):
        return "브랜드미매칭"


    if (
        row[
            "brand_region_status"
        ]
        == "지역검토필요"
    ):
        return "지역검토필요"


    if (
        row[
            "brand_region_status"
        ]
        == "공식정보부족"
    ):
        return "공식정보부족"


    if (
        row[
            "brand_region_status"
        ]
        == "신규가능성포함"
    ):
        return "신규가능성"


    if (
        row[
            "matched_brand_length"
        ]
        <= 3
    ):
        return "브랜드명3글자이하"


    if (
        row[
            "brand_region_status"
        ]
        != "지역검증우수"
    ):
        return "지역검증우수아님"


    return "보수적기준미충족"


shop_df[
    "hold_reason"
] = (
    shop_df.apply(
        hold_reason,
        axis=1
    )
)


# ============================================================
# 25. 실제 투입 / 보류 분리
# ============================================================

project_df = (
    shop_df[
        shop_df[
            "project_ready"
        ]
        == True
    ]
    .copy()
)


hold_df = (
    shop_df[
        shop_df[
            "project_ready"
        ]
        == False
    ]
    .copy()
)


# ============================================================
# 26. 프로젝트용 핵심 컬럼
# ============================================================

PROJECT_COLUMNS = [

    "bizesId",

    "brandMnno",
    "matched_brandNm",
    "matched_corpNm",
    "matched_brand_industry",

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
    "lat",

    "project_reason"
]


PROJECT_COLUMNS = [
    col
    for col in PROJECT_COLUMNS
    if col in project_df.columns
]


project_clean_df = (
    project_df[
        PROJECT_COLUMNS
    ]
    .copy()
)


# ============================================================
# 27. 브랜드별 요약
# ============================================================

brand_summary_df = (
    project_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm"
        ],
        dropna=False
    )
    .agg(

        store_count=(
            "bizesId",
            "count"
        ),

        province_count=(
            "ctprvnNm",
            "nunique"
        ),

        district_count=(
            "signguNm",
            "nunique"
        )

    )
    .reset_index()
    .sort_values(
        "store_count",
        ascending=False
    )
)


# ============================================================
# 28. 지역별 요약
# ============================================================

region_summary_df = (
    project_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm",
            "ctprvnNm",
            "signguNm"
        ],
        dropna=False
    )
    .size()
    .reset_index(
        name="store_count"
    )
)


# ============================================================
# 29. 보류 사유 요약
# ============================================================

hold_summary_df = (
    hold_df[
        "hold_reason"
    ]
    .value_counts(
        dropna=False
    )
    .reset_index()
)


hold_summary_df.columns = [
    "보류사유",
    "건수"
]


# ============================================================
# 30. 분석 요약
# ============================================================

summary_df = pd.DataFrame(
    {

        "항목": [

            "숙박업 전체 상가",

            "공정위 숙박 브랜드",

            "브랜드 매칭",

            "프로젝트 실제 투입",

            "정확일치 투입",

            "4글자이상 PREFIX 투입",

            "보류",

            "최종 브랜드 수"
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

            len(
                project_df
            ),

            (
                project_df[
                    "project_reason"
                ]
                ==
                "공식브랜드정확일치+지역검증우수"
            ).sum(),

            (
                project_df[
                    "project_reason"
                ]
                ==
                "4글자이상PREFIX+지역검증우수"
            ).sum(),

            len(
                hold_df
            ),

            project_df[
                "brandMnno"
            ]
            .nunique()
        ]
    }
)


# ============================================================
# 31. 콘솔 출력
# ============================================================

print()
print("========================================")
print("숙박업 최종 결과")
print("========================================")

print(
    summary_df.to_string(
        index=False
    )
)


print()
print("========================================")
print("보류 사유")
print("========================================")

print(
    hold_summary_df.to_string(
        index=False
    )
)


print()
print("========================================")
print("최종 브랜드")
print("========================================")

print(
    brand_summary_df.to_string(
        index=False
    )
)


# ============================================================
# 32. 경량 엑셀 저장
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


    project_clean_df.to_excel(
        writer,
        sheet_name="프로젝트실제투입",
        index=False
    )


    brand_summary_df.to_excel(
        writer,
        sheet_name="투입브랜드요약",
        index=False
    )


    region_summary_df.to_excel(
        writer,
        sheet_name="투입지역별요약",
        index=False
    )


    hold_summary_df.to_excel(
        writer,
        sheet_name="보류사유요약",
        index=False
    )


# ============================================================
# 33. 보류 데이터 CSV
# ============================================================

hold_df.to_csv(
    HOLD_CSV_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 34. 완료
# ============================================================

print()
print("========================================")
print("저장 완료")
print("========================================")

print()
print("프로젝트 실제 투입본:")
print(
    OUTPUT_FILE
)

print()
print("보류 후보:")
print(
    HOLD_CSV_FILE
)