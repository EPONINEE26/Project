import pandas as pd
import re
from pathlib import Path


# ============================================================
# 0. 파일 경로
# ============================================================

INPUT_FILE = Path(
    r"C:\workspace\fcha_data\output\franchise_matching\예술스포츠여가서비스업_프랜차이즈_최종매칭_v2.xlsx"
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
    / "예술스포츠여가서비스업_프랜차이즈_엄격최종본.xlsx"
)


# ============================================================
# 1. 문자열 정리 함수
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

    # 한글 / 영문 / 숫자를 제외한 특수문자 제거
    name = re.sub(
        r"[^가-힣A-Z0-9]",
        "",
        name
    )

    return name


# ============================================================
# 2. 기존 최종매칭 파일 읽기
# ============================================================

print()
print("========================================")
print("1. 기존 최종매칭 파일 읽기")
print("========================================")

df = pd.read_excel(
    INPUT_FILE,
    sheet_name="전체매칭결과"
)

print(
    "전체 데이터 :",
    len(df)
)


# ============================================================
# 3. 비교용 브랜드명 다시 정리
# ============================================================

df[
    "cleaned_matched_brand"
] = (
    df[
        "matched_brandNm"
    ]
    .apply(
        clean_name
    )
)


# 기존 상호명 정리 컬럼이 없을 경우 다시 생성
if (
    "cleaned_store_name"
    not in df.columns
):

    df[
        "cleaned_store_name"
    ] = (
        df[
            "bizesNm"
        ]
        .apply(
            clean_name
        )
    )


# ============================================================
# 4. 브랜드명 길이
# ============================================================

df[
    "matched_brand_length"
] = (
    df[
        "cleaned_matched_brand"
    ]
    .str.len()
)


# ============================================================
# 5. 정확 일치 여부
# ============================================================

df[
    "strict_exact_match"
] = (
    (
        df[
            "cleaned_store_name"
        ]
        ==
        df[
            "cleaned_matched_brand"
        ]
    )
    &
    (
        df[
            "cleaned_matched_brand"
        ] != ""
    )
)


# ============================================================
# 6. 브랜드명으로 상호명이 시작하는지 확인
# ============================================================

def check_prefix(row):

    store_name = row[
        "cleaned_store_name"
    ]

    brand_name = row[
        "cleaned_matched_brand"
    ]


    if pd.isna(store_name):
        return False

    if pd.isna(brand_name):
        return False

    if brand_name == "":
        return False

    return str(
        store_name
    ).startswith(
        str(
            brand_name
        )
    )


df[
    "strict_prefix_match"
] = (
    df.apply(
        check_prefix,
        axis=1
    )
)


# ============================================================
# 7. 중간 포함 매칭 여부
# ============================================================
#
# 브랜드명이 상호 중간에만 들어간 경우
#
# 예:
#
# 순수노래연습장
# 공식브랜드: 수노래연습장
#
# contains는 되지만 prefix는 안 됨
#
# → 제외 대상으로 판단
# ============================================================

df[
    "middle_contains_only"
] = (
    (
        df[
            "match_type"
        ]
        == "contains"
    )
    &
    (
        df[
            "strict_prefix_match"
        ]
        == False
    )
)


# ============================================================
# 8. 너무 짧은 브랜드명 여부
# ============================================================
#
# 2글자 이하 브랜드명은 오탐 가능성이 매우 높으므로 제외
#
# 3글자 브랜드명도 contains만으로는 불안하므로
# prefix + 지역검증우수일 때만 허용
# ============================================================

df[
    "very_short_brand"
] = (
    df[
        "matched_brand_length"
    ]
    <= 2
)


df[
    "short_brand"
] = (
    df[
        "matched_brand_length"
    ]
    == 3
)


# ============================================================
# 9. 지역검증 상태
# ============================================================

GOOD_REGION_STATUS = [
    "지역검증우수",
    "지역검증유력",
]


VERY_GOOD_REGION_STATUS = [
    "지역검증우수",
]


# ============================================================
# 10. 정확 일치 확정 조건
# ============================================================
#
# 브랜드명 == 상호명
#
# +
#
# 지역검증 우수 또는 유력
# +
# 검토지역 없음
# +
# 공식정보 부족 없음
# ============================================================

