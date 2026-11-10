import pandas as pd
import re
from pathlib import Path


# ============================================================
# 0. 경로 설정
# ============================================================

# 전국상가정보 - 교육서비스업
SHOP_FILE = Path(
    r"C:\workspace\fcha_data\data\전국상가정보_교육서비스업_202610\records.csv"
)

# 공정위 브랜드 기본정보 2024 / 2025 / 2026
BRAND_FILES = [
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2024\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2025\records.csv"),
    Path(r"C:\workspace\fcha_data\data\공정거래위원회_브랜드목록_2026\records.csv"),
]

# 결과 저장 폴더
OUTPUT_DIR = Path(
    r"C:\workspace\fcha_data\output\franchise_matching"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = (
    OUTPUT_DIR /
    "교육서비스업_프랜차이즈_2차자동매칭.xlsx"
)


# ============================================================
# 1. 상호명 / 브랜드명 정리 함수
# ============================================================

def clean_name(name):
    """
    브랜드명 비교용 문자열 정리

    예)
    '뮤엠 영어'       -> '뮤엠영어'
    'TMT-피자'       -> 'TMT피자'
    '한우리(논술)'   -> '한우리논술'

    원본 데이터는 수정하지 않는다.
    비교용 컬럼만 따로 만든다.
    """

    if pd.isna(name):
        return ""

    name = str(name).strip()

    # 영어는 대문자로 통일
    name = name.upper()

    # 공백 제거
    name = re.sub(r"\s+", "", name)

    # 한글, 영문, 숫자를 제외한 문자 제거
    name = re.sub(
        r"[^가-힣A-Z0-9]",
        "",
        name
    )

    return name


# ============================================================
# 2. 전국상가정보 읽기
# ============================================================

print()
print("========================================")
print("1. 전국상가정보 읽기")
print("========================================")

shop_df = pd.read_csv(
    SHOP_FILE,
    encoding="utf-8"
)

print("전체 상가 데이터 :", shop_df.shape)


# ============================================================
# 3. 전국상가정보에서 사용할 컬럼만 선택
# ============================================================

shop_cols = [
    'bizesId',
    'bizesNm',
    'brchNm',

    'indsLclsCd',
    'indsLclsNm',

    'indsMclsCd',
    'indsMclsNm',

    'indsSclsCd',
    'indsSclsNm',

    'ctprvnCd',
    'ctprvnNm',

    'signguCd',
    'signguNm',

    'rdnmAdr',

    'lon',
    'lat'
]

shop_df = shop_df[shop_cols].copy()


# 비교용 정리 상호명 생성
shop_df['cleaned_store_name'] = (
    shop_df['bizesNm']
    .apply(clean_name)
)


print("사용 컬럼 :", shop_df.shape)


# ============================================================
# 4. 공정위 브랜드 기본정보 읽기
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
        file.name,
        ":",
        len(temp),
        "건"
    )

    brand_list.append(temp)


# 2024 + 2025 + 2026 통합
brand_df = pd.concat(
    brand_list,
    ignore_index=True
)

print("연도 통합 전체 :", len(brand_df))


# ============================================================
# 5. 필요한 브랜드 컬럼만 선택
# ============================================================

brand_cols = [
    'jngBizCrtraYr',
    'brandMnno',
    'brandNm',
    'indutyLclasNm',
    'indutyMlsfcNm',
    'corpNm'
]

brand_df = brand_df[
    brand_cols
].copy()


# 브랜드명이 없는 데이터 제거
brand_df = brand_df[
    brand_df['brandNm'].notna()
].copy()


# 비교용 브랜드명
brand_df['cleaned_brand_name'] = (
    brand_df['brandNm']
    .apply(clean_name)
)


# ============================================================
# 6. 교육서비스업 관련 브랜드 우선 추출
# ============================================================
#
# 공정위 데이터의 실제 서비스업 중분류:
#
# 기타 교육
# 교육 (외국어)
# 교육 (교과)
#
# 교육서비스업 상가정보와 비교하므로
# 우선 이 세 종류를 공식 브랜드 후보로 사용한다.
# ============================================================

EDUCATION_INDUSTRIES = [
    '기타 교육',
    '교육 (외국어)',
    '교육 (교과)',
]


education_brand_df = brand_df[
    (
        brand_df['indutyLclasNm'] == '서비스'
    )
    &
    (
        brand_df['indutyMlsfcNm']
        .isin(EDUCATION_INDUSTRIES)
    )
].copy()


print()
print("교육 관련 브랜드 연도별 전체 :", len(education_brand_df))


