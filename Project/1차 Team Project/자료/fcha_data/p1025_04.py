import pandas as pd
import json
import numpy as np
from pathlib import Path


# ============================================================
# 0. 경로 설정
# ============================================================

MATCH_FILE = Path(
    r"C:\workspace\fcha_data\output\franchise_matching\교육서비스업_프랜차이즈_2차자동매칭.xlsx"
)

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
    / "교육서비스업_프랜차이즈_4차최종지역검증.xlsx"
)


# ============================================================
# 1. 2차 자동매칭 결과 읽기
# ============================================================

print()
print("========================================")
print("1. 2차 자동매칭 결과 읽기")
print("========================================")

match_df = pd.read_excel(
    MATCH_FILE,
    sheet_name="전체매칭결과"
)

print("전체 상가 :", len(match_df))

print(
    "brandMnno 존재 :",
    match_df["brandMnno"].notna().sum()
)


# ============================================================
# 2. 브랜드 지역현황 읽기
# ============================================================

print()
print("========================================")
print("2. 브랜드 지역현황 읽기")
print("========================================")

with open(
    REGION_FILE,
    "r",
    encoding="utf-8"
) as f:
    region_data = json.load(f)


region_df = pd.DataFrame(
    region_data
)


print(
    "지역현황 전체 :",
    len(region_df)
)

print(
    "고유 브랜드 :",
    region_df["brandMnno"].nunique()
)


# ============================================================
# 3. 숫자 컬럼 정리
# ============================================================

number_cols = [
    "frcsCnt",
    "dmsCnt",
    "allFrcsDmsCnt"
]

for col in number_cols:

    region_df[col] = pd.to_numeric(
        region_df[col],
        errors="coerce"
    )


# ============================================================
# 4. 연도 컬럼 숫자 변환
# ============================================================

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
# 5. 지역명 정규화
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


def normalize_shop_region(region):

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


match_df[
    "normalized_region"
] = (
    match_df[
        "ctprvnNm"
    ]
    .apply(
        normalize_shop_region
    )
)


region_df[
    "normalized_region"
] = (
    region_df[
        "areaNm"
    ]
)


# ============================================================
# 6. 브랜드별 최신 지역현황 선택
# ============================================================
#
# 핵심:
#
# 브랜드마다 최신 조회연도가 다를 수 있음
#
# 2026 있으면 2026
# 없으면 2025
# 없으면 2024
#
# 즉 전 브랜드에 2026을 강제하지 않음
# ============================================================

print()
print("========================================")
print("3. 브랜드별 최신 지역현황 선택")
print("========================================")


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
            "selected_jngBizCrtraYr"
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
            "selected_jngBizCrtraYr"
        ]
    ]
    .copy()
)


print(
    "최신 지역현황 행 :",
    len(latest_region_df)
)


print()
print(
    "사용 조회연도 분포"
)

print(
    latest_region_df[
        "selected_jngBizCrtraYr"
    ]
    .value_counts()
    .sort_index(
        ascending=False
    )
)


# ============================================================
# 7. 조회연도 선택 사유 생성
# ============================================================

def make_year_source(year):

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
        "selected_jngBizCrtraYr"
    ]
    .apply(
        make_year_source
    )
)


# ============================================================
# 8. 전국 행 / 지역 행 분리
# ============================================================

national_region_df = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ] == "전체"
    ]
    .copy()
)


region_by_area = (
    latest_region_df[
        latest_region_df[
            "areaNm"
        ] != "전체"
    ]
    .copy()
)


# ============================================================
# 9. 공식 지역현황 컬럼 선택
# ============================================================

