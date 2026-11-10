import pandas as pd
import json
from pathlib import Path
import numpy as np


# ============================================================
# 0. 경로 설정
# ============================================================

# 2차 자동매칭 결과
MATCH_FILE = Path(
    r"C:\workspace\fcha_data\output\franchise_matching\교육서비스업_프랜차이즈_2차자동매칭.xlsx"
)

# 브랜드 지역현황 가공 JSON
REGION_FILE = Path(
    r"C:\workspace\fcha_data\data\브랜드지역현황_v5\processed\brand_region_raw.json"
)

# 결과 폴더
OUTPUT_DIR = Path(
    r"C:\workspace\fcha_data\output\franchise_matching"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT_FILE = (
    OUTPUT_DIR
    / "교육서비스업_프랜차이즈_3차지역검증.xlsx"
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

print(
    "전체 상가 :",
    len(match_df)
)

print(
    "brandMnno 존재 :",
    match_df["brandMnno"].notna().sum()
)


# ============================================================
# 2. 지역현황 JSON 읽기
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
# 3. 지역현황 최신 자료 선택
# ============================================================
#
# 현재 데이터 구조:
#
# jngBizCrtraYr 2024 -> acntgYr 2023
# jngBizCrtraYr 2025 -> acntgYr 2024
# jngBizCrtraYr 2026 -> acntgYr 2025
#
# 따라서 가장 최신인
# jngBizCrtraYr = 2026을 우선 사용
# ============================================================

LATEST_YEAR = "2026"


latest_region_df = region_df[
    region_df[
        "jngBizCrtraYr"
    ].astype(str)
    == LATEST_YEAR
].copy()


print(
    "2026 조회기준 지역현황 :",
    len(latest_region_df)
)

print(
    "실제 회계연도 :",
    latest_region_df[
        "acntgYr"
    ]
    .dropna()
    .unique()
)


# ============================================================
# 4. 전체 지역 행 제외
# ============================================================
#
# areaNm = 전체
#
# 는 시도별 비교에 사용하지 않는다.
# 전국 합계 검증에서 따로 사용
# ============================================================

region_by_area = latest_region_df[
    latest_region_df[
        "areaNm"
    ] != "전체"
].copy()


national_region_df = latest_region_df[
    latest_region_df[
        "areaNm"
    ] == "전체"
].copy()


# ============================================================
# 5. 지역명 정규화
# ============================================================
#
# 공정위 지역현황:
#
# 서울 / 부산 / 경기 / 전남 ...
#
# 전국상가정보:
#
# 서울특별시
# 부산광역시
# 경기도
# ...
#
# 형태가 다르므로 비교용 지역명을 만든다.
#
# 원본 지역명은 변경하지 않는다.
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


# ============================================================
# 6. 전남광주통합특별시 처리
# ============================================================
#
# 전국상가정보가 2026 행정구역명을 사용하지만
# 공정위 최신 지역현황은 acntgYr = 2025이므로
#
# 광주 + 전남
#
# 으로 나뉘어 있다.
#
# 따라서 통합특별시는 별도 그룹으로 만들어
# 공정위 광주+전남 합계와 비교한다.
# ============================================================

def normalize_shop_region(region):

    if pd.isna(region):
        return None

    region = str(region).strip()

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


# 공정위 지역명은 이미 축약형
region_by_area[
    "normalized_region"
] = (
    region_by_area[
        "areaNm"
    ]
)


# ============================================================
# 7. 전국상가정보 브랜드 + 지역별 매장 수 계산
# ============================================================

print()
print("========================================")
print("3. 상가정보 지역별 매장 수 계산")
print("========================================")


matched_only_df = match_df[
    match_df[
        "brandMnno"
    ].notna()
].copy()


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
# 8. 공정위 지역현황 필요한 컬럼 선택
# ============================================================

official_region = region_by_area[
    [
        "jngBizCrtraYr",
        "acntgYr",
        "brandMnno",
        "indutyLclasNm",
        "indutyMlsfcNm",
        "normalized_region",
        "frcsCnt",
        "dmsCnt",
        "allFrcsDmsCnt"
    ]
].copy()


official_region = official_region.rename(
    columns={
        "frcsCnt":
        "official_franchise_count",

        "dmsCnt":
        "official_direct_count",

        "allFrcsDmsCnt":
        "official_total_count"
    }
)


# ============================================================
# 9. 전남 + 광주 공식 데이터 합산 생성
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


official_region = pd.concat(
    [
        official_region,
        south_gwangju
    ],
    ignore_index=True
)


# ============================================================
# 10. 상가정보 + 공식 지역현황 연결
# ============================================================

print()
print("========================================")
print("4. 지역현황 매칭")
print("========================================")


validation_df = shop_region_count.merge(

    official_region,

    on=[
        "brandMnno",
        "normalized_region"
    ],

    how="left"
)


print(
    "지역 비교 행 :",
    len(validation_df)
)


print(
    "공식 지역현황 연결 성공 :",
    validation_df[
        "official_total_count"
    ].notna().sum()
)


# ============================================================
# 11. 숫자 타입 정리
# ============================================================

number_cols = [
    "shop_store_count",
    "official_franchise_count",
    "official_direct_count",
    "official_total_count",
]


for col in number_cols:

    validation_df[
        col
    ] = pd.to_numeric(
        validation_df[
            col
        ],
        errors="coerce"
    )


# ============================================================
# 12. 차이 계산
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
# 13. 상가정보 / 공식매장 비율 계산
# ============================================================
#
# 공식 매장수가 0이면 나눗셈하지 않는다.
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
# 14. 지역 검증 상태 결정
# ============================================================
#
# 숫자가 정확히 같아야만 정상이라고 판단하지 않는다.
#
# 전국상가정보와 공정위 자료의 기준 시점,
# 등록 방식 등이 다르기 때문이다.
#
# 비율을 참고 지표로 사용한다.
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


    # --------------------------------------------
    # 공식 데이터 자체가 없음
    # --------------------------------------------

    if pd.isna(
        official_count
    ):
        return "공식지역정보없음"


    # --------------------------------------------
    # 공정위 공식 매장이 0인데
    # 상가정보에서 매칭된 경우
    # --------------------------------------------

    if (
        official_count == 0
        and
        shop_count > 0
    ):
        return "강한검토필요"


    # --------------------------------------------
    # 둘 다 0
    # --------------------------------------------

    if (
        official_count == 0
        and
        shop_count == 0
    ):
        return "일치"


    # --------------------------------------------
    # 공식 매장수 대비
    # 상가정보 매칭 수 비율
    #
    # 50% ~ 150%
    # --------------------------------------------

    if (
        ratio >= 0.5
        and
        ratio <= 1.5
    ):
        return "양호"


    # --------------------------------------------
    # 20% ~ 200%
    # --------------------------------------------

    if (
        ratio >= 0.2
        and
        ratio <= 2.0
    ):
        return "유력"


    # --------------------------------------------
    # 상가정보가 공식 매장 수보다
    # 지나치게 많이 잡힌 경우
    # --------------------------------------------

    if ratio > 2.0:
        return "과다매칭검토"


    # --------------------------------------------
    # 공식매장은 있는데
    # 너무 적게 발견된 경우
    # --------------------------------------------

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
# 15. 지역 검증 점수 생성
# ============================================================
#
# 최종 확정이 아니라
# 검토 우선순위를 잡기 위한 점수
# ============================================================

REGION_SCORE_MAP = {

    "일치": 3,

    "양호": 3,

    "유력": 2,

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
# 16. 브랜드별 지역 검증 요약
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

        review_region_count=(
            "region_validation",
            lambda x:
            x.isin(
                [
                    "과다매칭검토",
                    "강한검토필요",
                    "검토필요"
                ]
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
# 17. 브랜드 신뢰도 판정
# ============================================================

def brand_validation_status(row):

    good = row[
        "good_region_count"
    ]

    review = row[
        "review_region_count"
    ]

    score = row[
        "region_score_sum"
    ]


    # --------------------------------------------
    # 지역 일치가 충분하고
    # 위험지역이 없음
    # --------------------------------------------

    if (
        good >= 3
        and
        review == 0
        and
        score >= 6
    ):
        return "지역검증우수"


    # --------------------------------------------

    if (
        good >= 1
        and
        score > 0
    ):
        return "지역검증유력"


    # --------------------------------------------

    if review >= 1:
        return "지역검토필요"


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
# 18. 전국 단위 공식 매장 수 추가
# ============================================================

national_official = (
    national_region_df[
        [
            "brandMnno",
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


# 상가정보 브랜드별 전국 발견 개수
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
# 19. 상가 개별 데이터에 브랜드 지역판정 붙이기
# ============================================================

match_df = match_df.merge(

    brand_validation_summary[
        [
            "brandMnno",
            "brand_region_status",
            "region_score_sum",
            "good_region_count",
            "review_region_count"
        ]
    ],

    on="brandMnno",

    how="left"
)


# ============================================================
# 20. 최종 3차 등급
# ============================================================
#
# 기존 이름매칭 신뢰도
# +
# 지역현황 검증
#
# 둘을 같이 사용한다.
# ============================================================

def final_validation_status(row):

    name_status = row[
        "match_status"
    ]

    region_status = row[
        "brand_region_status"
    ]


    # 정확일치 + 지역검증 우수
    if (
        name_status == "자동확정"
        and
        region_status == "지역검증우수"
    ):
        return "확정"


    # 정확일치 + 지역검증 유력
    if (
        name_status == "자동확정"
        and
        region_status == "지역검증유력"
    ):
        return "확정유력"


    # 포함매칭 + 지역검증 우수
    if (
        name_status == "프랜차이즈후보"
        and
        region_status == "지역검증우수"
    ):
        return "유력"


    # 포함매칭 + 지역검증 유력
    if (
        name_status == "프랜차이즈후보"
        and
        region_status == "지역검증유력"
    ):
        return "후보"


    # 지역에서 문제 발생
    if (
        region_status == "지역검토필요"
    ):
        return "검토필요"


    # 이름 단계에서도 이미 검토필요
    if (
        name_status == "검토필요"
    ):
        return "검토필요"


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
# 21. 최종 분류
# ============================================================

confirmed_df = match_df[
    match_df[
        "final_match_status"
    ].isin(
        [
            "확정",
            "확정유력"
        ]
    )
].copy()


likely_df = match_df[
    match_df[
        "final_match_status"
    ].isin(
        [
            "유력",
            "후보"
        ]
    )
].copy()


review_final_df = match_df[
    match_df[
        "final_match_status"
    ] == "검토필요"
].copy()


# ============================================================
# 22. 분석 요약
# ============================================================

summary_df = pd.DataFrame(
    {
        "항목": [

            "전체 상가",

            "2차 브랜드 매칭 존재",

            "확정",

            "확정유력",

            "유력",

            "후보",

            "검토필요",

            "정보부족",

            "지역검증 브랜드 수"
        ],

        "건수": [

            len(match_df),

            match_df[
                "brandMnno"
            ].notna().sum(),

            (
                match_df[
                    "final_match_status"
                ]
                == "확정"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ]
                == "확정유력"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ]
                == "유력"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ]
                == "후보"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ]
                == "검토필요"
            ).sum(),

            (
                match_df[
                    "final_match_status"
                ]
                == "정보부족"
            ).sum(),

            len(
                brand_validation_summary
            )
        ]
    }
)


# ============================================================
# 23. 결과 출력
# ============================================================

print()
print("========================================")
print("5. 3차 지역검증 결과")
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
    brand_validation_summary[
        "brand_region_status"
    ]
    .value_counts(
        dropna=False
    )
)


# ============================================================
# 24. 엑셀 저장
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
        sheet_name="전체3차결과",
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


    review_final_df.to_excel(
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