# ============================================================
# 7. 같은 브랜드가 여러 연도에 존재하므로 최신연도 우선
# ============================================================
#
# brandMnno 기준으로
# 2026 -> 2025 -> 2024 순으로 최신 정보를 남긴다.
# ============================================================

education_brand_df = (
    education_brand_df
    .sort_values(
        'jngBizCrtraYr',
        ascending=False
    )
    .drop_duplicates(
        subset=['brandMnno'],
        keep='first'
    )
    .reset_index(drop=True)
)


print(
    "교육 관련 고유 브랜드 :",
    len(education_brand_df)
)


# ============================================================
# 8. 너무 짧은 브랜드명 표시
# ============================================================
#
# 예:
# 이룸
# 채움
# 리드
#
# 이런 이름은 contains 검색 시
# 오탐 가능성이 높으므로 별도 주의한다.
# ============================================================

education_brand_df['brand_name_length'] = (
    education_brand_df[
        'cleaned_brand_name'
    ]
    .str.len()
)


education_brand_df['short_brand'] = (
    education_brand_df[
        'brand_name_length'
    ] < 3
)


# ============================================================
# 9. 정확 일치용 사전 생성
# ============================================================

exact_map = {}

for _, row in education_brand_df.iterrows():

    cleaned = row['cleaned_brand_name']

    if cleaned == "":
        continue

    # 같은 이름이 여러 브랜드 ID에 걸릴 수도 있으므로
    # 우선 리스트로 저장
    if cleaned not in exact_map:
        exact_map[cleaned] = []

    exact_map[cleaned].append(
        {
            'brandMnno': row['brandMnno'],
            'brandNm': row['brandNm'],
            'indutyMlsfcNm': row['indutyMlsfcNm'],
            'corpNm': row['corpNm'],
            'year': row['jngBizCrtraYr'],
        }
    )


# ============================================================
# 10. 1단계 - 공식 브랜드명 정확 일치
# ============================================================

def find_exact_match(store_name):

    if store_name in exact_map:

        matches = exact_map[store_name]

        # 브랜드 ID가 하나뿐이면 자동 확정
        if len(matches) == 1:

            m = matches[0]

            return pd.Series([
                m['brandMnno'],
                m['brandNm'],
                m['corpNm'],
                m['indutyMlsfcNm'],
                'exact',
                'HIGH'
            ])

        # 같은 공식 브랜드명이 여러 브랜드 ID에서 사용될 경우
        return pd.Series([
            None,
            None,
            None,
            None,
            'duplicate_brand_name',
            'REVIEW'
        ])

    return pd.Series([
        None,
        None,
        None,
        None,
        None,
        None
    ])


shop_df[
    [
        'brandMnno',
        'matched_brandNm',
        'matched_corpNm',
        'matched_brand_industry',
        'match_type',
        'match_confidence'
    ]
] = shop_df[
    'cleaned_store_name'
].apply(
    find_exact_match
)


print()
print(
    "정확 일치 :",
    (
        shop_df['match_type']
        == 'exact'
    ).sum()
)

# ============================================================
# 11. 포함 검색 준비 - 빠른 방식
# ============================================================

print()
print("========================================")
print("3. 공식 브랜드 포함 검색 시작")
print("========================================")


# 브랜드명이 너무 짧으면 오탐이 많으므로
# 우선 정규화 후 3글자 이상만 포함 검색에 사용
contains_brand_df = (
    education_brand_df[
        education_brand_df['brand_name_length'] >= 3
    ]
    .copy()
)


# ------------------------------------------------------------
# 같은 정규화 브랜드명이 여러 brandMnno에 존재하는지 확인
# ------------------------------------------------------------

brand_name_counts = (
    contains_brand_df[
        'cleaned_brand_name'
    ]
    .value_counts()
)


duplicate_clean_names = set(
    brand_name_counts[
        brand_name_counts > 1
    ].index
)


# ------------------------------------------------------------
# 브랜드명을 길이가 긴 순서로 정렬
#
# 예:
# 한우리독서토론논술
# 한우리
#
# 긴 이름부터 검색해야 더 구체적인 브랜드가 먼저 잡힘
# ------------------------------------------------------------

unique_brand_names = (
    contains_brand_df[
        'cleaned_brand_name'
    ]
    .dropna()
    .drop_duplicates()
    .tolist()
)


unique_brand_names = sorted(
    unique_brand_names,
    key=len,
    reverse=True
)


# ============================================================
# 12. 정규식 패턴 생성
# ============================================================
#
# 502개 브랜드를 상가마다 반복문으로 비교하는 대신
# pandas 문자열 검색을 한 번에 사용
# ============================================================