official_region = (
    region_by_area[
        [
            "brandMnno",

            "jngBizCrtraYr",
            "acntgYr",

            "selected_jngBizCrtraYr",
            "region_year_source",

            "indutyLclasNm",
            "indutyMlsfcNm",

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
# 10. 전남 + 광주 통합 비교값 생성
# ============================================================
#
# 예:
#
# 상가정보
# 전남광주통합특별시
#
# 공식 지역현황
# 광주 + 전남
#
# 비교용으로만 합친다.
# ============================================================

south_gwangju = (
    official_region[
        official_region[
            "normalized_region"
        ].isin(
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

            "selected_jngBizCrtraYr",
            "region_year_source",

            "indutyLclasNm",
            "indutyMlsfcNm"
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
# 11. 2차 매칭된 상가만 추출
# ============================================================

matched_only_df = (
    match_df[
        match_df[
            "brandMnno"
        ].notna()
    ]
    .copy()
)


print()
print(
    "2차 브랜드 매칭 데이터 :",
    len(matched_only_df)
)


# ============================================================
# 12. 상가정보 브랜드 + 지역별 개수 집계
# ============================================================

shop_region_count = (
    matched_only_df
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
            x.isin(
                [
                    "contains",
                    "contains_longest"
                ]
            ).sum()
        )

    )
    .reset_index()
)


print(
    "상가정보 브랜드+지역 조합 :",
    len(shop_region_count)
)


# ============================================================
# 13. 상가정보 + 공식지역현황 연결
# ============================================================

print()
print("========================================")
print("4. 지역현황 매칭")
print("========================================")


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


print(
    "지역 비교 행 :",
    len(validation_df)
)


print(
    "공식 지역현황 연결 성공 :",
    validation_df[
        "official_total_count"
    ]
    .notna()
    .sum()
)


# ============================================================
# 14. 숫자 변환
# ============================================================

validation_number_cols = [
    "shop_store_count",
    "official_franchise_count",
    "official_direct_count",
    "official_total_count"
]


for col in validation_number_cols:

    validation_df[
        col
    ] = pd.to_numeric(
        validation_df[
            col
        ],
        errors="coerce"
    )


# ============================================================
# 15. 차이 계산
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


# ============================================================
# 16. 비율 계산
# ============================================================

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
# 17. 4차 지역검증 판정
# ============================================================
#
# 3차와 차이점:
#
# 공식매장 0인 경우
#
# 상가 1~2 → 신규가능성
# 상가 3~5 → 검토필요
# 상가 6+  → 강한검토필요
# ============================================================

def region_validation_status(row):

    shop_count = row[
        "shop_store_count"
    ]

    official_count = row[
        "official_total_count"
    ]

    ratio = row[
        "shop_official_ratio"
    ]


    # --------------------------------------------------------
    # 공식 지역정보가 없음
    # --------------------------------------------------------

    if pd.isna(
        official_count
    ):
        return "공식지역정보없음"


    # --------------------------------------------------------
    # 공식 0
    # --------------------------------------------------------

    if official_count == 0:

        if shop_count == 0:
            return "일치"

        if shop_count <= 2:
            return "신규가능성"

        if shop_count <= 5:
            return "검토필요"

        return "강한검토필요"


    # --------------------------------------------------------
    # 공식 매장 존재
    # --------------------------------------------------------

    if pd.isna(ratio):
        return "검토필요"


    # 50% ~ 150%
    if (
        ratio >= 0.5
        and
        ratio <= 1.5
    ):
        return "양호"


    # 20% ~ 200%
    if (
        ratio >= 0.2
        and
        ratio <= 2.0
    ):
        return "유력"


    # 공식보다 지나치게 많음
    if ratio > 2.0:
        return "과다매칭검토"


    # 공식 대비 너무 적게 발견
    if ratio < 0.2:
        return "누락가능성"


    return "검토필요"


validation_df[
    "region_validation"
] = (
    validation_df.apply(
        region_validation_status,
        axis=1
    )
)


# ============================================================
# 18. 지역 검증 점수
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
# 19. 브랜드별 지역검증 요약
# ============================================================

brand_validation_summary = (
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
# 20. 브랜드별 사용 공식연도 확인
# ============================================================

brand_year_info = (
    validation_df[
        [
            "brandMnno",
            "selected_jngBizCrtraYr",
            "acntgYr",
            "region_year_source"
        ]
    ]
    .drop_duplicates(
        subset=[
            "brandMnno"
        ]
    )
)


brand_validation_summary = (
    brand_validation_summary
    .merge(
        brand_year_info,
        on="brandMnno",
        how="left"
    )
)


# ============================================================
# 21. 브랜드 지역 신뢰도 판정
# ============================================================

def brand_validation_status(row):

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


    # --------------------------------------------------------
    # 우수
    # --------------------------------------------------------

    if (
        good >= 3
        and
        review == 0
        and
        score >= 6
    ):
        return "지역검증우수"


    # --------------------------------------------------------
    # 유력
    # 신규가능성은 패널티로 보지 않음
    # --------------------------------------------------------

    if (
        good >= 1
        and
        score > 0
        and
        review == 0
    ):
        return "지역검증유력"


    # --------------------------------------------------------
    # 일부 검토 필요
    # --------------------------------------------------------

    if review >= 1:
        return "지역검토필요"


    # --------------------------------------------------------
    # 공식 지역정보 부족
    # --------------------------------------------------------

    if (
        no_info > 0
        and
        good == 0
    ):
        return "공식정보부족"


    # --------------------------------------------------------

    if new_possible > 0:
        return "신규가능성포함"


    return "정보부족"


brand_validation_summary[
    "brand_region_status"
] = (
    brand_validation_summary
    .apply(
        brand_validation_status,
        axis=1
    )
)


# ============================================================
# 22. 전국 공식 매장 수 추출
# ============================================================

national_official = (
    national_region_df[
        [
            "brandMnno",

            "selected_jngBizCrtraYr",
            "acntgYr",
            "region_year_source",

            "frcsCnt",
            "dmsCnt",
            "allFrcsDmsCnt"
        ]
    ]
    .copy()
)


national_official = (
    national_official
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


# ============================================================
# 23. 상가정보 전국 발견 개수
# ============================================================

national_shop = (
    matched_only_df
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


# ============================================================
# 24. 전국 비교
# ============================================================

national_compare = (
    national_shop
    .merge(
        national_official,
        on="brandMnno",
        how="left"
    )
)


national_compare[
    "national_difference"
] = (
    national_compare[
        "national_shop_count"
    ]
    -
    national_compare[
        "national_official_total"
    ]
)


national_compare[
    "national_ratio"
] = np.where(

    national_compare[
        "national_official_total"
    ] > 0,

    (
        national_compare[
            "national_shop_count"
        ]
        /
        national_compare[
            "national_official_total"
        ]
    ),

    np.nan
)


# ============================================================
# 25. 개별 상가에 브랜드 지역결과 연결
# ============================================================

match_df = (
    match_df
    .merge(

        brand_validation_summary[
            [
                "brandMnno",

                "brand_region_status",

                "region_score_sum",

                "good_region_count",

                "new_possible_count",

                "review_region_count",

                "no_official_info_count",

                "selected_jngBizCrtraYr",

                "acntgYr",

                "region_year_source"
            ]
        ],

        on="brandMnno",

        how="left"
    )
)


# ============================================================
# 26. 최종 4차 판정
# ============================================================

def final_validation_status(row):

    name_status = row[
        "match_status"
    ]

    region_status = row[
        "brand_region_status"
    ]


    # --------------------------------------------------------
    # 정확일치
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 포함일치
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 2차부터 검토필요
    # --------------------------------------------------------

    if name_status == "검토필요":
        return "검토필요"


    # --------------------------------------------------------

    return "정보부족"


match_df[
    "final_match_status"
] = (
    match_df.apply(
        final_validation_status,
        axis=1
    )
)


# ============================================================
# 27. 최종 신뢰도 점수
# ============================================================
#
# 프로젝트 내부 분석용 점수
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


match_df[
    "final_score"
] = (
    match_df[
        "final_match_status"
    ]
    .map(
        FINAL_SCORE_MAP
    )
    .fillna(0)
)


# ============================================================
# 28. 최종 데이터 분리
# ============================================================

confirmed_df = (
    match_df[
        match_df[
            "final_match_status"
        ].isin(
            [
                "확정",
                "확정유력"
            ]
        )
    ]
    .copy()
)


likely_df = (
    match_df[
        match_df[
            "final_match_status"
        ].isin(
            [
                "유력",
                "후보"
            ]
        )
    ]
    .copy()
)


review_df = (
    match_df[
        match_df[
            "final_match_status"
        ] == "검토필요"
    ]
    .copy()
)


no_info_df = (
    match_df[
        match_df[
            "final_match_status"
        ] == "공식정보부족"
    ]
    .copy()
)


# ============================================================
# 29. 최종 프랜차이즈 활용 후보
# ============================================================
#
# 현재 프로젝트에서는
#
# 확정 / 확정유력 / 유력
#
# 까지만 우선 활용 권장
#
# 후보는 별도 검토 후 사용
# ============================================================

project_ready_df = (
    match_df[
        match_df[
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


# ============================================================
# 30. 분석요약 생성
# ============================================================

summary_df = pd.DataFrame(
    {

        "항목": [

            "전체 상가",

            "2차 브랜드 매칭",

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

            len(match_df),

            match_df[
                "brandMnno"
            ]
            .notna()
            .sum(),

            (
                match_df[
                    "final_match_status"
                ] == "확정"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ] == "확정유력"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ] == "유력"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ] == "후보"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ] == "검토필요"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ] == "공식정보부족"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ] == "정보부족"
            ).sum(),

            len(
                project_ready_df
            ),

            len(
                brand_validation_summary
            )
        ]
    }
)


# ============================================================
# 31. 콘솔 출력
# ============================================================

print()
print("========================================")
print("5. 4차 최종 지역검증 결과")
print("========================================")

print(
    summary_df.to_string(
        index=False
    )
)


print()
print("========================================")
print("지역별 검증 상태")
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
print("브랜드 지역검증 상태")
print("========================================")

print(
    brand_validation_summary[
        "brand_region_status"
    ]
    .value_counts(
        dropna=False
    )
)


print()
print("========================================")
print("사용 공식연도")
print("========================================")

print(
    brand_validation_summary[
        "selected_jngBizCrtraYr"
    ]
    .value_counts(
        dropna=False
    )
    .sort_index(
        ascending=False
    )
)


# ============================================================
# 32. 엑셀 저장
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


    match_df.to_excel(
        writer,
        sheet_name="전체4차결과",
        index=False
    )


    validation_df.to_excel(
        writer,
        sheet_name="지역별검증",
        index=False
    )


    brand_validation_summary.to_excel(
        writer,
        sheet_name="브랜드지역요약",
        index=False
    )


    national_compare.to_excel(
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