exact_confirmed = (

    (
        df[
            "strict_exact_match"
        ]
        == True
    )

    &

    (
        df[
            "brand_region_status"
        ]
        .isin(
            GOOD_REGION_STATUS
        )
    )

    &

    (
        df[
            "review_region_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        df[
            "no_official_info_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        df[
            "match_type"
        ]
        != "duplicate_brand_name"
    )
)


# ============================================================
# 11. 브랜드명 PREFIX 매칭 조건
# ============================================================
#
# 예:
#
# 세븐스타코인노래연습장전주
# → 세븐스타코인노래연습장
#
# 작심스터디카페구미
# → 작심스터디카페
#
# 이런 형태
#
# 지역검증은 "우수"만 허용
# ============================================================

prefix_confirmed = (

    (
        df[
            "strict_prefix_match"
        ]
        == True
    )

    &

    (
        df[
            "strict_exact_match"
        ]
        == False
    )

    &

    (
        df[
            "brand_region_status"
        ]
        .isin(
            VERY_GOOD_REGION_STATUS
        )
    )

    &

    (
        df[
            "review_region_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        df[
            "no_official_info_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        df[
            "match_type"
        ]
        == "contains"
    )

    &

    (
        df[
            "very_short_brand"
        ]
        == False
    )
)


# ============================================================
# 12. 3글자 브랜드는 더 엄격하게
# ============================================================
#
# 3글자 브랜드는
#
# PREFIX
# +
# 지역검증우수
# +
# 최소 2개 이상의 양호 지역
#
# 모두 필요
# ============================================================

short_brand_confirmed = (

    (
        df[
            "short_brand"
        ]
        == True
    )

    &

    (
        df[
            "strict_prefix_match"
        ]
        == True
    )

    &

    (
        df[
            "brand_region_status"
        ]
        == "지역검증우수"
    )

    &

    (
        df[
            "good_region_count"
        ]
        .fillna(0)
        >= 2
    )

    &

    (
        df[
            "review_region_count"
        ]
        .fillna(0)
        == 0
    )

    &

    (
        df[
            "no_official_info_count"
        ]
        .fillna(0)
        == 0
    )
)


# ============================================================
# 13. PREFIX 조건에서 3글자 브랜드 제거
# ============================================================
#
# 3글자는 위의 short_brand_confirmed 조건만 사용
# ============================================================

prefix_confirmed = (

    prefix_confirmed

    &

    (
        df[
            "short_brand"
        ]
        == False
    )
)


# ============================================================
# 14. 최종 엄격 확정 여부
# ============================================================

df[
    "strict_confirmed"
] = (

    exact_confirmed

    |

    prefix_confirmed

    |

    short_brand_confirmed
)


# ============================================================
# 15. 확정 방식 표시
# ============================================================

def strict_match_reason(row):

    if row[
        "strict_confirmed"
    ] == False:

        return "제외"


    if row[
        "strict_exact_match"
    ]:

        return "정확일치+지역검증"


    if (
        row[
            "short_brand"
        ]
        and
        row[
            "strict_prefix_match"
        ]
    ):

        return "3글자PREFIX+강한지역검증"


    if row[
        "strict_prefix_match"
    ]:

        return "PREFIX+지역검증우수"


    return "기타확정"


df[
    "strict_reason"
] = (
    df.apply(
        strict_match_reason,
        axis=1
    )
)


# ============================================================
# 16. 제외 사유
# ============================================================

def exclude_reason(row):

    if row[
        "strict_confirmed"
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
            "match_type"
        ]
        == "duplicate_brand_name"
    ):
        return "중복브랜드명"


    if row[
        "very_short_brand"
    ]:
        return "브랜드명너무짧음"


    if row[
        "middle_contains_only"
    ]:
        return "중간문자열포함"


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
            "review_region_count"
        ]
        > 0
    ):
        return "검토지역존재"


    if (
        row[
            "no_official_info_count"
        ]
        > 0
    ):
        return "지역공식정보부족"


    if (
        row[
            "brand_region_status"
        ]
        == "신규가능성포함"
    ):
        return "신규가능성만존재"


    return "엄격기준미충족"


