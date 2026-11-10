import pandas as pd
import numpy as np
import json
import re
from pathlib import Path


# ============================================================
# 0. 기본 설정
# ============================================================

TARGET_MAJOR_INDUSTRY = "외식"


# ============================================================
# 1. 전국상가정보 외식 파일
# ============================================================
#
# ★ 이 경로는 네 실제 전국상가 외식 파일명에 맞게 수정
#
# 예:
# 전국상가정보_음식점업_202610
# 전국상가정보_숙박음식점업_202610
# 등 실제 폴더명 사용
#
# ============================================================

SHOP_FILE = Path(
    r"C:\workspace\fcha_data\data\전국상가정보_음식업_202610\records.csv"
)


# ============================================================
# 2. 공정위 브랜드 기본정보
# ============================================================

BRAND_FILES = [
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2024\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2025\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2026\records.csv"),
]


# ============================================================
# 3. 브랜드 지역현황
# ============================================================

REGION_FILE = Path(
    r"C:\workspace\fcha_data\data\브랜드지역현황_v5\processed\brand_region_raw.json"
)


# ============================================================
# 4. 출력 경로
# ============================================================

OUTPUT_ROOT = Path(
    r"C:\workspace\fcha_data\output\project_ready\외식"
)

OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True
)


SUMMARY_FILE = (
    OUTPUT_ROOT
    / "외식_전체요약.xlsx"
)


# ============================================================
# 5. 문자열 정리
# ============================================================

def clean_name(name):

    if pd.isna(name):
        return ""

    name = str(name).strip().upper()

    # 모든 공백 제거
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
# 6. 파일명에 사용할 문자열 정리
# ============================================================

def clean_filename(name):

    name = str(name).strip()

    name = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        name
    )

    name = name.replace(
        " ",
        "_"
    )

    return name


# ============================================================
# 7. 지역명 정규화
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

    # 2026 현재 행정구역
    if region == "전남광주통합특별시":
        return "전남광주통합"

    return REGION_MAP.get(
        region,
        region
    )


# ============================================================
# 8. 입력 파일 존재 확인
# ============================================================

print()
print("========================================")
print("입력 파일 확인")
print("========================================")


if not SHOP_FILE.exists():

    raise FileNotFoundError(
        "\n전국상가 외식 파일을 찾지 못했습니다.\n"
        f"{SHOP_FILE}\n\n"
        "SHOP_FILE 경로를 실제 폴더명으로 수정해주세요."
    )


for file in BRAND_FILES:

    if not file.exists():

        raise FileNotFoundError(
            "\n공정위 브랜드 파일을 찾지 못했습니다.\n"
            f"{file}"
        )


if not REGION_FILE.exists():

    raise FileNotFoundError(
        "\n브랜드 지역현황 파일을 찾지 못했습니다.\n"
        f"{REGION_FILE}"
    )


print("모든 입력 파일 확인 완료")


# ============================================================
# 9. 전국상가 외식 파일 읽기
# ============================================================

print()
print("========================================")
print("1. 전국상가 외식 데이터 읽기")
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
    "전체 외식 상가 :",
    len(shop_df)
)


# ============================================================
# 10. 전국상가 업종 확인
# ============================================================

print()
print("전국상가 중분류")

if "indsMclsNm" in shop_df.columns:

    print(
        shop_df[
            "indsMclsNm"
        ]
        .value_counts(
            dropna=False
        )
        .head(50)
    )


print()
print("전국상가 소분류")

if "indsSclsNm" in shop_df.columns:

    print(
        shop_df[
            "indsSclsNm"
        ]
        .value_counts(
            dropna=False
        )
        .head(100)
    )


# ============================================================
# 11. 공정위 브랜드 기본정보 읽기
# ============================================================

print()
print("========================================")
print("2. 공정위 브랜드 기본정보")
print("========================================")


brand_list = []


for file in BRAND_FILES:

    temp = pd.read_csv(
        file,
        encoding="utf-8"
    )

    print(
        file.parent.name,
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
    "jngBizCrtraYr_num"
] = pd.to_numeric(
    brand_df[
        "jngBizCrtraYr"
    ],
    errors="coerce"
)


# ============================================================
# 12. 외식 브랜드만 추출
# ============================================================

