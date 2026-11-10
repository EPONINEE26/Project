import pandas as pd
import re
from pathlib import Path


# ============================================================
# 1. 파일 경로 설정
# ============================================================

input_file = Path(
    r"C:\workspace\fcha_data\data\전국상가정보_교육서비스업_202610\records.csv"
)

output_dir = Path(
    r"C:\workspace\fcha_data\output\franchise_matching"
)

output_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 전국상가정보 CSV 읽기
# ============================================================

df = pd.read_csv(
    input_file,
    encoding="utf-8"
)

print("전체 데이터 크기 :", df.shape)


# ============================================================
# 3. 프로젝트에서 사용할 컬럼만 선택
# ============================================================

use_cols = [
    'bizesId',      # 상가업소번호
    'bizesNm',      # 상호명
    'brchNm',       # 지점명

    'indsLclsCd',   # 업종 대분류 코드
    'indsLclsNm',   # 업종 대분류명
    'indsMclsCd',   # 업종 중분류 코드
    'indsMclsNm',   # 업종 중분류명
    'indsSclsCd',   # 업종 소분류 코드
    'indsSclsNm',   # 업종 소분류명

    'ctprvnCd',     # 시도 코드
    'ctprvnNm',     # 시도명
    'signguCd',     # 시군구 코드
    'signguNm',     # 시군구명

    'rdnmAdr',      # 도로명주소
    'lon',          # 경도
    'lat'           # 위도
]

shop_df = df[use_cols].copy()

print("사용 컬럼 데이터 :", shop_df.shape)


# ============================================================
# 4. 상호명 정리 함수
# ============================================================

def clean_store_name(name):
    """
    상호명 비교를 위해
    공백과 특수문자를 제거한다.

    원본 bizesNm은 수정하지 않고
    별도의 cleaned_name 컬럼을 만든다.
    """

    if pd.isna(name):
        return ''

    name = str(name).strip()

    # 모든 공백 제거
    name = re.sub(r'\s+', '', name)

    # 한글, 영어, 숫자를 제외한 문자 제거
    name = re.sub(r'[^가-힣a-zA-Z0-9]', '', name)

    return name


shop_df['cleaned_name'] = (
    shop_df['bizesNm']
    .apply(clean_store_name)
)


# ============================================================
# 5. 브랜드명 정규화 사전
# ============================================================
#
# key:
#   최종적으로 사용할 공식 브랜드명
#
# value:
#   전국상가정보에서 나타날 수 있는 상호명 변형
#
# 현재는 테스트용이며
# 앞으로 공정위 공식 브랜드 정보를 기준으로 계속 확장한다.
# ============================================================

brand_aliases = {

    '뮤엠영어': [
        '뮤엠영어',
        '뮤엠영어학원',
        '뮤엠영어교습소',
    ],

    '한우리독서토론논술': [
        '한우리독서토론논술',
        '한우리독서논술',
        '한우리독서토론논술학원',
        '한우리독서논술학원',
    ],

    '리드인': [
        '리드인',
        '리드인독서논술',
        '리드인독서논술학원',
        '리드인독서논술교습소',
    ],

    '푸르넷공부방': [
        '푸르넷공부방',
        '푸르넷',
    ],

    '아소비': [
        '아소비',
        '아소비학원',
        '아소비공부방',
    ],
}


# ============================================================
# 6. 브랜드명 정규화 함수
# ============================================================

def normalize_brand_name(store_name):

    cleaned_store_name = clean_store_name(store_name)

    if cleaned_store_name == '':
        return None

    for official_name, aliases in brand_aliases.items():

        for alias in aliases:

            cleaned_alias = clean_store_name(alias)

            if cleaned_alias in cleaned_store_name:
                return official_name

    return None


shop_df['normalized_brand'] = (
    shop_df['bizesNm']
    .apply(normalize_brand_name)
)


# ============================================================
# 7. 상호명별 등장 횟수 계산
# ============================================================

name_counts = (
    shop_df['bizesNm']
    .value_counts()
    .reset_index()
)