df[
    "exclude_reason"
] = (
    df.apply(
        exclude_reason,
        axis=1
    )
)


# ============================================================
# 17. 프로젝트 최종 사용 데이터
# ============================================================

strict_final_df = (
    df[
        df[
            "strict_confirmed"
        ]
        == True
    ]
    .copy()
)


# ============================================================
# 18. 제외 데이터
# ============================================================

excluded_df = (
    df[
        df[
            "strict_confirmed"
        ]
        == False
    ]
    .copy()
)


# ============================================================
# 19. 브랜드별 최종 매장 수
# ============================================================

brand_summary_df = (
    strict_final_df
    .groupby(
        [
            "brandMnno",
            "matched_brandNm",
            "matched_brand_industry"
        ],
        dropna=False
    )
    .agg(

        final_store_count=(
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

        exact_store_count=(
            "strict_reason",
            lambda x:
            (
                x
                == "정확일치+지역검증"
            ).sum()
        ),

        prefix_store_count=(
            "strict_reason",
            lambda x:
            x.isin(
                [
                    "PREFIX+지역검증우수",
                    "3글자PREFIX+강한지역검증"
                ]
            ).sum()
        )

    )
    .reset_index()
    .sort_values(
        "final_store_count",
        ascending=False
    )
)


# ============================================================
# 20. 지역별 최종 매장 수
# ============================================================

region_summary_df = (
    strict_final_df
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
# 21. 제외 사유 요약
# ============================================================

exclude_summary_df = (
    excluded_df[
        "exclude_reason"
    ]
    .value_counts(
        dropna=False
    )
    .reset_index()
)

exclude_summary_df.columns = [
    "제외사유",
    "건수"
]


# ============================================================
# 22. 최종 분석 요약
# ============================================================

summary_df = pd.DataFrame(
    {
        "항목": [

            "전체 상가",

            "기존 브랜드 매칭",

            "엄격 최종 확정",

            "정확일치 확정",

            "PREFIX 확정",

            "3글자 PREFIX 확정",

            "최종 브랜드 수",

            "제외 데이터"

        ],

        "건수": [

            len(df),

            df[
                "brandMnno"
            ]
            .notna()
            .sum(),

            len(
                strict_final_df
            ),

            (
                strict_final_df[
                    "strict_reason"
                ]
                == "정확일치+지역검증"
            ).sum(),

            (
                strict_final_df[
                    "strict_reason"
                ]
                == "PREFIX+지역검증우수"
            ).sum(),

            (
                strict_final_df[
                    "strict_reason"
                ]
                == "3글자PREFIX+강한지역검증"
            ).sum(),

            strict_final_df[
                "brandMnno"
            ]
            .nunique(),

            len(
                excluded_df
            )
        ]
    }
)


# ============================================================
# 23. 콘솔 출력
# ============================================================

print()
print("========================================")
print("엄격 최종 매칭 결과")
print("========================================")

print(
    summary_df.to_string(
        index=False
    )
)


print()
print("========================================")
print("제외 사유")
print("========================================")

print(
    exclude_summary_df.to_string(
        index=False
    )
)


print()
print("========================================")
print("최종 브랜드 TOP 30")
print("========================================")

print(
    brand_summary_df.head(
        30
    ).to_string(
        index=False
    )
)


# ============================================================
# 24. 엑셀 저장
# ============================================================

print()
print("========================================")
print("엑셀 저장")
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


    strict_final_df.to_excel(
        writer,
        sheet_name="최종확정매장",
        index=False
    )


    brand_summary_df.to_excel(
        writer,
        sheet_name="최종브랜드요약",
        index=False
    )


    region_summary_df.to_excel(
        writer,
        sheet_name="최종지역별요약",
        index=False
    )


    exclude_summary_df.to_excel(
        writer,
        sheet_name="제외사유요약",
        index=False
    )


    excluded_df.to_excel(
        writer,
        sheet_name="제외데이터",
        index=False
    )


print()
print("========================================")
print("저장 완료")
print("========================================")

print(
    OUTPUT_FILE
)