food_brand_df = (
    brand_df[
        brand_df[
            "indutyLclasNm"
        ]
        == TARGET_MAJOR_INDUSTRY
    ]
    .copy()
)


print()
print(
    "공정위 외식 전체 행 :",
    len(food_brand_df)
)


# ============================================================
# 13. 브랜드별 최신 정보만 사용
# ============================================================

food_brand_latest_df = (
    food_brand_df
    .sort_values(
        "jngBizCrtraYr_num",
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


food_brand_latest_df[
    "brand_length"
] = (
    food_brand_latest_df[
        "cleaned_brand_name"
    ]
    .str.len()
)


print(
    "외식 고유 브랜드 :",
    food_brand_latest_df[
        "brandMnno"
    ]
    .nunique()
)


# ============================================================
# 14. 실제 공정위 외식 중분류 확인
# ============================================================

middle_categories = (
    food_brand_latest_df[
        "indutyMlsfcNm"
    ]
    .dropna()
    .drop_duplicates()
    .sort_values()
    .tolist()
)


print()
print("========================================")
print("공정위 외식 중분류")
print("========================================")


for category in middle_categories:

    count = (
        food_brand_latest_df[
            "indutyMlsfcNm"
        ]
        == category
    ).sum()

    print(
        category,
        ":",
        count,
        "개 브랜드"
    )


print()
print(
    "외식 중분류 개수 :",
    len(middle_categories)
)


# ============================================================
# 15. 브랜드 지역현황 읽기
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
# 16. 브랜드별 최신 지역현황
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
# 17. 광주 + 전남 통합 비교값 생성
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
# 18. 지역 검증 함수
# ============================================================

def check_region(row):

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


REGION_SCORE_MAP = {

    "양호": 3,
    "유력": 2,

    "누락가능성": 1,
    "신규가능성": 1,

    "공식지역정보없음": 0,
    "검토필요": 0,

    "과다매칭검토": -2,
    "강한검토필요": -3
}


# ============================================================
# 19. 전체 요약 저장용 리스트
# ============================================================

overall_summary = []


# ============================================================
# 20. 중분류별 반복 처리
# ============================================================

for category in middle_categories:

    print()
    print()
    print("########################################")
    print(
        "중분류 처리 :",
        category
    )
    print("########################################")


    # --------------------------------------------------------
    # 20-1. 해당 중분류 브랜드
    # --------------------------------------------------------

    category_brand_df = (
        food_brand_latest_df[
            food_brand_latest_df[
                "indutyMlsfcNm"
            ]
            == category
        ]
        .copy()
    )


    print(
        "공정위 브랜드 :",
        len(category_brand_df)
    )


    # --------------------------------------------------------
    # 20-2. 중복 브랜드명 찾기
    # --------------------------------------------------------

    brand_name_counts = (
        category_brand_df[
            "cleaned_brand_name"
        ]
        .value_counts()
    )


    duplicate_brand_names = set(
        brand_name_counts[
            brand_name_counts > 1
        ].index
    )


    # --------------------------------------------------------
    # 20-3. 정확일치 사전
    # --------------------------------------------------------

    exact_lookup = {}


    for _, row in category_brand_df.iterrows():

        cleaned = row[
            "cleaned_brand_name"
        ]


        if not cleaned:
            continue


        if cleaned in duplicate_brand_names:
            continue


        exact_lookup[
            cleaned
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


    # --------------------------------------------------------
    # 20-4. 상가 복사
    # --------------------------------------------------------

    category_shop_df = (
        shop_df.copy()
    )


    category_shop_df[
        "brandMnno"
    ] = None

    category_shop_df[
        "matched_brandNm"
    ] = None

    category_shop_df[
        "matched_corpNm"
    ] = None

    category_shop_df[
        "matched_brand_industry"
    ] = None

    category_shop_df[
        "match_type"
    ] = None


    # --------------------------------------------------------
    # 20-5. EXACT
    # --------------------------------------------------------

    for index, store_name in category_shop_df[
        "cleaned_store_name"
    ].items():


        if store_name in exact_lookup:

            info = exact_lookup[
                store_name
            ]

            category_shop_df.at[
                index,
                "brandMnno"
            ] = info[
                "brandMnno"
            ]

            category_shop_df.at[
                index,
                "matched_brandNm"
            ] = info[
                "brandNm"
            ]

            category_shop_df.at[
                index,
                "matched_corpNm"
            ] = info[
                "corpNm"
            ]

            category_shop_df.at[
                index,
                "matched_brand_industry"
            ] = info[
                "industry"
            ]

            category_shop_df.at[
                index,
                "match_type"
            ] = "exact"


    # --------------------------------------------------------
    # 20-6. PREFIX용 브랜드
    # --------------------------------------------------------

    prefix_brand_df = (
        category_brand_df[
            category_brand_df[
                "brand_length"
            ]
            >= 4
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
        .copy()
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


    # --------------------------------------------------------
    # 20-7. PREFIX 매칭
    # --------------------------------------------------------

    no_match_indexes = (
        category_shop_df[
            category_shop_df[
                "brandMnno"
            ]
            .isna()
        ]
        .index
    )


    for index in no_match_indexes:

        store_name = category_shop_df.at[
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

                category_shop_df.at[
                    index,
                    "brandMnno"
                ] = brand[
                    "brandMnno"
                ]

                category_shop_df.at[
                    index,
                    "matched_brandNm"
                ] = brand[
                    "brandNm"
                ]

                category_shop_df.at[
                    index,
                    "matched_corpNm"
                ] = brand[
                    "corpNm"
                ]

                category_shop_df.at[
                    index,
                    "matched_brand_industry"
                ] = brand[
                    "indutyMlsfcNm"
                ]

                category_shop_df.at[
                    index,
                    "match_type"
                ] = "prefix"

                break


    # --------------------------------------------------------
    # 20-8. 매칭 결과
    # --------------------------------------------------------

    matched_df = (
        category_shop_df[
            category_shop_df[
                "brandMnno"
            ]
            .notna()
        ]
        .copy()
    )


    exact_count = (
        matched_df[
            "match_type"
        ]
        == "exact"
    ).sum()


    prefix_count = (
        matched_df[
            "match_type"
        ]
        == "prefix"
    ).sum()


    print(
        "이름 매칭 :",
        len(matched_df)
    )

    print(
        "EXACT :",
        exact_count
    )

    print(
        "PREFIX :",
        prefix_count
    )


    # --------------------------------------------------------
    # 매칭이 하나도 없을 경우
    # --------------------------------------------------------

    if matched_df.empty:

        overall_summary.append(
            {
                "중분류": category,
                "공정위브랜드수": len(category_brand_df),
                "브랜드매칭": 0,
                "프로젝트실제투입": 0,
                "정확일치투입": 0,
                "PREFIX투입": 0,
                "최종브랜드수": 0
            }
        )

        print(
            "→ 매칭 데이터 없음"
        )

        continue


    # --------------------------------------------------------
    # 20-9. 지역별 매장 수
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-10. 공식 지역자료 연결
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-11. 비율
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-12. 지역 판정
    # --------------------------------------------------------

    validation_df[
        "region_validation"
    ] = (
        validation_df.apply(
            check_region,
            axis=1
        )
    )


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


    # --------------------------------------------------------
    # 20-13. 브랜드별 지역요약
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-14. 브랜드 지역상태
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-15. 상가에 지역검증 연결
    # --------------------------------------------------------

    category_shop_df = (
        category_shop_df
        .merge(

            brand_validation_df,

            on=[
                "brandMnno",
                "matched_brandNm"
            ],

            how="left"
        )
    )


    # --------------------------------------------------------
    # 20-16. 브랜드명 길이
    # --------------------------------------------------------

    category_shop_df[
        "matched_brand_length"
    ] = (
        category_shop_df[
            "matched_brandNm"
        ]
        .apply(
            clean_name
        )
        .str.len()
    )


    # --------------------------------------------------------
    # 20-17. 프로젝트 실제 투입 조건
    # --------------------------------------------------------
    #
    # EXACT + 지역검증우수
    #
    # 또는
    #
    # 4글자 이상 PREFIX + 지역검증우수
    #
    # --------------------------------------------------------

    exact_condition = (

        (
            category_shop_df[
                "match_type"
            ]
            == "exact"
        )

        &

        (
            category_shop_df[
                "brand_region_status"
            ]
            == "지역검증우수"
        )

        &

        (
            category_shop_df[
                "review_region_count"
            ]
            .fillna(0)
            == 0
        )

        &

        (
            category_shop_df[
                "no_official_info_count"
            ]
            .fillna(0)
            == 0
        )
    )


    prefix_condition = (

        (
            category_shop_df[
                "match_type"
            ]
            == "prefix"
        )

        &

        (
            category_shop_df[
                "matched_brand_length"
            ]
            >= 4
        )

        &

        (
            category_shop_df[
                "brand_region_status"
            ]
            == "지역검증우수"
        )

        &

        (
            category_shop_df[
                "review_region_count"
            ]
            .fillna(0)
            == 0
        )

        &

        (
            category_shop_df[
                "no_official_info_count"
            ]
            .fillna(0)
            == 0
        )
    )


    category_shop_df[
        "project_ready"
    ] = (
        exact_condition
        |
        prefix_condition
    )


    # --------------------------------------------------------
    # 20-18. 프로젝트 투입 근거
    # --------------------------------------------------------

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


    category_shop_df[
        "project_reason"
    ] = (
        category_shop_df.apply(
            project_reason,
            axis=1
        )
    )


    # --------------------------------------------------------
    # 20-19. 보류 사유
    # --------------------------------------------------------

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


    category_shop_df[
        "hold_reason"
    ] = (
        category_shop_df.apply(
            hold_reason,
            axis=1
        )
    )


    # --------------------------------------------------------
    # 20-20. 프로젝트 실제 투입
    # --------------------------------------------------------

    project_df = (
        category_shop_df[
            category_shop_df[
                "project_ready"
            ]
            == True
        ]
        .copy()
    )


    # --------------------------------------------------------
    # 20-21. 보류
    #
    # 여기서는 전체 미매칭 10만 건을 CSV에 넣지 않고
    # 이름 매칭은 됐지만 프로젝트 기준에서 떨어진 것만 저장
    #
    # --------------------------------------------------------

    hold_df = (
        category_shop_df[
            (
                category_shop_df[
                    "brandMnno"
                ]
                .notna()
            )
            &
            (
                category_shop_df[
                    "project_ready"
                ]
                == False
            )
        ]
        .copy()
    )


    # --------------------------------------------------------
    # 20-22. 프로젝트 핵심 컬럼
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 20-23. 브랜드별 요약
    # --------------------------------------------------------

    if not project_df.empty:

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
                ),

                exact_count=(
                    "project_reason",
                    lambda x:
                    (
                        x
                        ==
                        "공식브랜드정확일치+지역검증우수"
                    ).sum()
                ),

                prefix_count=(
                    "project_reason",
                    lambda x:
                    (
                        x
                        ==
                        "4글자이상PREFIX+지역검증우수"
                    ).sum()
                )

            )
            .reset_index()
            .sort_values(
                "store_count",
                ascending=False
            )
        )


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

    else:

        brand_summary_df = pd.DataFrame(
            columns=[
                "brandMnno",
                "matched_brandNm",
                "store_count",
                "province_count",
                "district_count",
                "exact_count",
                "prefix_count"
            ]
        )


        region_summary_df = pd.DataFrame(
            columns=[
                "brandMnno",
                "matched_brandNm",
                "ctprvnNm",
                "signguNm",
                "store_count"
            ]
        )


    # --------------------------------------------------------
    # 20-24. 보류 요약
    # --------------------------------------------------------

    if not hold_df.empty:

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

    else:

        hold_summary_df = pd.DataFrame(
            columns=[
                "보류사유",
                "건수"
            ]
        )


    # --------------------------------------------------------
    # 20-25. 중분류 분석 요약
    # --------------------------------------------------------

    summary_df = pd.DataFrame(
        {

            "항목": [

                "공정위 중분류",

                "공정위 브랜드",

                "이름 매칭",

                "프로젝트 실제 투입",

                "정확일치 투입",

                "4글자이상 PREFIX 투입",

                "보류 후보",

                "최종 브랜드 수"
            ],

            "값": [

                category,

                len(
                    category_brand_df
                ),

                len(
                    matched_df
                ),

                len(
                    project_df
                ),

                (
                    project_df[
                        "project_reason"
                    ]
                    ==
                    "공식브랜드정확일치+지역검증우수"
                ).sum()
                if not project_df.empty
                else 0,

                (
                    project_df[
                        "project_reason"
                    ]
                    ==
                    "4글자이상PREFIX+지역검증우수"
                ).sum()
                if not project_df.empty
                else 0,

                len(
                    hold_df
                ),

                project_df[
                    "brandMnno"
                ]
                .nunique()
                if not project_df.empty
                else 0
            ]
        }
    )


    # --------------------------------------------------------
    # 20-26. 폴더 생성
    # --------------------------------------------------------

    safe_category = clean_filename(
        category
    )


    CATEGORY_DIR = (
        OUTPUT_ROOT
        / safe_category
    )


    CATEGORY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    excel_file = (
        CATEGORY_DIR
        /
        f"외식_{safe_category}_프로젝트실제투입본.xlsx"
    )


    hold_csv_file = (
        CATEGORY_DIR
        /
        f"외식_{safe_category}_보류후보.csv"
    )


    # --------------------------------------------------------
    # 20-27. 경량 엑셀 저장
    # --------------------------------------------------------

    with pd.ExcelWriter(
        excel_file,
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


    # --------------------------------------------------------
    # 20-28. 보류 CSV
    # --------------------------------------------------------

    hold_df.to_csv(
        hold_csv_file,
        index=False,
        encoding="utf-8-sig"
    )


    # --------------------------------------------------------
    # 20-29. 전체 요약용 저장
    # --------------------------------------------------------

    exact_project_count = (
        (
            project_df[
                "project_reason"
            ]
            ==
            "공식브랜드정확일치+지역검증우수"
        ).sum()
        if not project_df.empty
        else 0
    )


    prefix_project_count = (
        (
            project_df[
                "project_reason"
            ]
            ==
            "4글자이상PREFIX+지역검증우수"
        ).sum()
        if not project_df.empty
        else 0
    )


    overall_summary.append(
        {

            "중분류":
            category,

            "공정위브랜드수":
            len(
                category_brand_df
            ),

            "브랜드매칭":
            len(
                matched_df
            ),

            "프로젝트실제투입":
            len(
                project_df
            ),

            "정확일치투입":
            exact_project_count,

            "PREFIX투입":
            prefix_project_count,

            "보류후보":
            len(
                hold_df
            ),

            "최종브랜드수":
            project_df[
                "brandMnno"
            ]
            .nunique()
            if not project_df.empty
            else 0
        }
    )


    print()
    print(
        "프로젝트 실제 투입 :",
        len(
            project_df
        )
    )

    print(
        "최종 브랜드 :",
        project_df[
            "brandMnno"
        ]
        .nunique()
        if not project_df.empty
        else 0
    )

    print(
        "저장:",
        excel_file
    )


# ============================================================
# 21. 외식 전체 요약
# ============================================================

overall_summary_df = pd.DataFrame(
    overall_summary
)


if not overall_summary_df.empty:

    overall_summary_df = (
        overall_summary_df
        .sort_values(
            [
                "프로젝트실제투입",
                "최종브랜드수"
            ],
            ascending=[
                False,
                False
            ]
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# 22. 외식 전체 중분류 브랜드 현황
# ============================================================

brand_category_summary_df = (
    food_brand_latest_df
    .groupby(
        "indutyMlsfcNm",
        dropna=False
    )
    .agg(

        official_brand_count=(
            "brandMnno",
            "nunique"
        )

    )
    .reset_index()
    .sort_values(
        "official_brand_count",
        ascending=False
    )
)


# ============================================================
# 23. 전체 요약 엑셀 저장
# ============================================================

with pd.ExcelWriter(
    SUMMARY_FILE,
    engine="openpyxl"
) as writer:


    overall_summary_df.to_excel(
        writer,
        sheet_name="중분류별결과",
        index=False
    )


    brand_category_summary_df.to_excel(
        writer,
        sheet_name="공정위중분류현황",
        index=False
    )


# ============================================================
# 24. 최종 콘솔 출력
# ============================================================

print()
print()
print("========================================")
print("외식 전체 작업 완료")
print("========================================")


print(
    overall_summary_df.to_string(
        index=False
    )
)


print()
print(
    "전체 요약 파일:",
    SUMMARY_FILE
)

print()
print(
    "결과 폴더:",
    OUTPUT_ROOT
)