brand_pattern = (
    '('
    +
    '|'.join(
        re.escape(name)
        for name in unique_brand_names
        if name != ''
    )
    +
    ')'
)


print(
    "포함 검색 대상 공식 브랜드 수 :",
    len(unique_brand_names)
)


# ============================================================
# 13. 정확 일치가 안 된 상가만 포함 검색
# ============================================================

no_match_mask = (
    shop_df['match_type']
    .isna()
)


# 검색 대상 상호
target_names = (
    shop_df.loc[
        no_match_mask,
        'cleaned_store_name'
    ]
)


# ------------------------------------------------------------
# 브랜드명 포함 여부를 벡터화 검색
# ------------------------------------------------------------

extracted_brand = (
    target_names
    .str.extract(
        brand_pattern,
        expand=False
    )
)


print(
    "공식 브랜드명 포함 발견 :",
    extracted_brand.notna().sum()
)


# ============================================================
# 14. 브랜드명 -> 브랜드 정보 사전 생성
# ============================================================

brand_lookup = {}


for _, row in contains_brand_df.iterrows():

    cleaned_name = row[
        'cleaned_brand_name'
    ]

    # 같은 이름이 여러 브랜드에 존재하면
    # 여기서는 자동확정하지 않음
    if cleaned_name in duplicate_clean_names:
        continue

    brand_lookup[
        cleaned_name
    ] = {
        'brandMnno': row['brandMnno'],
        'brandNm': row['brandNm'],
        'corpNm': row['corpNm'],
        'indutyMlsfcNm': row['indutyMlsfcNm'],
    }


# ============================================================
# 15. 포함 검색 결과 적용
# ============================================================

for index, cleaned_brand in extracted_brand.items():

    # 매칭 없음
    if pd.isna(cleaned_brand):
        continue

    # --------------------------------------------------------
    # 같은 정규화 브랜드명이
    # 여러 brandMnno에서 사용되는 경우
    # --------------------------------------------------------

    if cleaned_brand in duplicate_clean_names:

        shop_df.at[
            index,
            'match_type'
        ] = 'duplicate_brand_name'

        shop_df.at[
            index,
            'match_confidence'
        ] = 'REVIEW'

        continue


    # --------------------------------------------------------
    # 정상적으로 하나의 공식 브랜드와 연결
    # --------------------------------------------------------

    info = brand_lookup.get(
        cleaned_brand
    )

    if info is None:
        continue


    shop_df.at[
        index,
        'brandMnno'
    ] = info['brandMnno']

    shop_df.at[
        index,
        'matched_brandNm'
    ] = info['brandNm']

    shop_df.at[
        index,
        'matched_corpNm'
    ] = info['corpNm']

    shop_df.at[
        index,
        'matched_brand_industry'
    ] = info['indutyMlsfcNm']

    shop_df.at[
        index,
        'match_type'
    ] = 'contains'

    shop_df.at[
        index,
        'match_confidence'
    ] = 'MEDIUM'


print()
print("========================================")
print("포함 검색 완료")
print("========================================")

print(
    "contains :",
    (
        shop_df['match_type']
        == 'contains'
    ).sum()
)

print(
    "중복 브랜드명 검토 필요 :",
    (
        shop_df['match_type']
        == 'duplicate_brand_name'
    ).sum()
)



# ============================================================
# 13. 매칭 결과 상태 만들기
# ============================================================

def make_status(row):

    if row[
        'match_confidence'
    ] == 'HIGH':

        return '자동확정'

    if row[
        'match_confidence'
    ] == 'MEDIUM':

        return '프랜차이즈후보'

    if row[
        'match_confidence'
    ] == 'REVIEW':

        return '검토필요'

    return '미매칭'


shop_df[
    'match_status'
] = shop_df.apply(
    make_status,
    axis=1
)


# ============================================================
# 14. 반복 상호명 계산
# ============================================================

name_counts = (
    shop_df[
        'bizesNm'
    ]
    .value_counts()
    .reset_index()
)

name_counts.columns = [
    'bizesNm',
    'store_count'
]


# 5개 이상 반복 상호
repeat_candidates = (
    name_counts[
        name_counts[
            'store_count'
        ] >= 5
    ]
    .copy()
)


# ============================================================
# 15. 프랜차이즈 후보 데이터
# ============================================================

matched_df = shop_df[
    shop_df[
        'match_status'
    ].isin([
        '자동확정',
        '프랜차이즈후보',
        '검토필요'
    ])
].copy()


# ============================================================
# 16. 자동확정 데이터
# ============================================================

confirmed_df = shop_df[
    shop_df[
        'match_status'
    ] == '자동확정'
].copy()


