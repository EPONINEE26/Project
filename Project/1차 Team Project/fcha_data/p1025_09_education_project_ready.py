import pandas as pd
import re
from pathlib import Path


# ============================================================
# 0. 경로 설정
# ============================================================

INPUT_FILE = Path(
    r"C:\workspace\fcha_data\output\franchise_matching\교육서비스업_프랜차이즈_4차최종지역검증.xlsx"
)

OUTPUT_DIR = Path(
    r"C:\workspace\fcha_data\output\project_ready"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


OUTPUT_FILE = (
    OUTPUT_DIR
    / "교육서비스업_프로젝트실제투입본.xlsx"
)


HOLD_CSV_FILE = (
    OUTPUT_DIR
    / "교육서비스업_보류후보.csv"
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

    # 특수문자 제거
    name = re.sub(
        r"[^가-힣A-Z0-9]",
        "",
        name
    )

    return name


# ============================================================
# 2. 교육서비스업 4차 최종본 읽기
# ============================================================

print()
print("========================================")
print("1. 교육서비스업 4차 최종본 읽기")
print("========================================")


df = pd.read_excel(
    INPUT_FILE,
    sheet_name="전체4차결과"
)


print(
    "전체 데이터 :",
    len(df)
)


print(
    "브랜드 ID 존재 :",
    df[
        "brandMnno"
    ]
    .notna()
    .sum()
)


# ============================================================
# 3. 비교용 이름 정리
# ============================================================

df[
    "project_clean_brand"
] = (
    df[
        "matched_brandNm"
    ]
    .apply(
        clean_name
    )
)


if (
    "cleaned_store_name"
    in df.columns
):

    df[
        "project_clean_store"
    ] = (
        df[
            "cleaned_store_name"
        ]
        .fillna("")
        .astype(str)
    )

else:

    df[
        "project_clean_store"
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
    "project_brand_length"
] = (
    df[
        "project_clean_brand"
    ]
    .str.len()
)


# ============================================================
# 5. 정확 일치
# ============================================================

df[
    "project_exact"
] = (
    (
        df[
            "project_clean_store"
        ]
        ==
        df[
            "project_clean_brand"
        ]
    )
    &
    (
        df[
            "project_clean_brand"
        ]
        != ""
    )
)


# ============================================================
# 6. PREFIX 여부
# ============================================================

def check_prefix(row):

    store_name = row[
        "project_clean_store"
    ]

    brand_name = row[
        "project_clean_brand"
    ]

    if not store_name:
        return False

    if not brand_name:
        return False

    return str(
        store_name
    ).startswith(
        str(
            brand_name
        )
    )


df[
    "project_prefix"
] = (
    df.apply(
        check_prefix,
        axis=1
    )
)


# ============================================================
# 7. 지역 검증 안전성
# ============================================================

df[
    "project_region_safe"
] = (
    df[
        "brand_region_status"
    ]
    == "지역검증우수"
)


df[
    "project_no_review_region"
] = (
    df[
        "review_region_count"
    ]
    .fillna(0)
    == 0
)


df[
    "project_has_official_info"
] = (
    df[
        "no_official_info_count"
    ]
    .fillna(0)
    == 0
)


# ============================================================
# 8. 실제 투입 조건 - 정확 일치
# ============================================================

condition_exact = (

    (
        df[
            "project_exact"
        ]
        == True
    )

    &

    (
        df[
            "project_region_safe"
        ]
        == True
    )

    &

    (
        df[
            "project_no_review_region"
        ]
        == True
    )

    &

    (
        df[
            "project_has_official_info"
        ]
        == True
    )
)


# ============================================================
# 9. 실제 투입 조건 - PREFIX
# ============================================================
#
# 브랜드명으로 상호명이 시작
#
# 단,
# 브랜드명은 최소 4글자 이상
#
# ============================================================

condition_prefix = (

    (
        df[
            "project_exact"
        ]
        == False
    )

    &

    (
        df[
            "project_prefix"
        ]
        == True
    )

    &

    (
        df[
            "project_brand_length"
        ]
        >= 4
    )

    &

    (
        df[
            "project_region_safe"
        ]
        == True
    )

    &

    (
        df[
            "project_no_review_region"
        ]
        == True
    )

    &

    (
        df[
            "project_has_official_info"
        ]
        == True
    )
)


# ============================================================
# 10. 프로젝트 실제 투입 여부
# ============================================================

df[
    "project_ready"
] = (
    condition_exact
    |
    condition_prefix
)


# ============================================================
# 11. 프로젝트 투입 근거
# ============================================================

def project_reason(row):

    if not row[
        "project_ready"
    ]:
        return None


    if row[
        "project_exact"
    ]:

        return "공식브랜드정확일치+지역검증우수"


    if (
        row[
            "project_prefix"
        ]
        and
        row[
            "project_brand_length"
        ]
        >= 4
    ):

        return "4글자이상PREFIX+지역검증우수"


    return "기타"


df[
    "project_reason"
] = (
    df.apply(
        project_reason,
        axis=1
    )
)


# ============================================================
# 12. 보류 사유
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


    if not row[
        "project_region_safe"
    ]:
        return "지역검증우수아님"


    if not row[
        "project_no_review_region"
    ]:
        return "검토지역존재"


    if not row[
        "project_has_official_info"
    ]:
        return "공식지역정보부족"


    if (
        row[
            "project_brand_length"
        ]
        <= 3
    ):
        return "브랜드명3글자이하"


    if (
        not row[
            "project_exact"
        ]
        and
        not row[
            "project_prefix"
        ]
    ):
        return "PREFIX아님"


    return "보수적기준미충족"


df[
    "hold_reason"
] = (
    df.apply(
        hold_reason,
        axis=1
    )
)


# ============================================================
# 13. 실제 프로젝트 투입 데이터
# ============================================================

project_df = (
    df[
        df[
            "project_ready"
        ]
        == True
    ]
    .copy()
)


# ============================================================
# 14. 보류 후보
# ============================================================

hold_df = (
    df[
        df[
            "project_ready"
        ]
        == False
    ]
    .copy()
)


# ============================================================
# 15. 프로젝트 실제 투입용 핵심 컬럼
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
# 16. 브랜드별 요약
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


# ============================================================
# 17. 지역별 요약
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
# 18. 보류 사유 요약
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
# 19. 분석 요약
# ============================================================

summary_df = pd.DataFrame(
    {

        "항목": [

            "교육 4차 전체",

            "브랜드 ID 존재",

            "프로젝트 실제 투입",

            "정확일치 투입",

            "4글자이상 PREFIX 투입",

            "보류 후보",

            "최종 브랜드 수"
        ],

        "건수": [

            len(
                df
            ),

            df[
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
# 20. 콘솔 출력
# ============================================================

print()
print("========================================")
print("교육서비스업 프로젝트 실제 투입 결과")
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
print("최종 투입 브랜드 TOP 30")
print("========================================")

print(
    brand_summary_df.head(
        30
    ).to_string(
        index=False
    )
)


# ============================================================
# 21. 경량 엑셀 저장
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
# 22. 보류 후보 CSV 저장
# ============================================================

hold_df.to_csv(
    HOLD_CSV_FILE,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 23. 저장 완료
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
print("보류 후보 CSV:")
print(
    HOLD_CSV_FILE
)