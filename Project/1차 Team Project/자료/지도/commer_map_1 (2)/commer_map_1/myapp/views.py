import json
import os
from pathlib import Path
import pandas as pd
from django.shortcuts import render
from django.utils.safestring import mark_safe

def commercial_map_view(request):
    # 현재 파일 기준 상위 폴더(commer_map_1) 설정
    base_dir = Path(__file__).resolve().parent.parent
    
    seoul_path = base_dir / 'seoul_data_1.xlsx'
    store_path = base_dir / 'seoul_store.csv'

    # 1. 상권 폴리곤 데이터 로드
    df_seoul = pd.read_excel(seoul_path)
    features = []
    for idx, row in df_seoul.iterrows():
        polygon_raw = row['상권 실제 경계 Polygon']
        if isinstance(polygon_raw, str):
            try:
                polygon_data = json.loads(polygon_raw)
            except json.JSONDecodeError:
                continue
        else:
            continue

        detail_info = {
            'floating_pop': (
                f"{int(row['총 유동인구']):,}명"
                if pd.notnull(row['총 유동인구'])
                else '정보 없음'
            ),
            'gender_ratio': str(row['주요 성별 비중'])
            if pd.notnull(row['주요 성별 비중'])
            else '-',
            'age_group': str(row['주요 연령대(Top2)'])
            if pd.notnull(row['주요 연령대(Top2)'])
            else '-',
            'day_ratio': str(row['주중/주말 비중'])
            if pd.notnull(row['주중/주말 비중'])
            else '-',
            'time_slot': str(row['주요 시간대(Top2)'])
            if pd.notnull(row['주요 시간대(Top2)'])
            else '-',
            'target_audience': str(row['추천 타깃층'])
            if pd.notnull(row['추천 타깃층'])
            else '-',
            'description': str(row['상권의 특성'])
            if pd.notnull(row['상권의 특성'])
            else '-',
            'good_biz': str(row['🟢 유리한 예시 업종'])
            if pd.notnull(row['🟢 유리한 예시 업종'])
            else '-',
            'bad_biz': str(row['🔴 불리한 예시 업종'])
            if pd.notnull(row['🔴 불리한 예시 업종'])
            else '-',
        }

        features.append({
            'code': row['상권 코드'],
            'name': row['상권명'],
            'district': row['자치구명'],
            'dong': row['행정동명'],
            'area_type': row['상권 구분명'],
            'details': detail_info,
            'polygon': polygon_data,
        })

    # 2. 상점 데이터 로드
    stores = []
    if os.path.exists(store_path):
        df_store = pd.read_csv(store_path, encoding='cp949', nrows=4000)
        for idx, row in df_store.iterrows():
            try:
                store_name = str(row.iloc[1]) if len(row) > 1 else '상호명 없음'
                large_cat = str(row.iloc[4]) if pd.notnull(row.iloc[4]) else ''
                middle_cat = str(row.iloc[6]) if pd.notnull(row.iloc[6]) else ''
                small_cat = str(row.iloc[8]) if pd.notnull(row.iloc[8]) else ''

                # [수정] 자치구명 / 시군구명 매핑 강화 (컬럼명 또는 표준 CSV 인덱스 14번 활용)
                district_val = '강남구'
                if '시군구명' in df_store.columns and pd.notnull(row['시군구명']):
                    district_val = str(row['시군구명'])
                elif '자치구명' in df_store.columns and pd.notnull(row['자치구명']):
                    district_val = str(row['자치구명'])
                elif len(row) > 14 and pd.notnull(row.iloc[14]):
                    district_val = str(row.iloc[14])

                # [수정] 행정동명 매핑 강화 (컬럼명 또는 인덱스 16/15번 활용)
                dong = ''
                if '행정동명' in df_store.columns and pd.notnull(row['행정동명']):
                    dong = str(row['행정동명'])
                elif len(row) > 16 and pd.notnull(row.iloc[16]):
                    dong = str(row.iloc[16])
                elif len(row) > 15 and pd.notnull(row.iloc[15]):
                    dong = str(row.iloc[15])

                # [수정] 위도/경도 매핑 강화 (컬럼명 또는 인덱스 38, 37번 활용)
                lat, lng = None, None
                if '위도' in df_store.columns and pd.notnull(row['위도']):
                    lat = float(row['위도'])
                elif len(row) > 38 and pd.notnull(row.iloc[38]):
                    lat = float(row.iloc[38])

                if '경도' in df_store.columns and pd.notnull(row['경도']):
                    lng = float(row['경도'])
                elif len(row) > 37 and pd.notnull(row.iloc[37]):
                    lng = float(row.iloc[37])

                if lat and lng:
                    stores.append({
                        'name': store_name,
                        'large': large_cat,
                        'middle': middle_cat,
                        'small': small_cat,
                        'district': district_val,  # 올바른 자치구명 적용
                        'dong': dong,
                        'lat': lat,
                        'lng': lng,
                    })
            except Exception:
                continue

    context = {
        'commercial_data': mark_safe(json.dumps(features, ensure_ascii=False)),
        'store_data': mark_safe(json.dumps(stores, ensure_ascii=False)),
    }
    return render(request, 'myapp/map.html', context)