# ============================================================
# 17. 포함 매칭 후보
# ============================================================

candidate_df = shop_df[
    shop_df[
        'match_status'
    ] == '프랜차이즈후보'
].copy()


# ============================================================
# 18. 검토 필요
# ============================================================

review_df = shop_df[
    shop_df[
        'match_status'
    ] == '검토필요'
].copy()


# ============================================================
# 19. 미매칭
# ============================================================

unmatched_df = shop_df[
    shop_df[
        'match_status'
    ] == '미매칭'
].copy()


# ============================================================
# 20. 브랜드별 매장 수 요약
# ============================================================

brand_summary = (
    matched_df[
        matched_df[
            'brandMnno'
        ].notna()
    ]
    .groupby(
        [
            'brandMnno',
            'matched_brandNm',
            'matched_brand_industry'
        ],
        dropna=False
    )
    .agg(

        store_count=(
            'bizesId',
            'count'
        ),

        province_count=(
            'ctprvnNm',
            'nunique'
        ),

        district_count=(
            'signguNm',
            'nunique'
        ),

        exact_count=(
            'match_type',
            lambda x:
            x.isin(
                ['exact']
            ).sum()
        ),

        contains_count=(
            'match_type',
            lambda x:
            x.isin(
                [
                    'contains',
                    'contains_longest'
                ]
            ).sum()
        )

    )
    .reset_index()
    .sort_values(
        'store_count',
        ascending=False
    )
)


# ============================================================
# 21. 브랜드 + 지역별 요약
# ============================================================

region_summary = (
    matched_df[
        matched_df[
            'brandMnno'
        ].notna()
    ]
    .groupby(
        [
            'brandMnno',
            'matched_brandNm',
            'ctprvnNm',
            'signguNm'
        ]
    )
    .size()
    .reset_index(
        name='store_count'
    )
)


# ============================================================
# 22. 전체 결과 요약
# ============================================================

summary_df = pd.DataFrame(
    {
        '항목': [
            '전체 상가',
            '교육 관련 공식 브랜드',
            '자동확정',
            '프랜차이즈후보',
            '검토필요',
            '미매칭',
            '5개 이상 반복 상호명',
        ],

        '건수': [
            len(shop_df),
            len(education_brand_df),

            (
                shop_df[
                    'match_status'
                ] == '자동확정'
            ).sum(),

            (
                shop_df[
                    'match_status'
                ] == '프랜차이즈후보'
            ).sum(),

            (
                shop_df[
                    'match_status'
                ] == '검토필요'
            ).sum(),

            (
                shop_df[
                    'match_status'
                ] == '미매칭'
            ).sum(),

            len(repeat_candidates)
        ]
    }
)


# ============================================================
# 23. 콘솔 결과 출력
# ============================================================

print()
print("========================================")
print("3. 자동 매칭 결과")
print("========================================")

print(summary_df.to_string(index=False))


print()
print("========================================")
print("브랜드별 상위 30개")
print("========================================")

print(
    brand_summary.head(30)
)


# ============================================================
# 24. 엑셀 저장
# ============================================================

print()
print("========================================")
print("4. 엑셀 저장")
print("========================================")


with pd.ExcelWriter(
    OUTPUT_FILE,
    engine='openpyxl'
) as writer:

    # 분석 요약
    summary_df.to_excel(
        writer,
        sheet_name='분석요약',
        index=False
    )

    # 공식 브랜드 목록
    education_brand_df.to_excel(
        writer,
        sheet_name='공식브랜드',
        index=False
    )

    # 전체 상가 + 매칭 결과
    shop_df.to_excel(
        writer,
        sheet_name='전체매칭결과',
        index=False
    )

    # 정확 일치
    confirmed_df.to_excel(
        writer,
        sheet_name='자동확정',
        index=False
    )

    # 포함 검색
    candidate_df.to_excel(
        writer,
        sheet_name='프랜차이즈후보',
        index=False
    )

    # 사람이 확인해야 할 것
    review_df.to_excel(
        writer,
        sheet_name='검토필요',
        index=False
    )

    # 매칭되지 않은 데이터
    unmatched_df.to_excel(
        writer,
        sheet_name='미매칭',
        index=False
    )

    # 반복 상호명
    repeat_candidates.to_excel(
        writer,
        sheet_name='반복상호',
        index=False
    )

    # 브랜드별 요약
    brand_summary.to_excel(
        writer,
        sheet_name='브랜드별요약',
        index=False
    )

    # 지역별 요약
    region_summary.to_excel(
        writer,
        sheet_name='지역별요약',
        index=False
    )


print()
print("저장 완료")
print(OUTPUT_FILE)