name_counts.columns = [
    'bizesNm',
    'store_count'
]


# ============================================================
# 8. 반복 상호명 후보 추출
# ============================================================
#
# 우선 같은 상호명이 5개 이상 존재하는 경우를
# 브랜드 후보로 본다.
#
# 이것만으로 프랜차이즈 확정은 하지 않는다.
# ============================================================

brand_candidates = (
    name_counts[
        name_counts['store_count'] >= 5
    ]
    .copy()
)


# ============================================================
# 9. 일반명칭 목록
# ============================================================
#
# 반복해서 등장하지만
# 실제 브랜드명이 아닌 경우를 표시한다.
#
# 삭제하지 않고 generic_name=True 로 표시만 한다.
# ============================================================

generic_names = [
    '입시·교과학원',
    '업소명없음',
    '그외기타교육기관',
    '개인과외',
    '개인과외교습소',
    '음악학원',
    '외국어학원',
    '요가/필라테스학원',
]


brand_candidates['generic_name'] = (
    brand_candidates['bizesNm']
    .isin(generic_names)
)


# ============================================================
# 10. 프랜차이즈 브랜드 매칭 결과만 추출
# ============================================================

matched_df = (
    shop_df[
        shop_df['normalized_brand'].notna()
    ]
    .copy()
)


# ============================================================
# 11. 매칭 방식 컬럼 추가
# ============================================================
#
# 현재는 브랜드 사전 포함 여부를 이용한
# 1차 후보 추출이므로 alias_contains라고 표시한다.
#
# 이후:
# exact
# alias
# contains
# manual_review
#
# 같은 방식으로 발전시킬 수 있다.
# ============================================================

matched_df['match_type'] = 'alias_contains'


# ============================================================
# 12. 브랜드별 매장 수 집계
# ============================================================

brand_summary = (
    matched_df
    .groupby('normalized_brand')
    .agg(
        store_count=('bizesId', 'count'),
        province_count=('ctprvnNm', 'nunique'),
        district_count=('signguNm', 'nunique')
    )
    .reset_index()
    .sort_values(
        'store_count',
        ascending=False
    )
)


# ============================================================
# 13. 지역별 브랜드 매장 수 집계
# ============================================================

region_summary = (
    matched_df
    .groupby([
        'normalized_brand',
        'ctprvnNm',
        'signguNm'
    ])
    .size()
    .reset_index(
        name='store_count'
    )
)


# ============================================================
# 14. 결과 확인
# ============================================================

print()
print("========================================")
print("전체 상가 수")
print("========================================")
print(len(shop_df))


print()
print("========================================")
print("5개 이상 반복 상호명 수")
print("========================================")
print(len(brand_candidates))


print()
print("========================================")
print("브랜드 매칭 상가 수")
print("========================================")
print(len(matched_df))


print()
print("========================================")
print("브랜드별 매장 수")
print("========================================")
print(brand_summary.head(30))


# ============================================================
# 15. 결과 엑셀 저장
# ============================================================

output_file = (
    output_dir /
    "교육서비스업_프랜차이즈_1차분석.xlsx"
)


with pd.ExcelWriter(
    output_file,
    engine='openpyxl'
) as writer:

    # 전체에서 필요한 컬럼만 추린 데이터
    shop_df.to_excel(
        writer,
        sheet_name='상가원본가공',
        index=False
    )

    # 반복 상호명 후보
    brand_candidates.to_excel(
        writer,
        sheet_name='브랜드후보',
        index=False
    )

    # 실제 브랜드 사전에 매칭된 상가
    matched_df.to_excel(
        writer,
        sheet_name='브랜드매칭',
        index=False
    )

    # 브랜드별 매장 수
    brand_summary.to_excel(
        writer,
        sheet_name='브랜드별요약',
        index=False
    )

    # 브랜드 + 지역별 매장 수
    region_summary.to_excel(
        writer,
        sheet_name='지역별요약',
        index=False
    )


print()
print("========================================")
print("저장 완료")
print("========================================")
print(output_file)
