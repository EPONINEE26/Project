from pathlib import Path
import pandas as pd
from django.core.management.base import BaseCommand,CommandError
from django.db import transaction
from brands.models import Brand,AnnualStat,RegionalStat
from brands.views import REGIONS

class Command(BaseCommand):
    help='정규화한 브랜드·연도·지역 CSV를 검증한 후 원자적으로 저장합니다.'
    def add_arguments(self,parser):
        parser.add_argument('csv_path')
        parser.add_argument('--demo',action='store_true',help='예시 CSV 입력 시 필수. 실데이터로 표시하지 않음')
    @transaction.atomic
    def handle(self,*args,**opts):
        try:
            df=pd.read_csv(Path(opts['csv_path']),dtype=str,keep_default_na=False,encoding='utf-8-sig')
            required=['brand_id','name','category','year','region','region_stores','stores','opened','closed','annual_sales_krw','source_label','source_url']
            missing=set(required)-set(df.columns)
            if missing: raise ValueError('필수 열 누락: '+', '.join(sorted(missing)))
            if df.empty: raise ValueError('CSV에 데이터가 없습니다.')
            for c in required: df[c]=df[c].str.strip()
            if df[['brand_id','name','category','year','region','source_label']].eq('').any().any(): raise ValueError('식별자, 이름, 업종, 연도, 지역, 출처는 필수입니다.')
            if (~df['brand_id'].str.fullmatch(r'[a-z0-9][a-z0-9-]*')).any(): raise ValueError('brand_id는 영문 소문자·숫자·하이픈만 사용합니다.')
            if (~df['region'].isin(REGIONS)).any(): raise ValueError('지역은 API_CONTRACT.md의 17개 지역명을 사용하세요.')
            if (~df['category'].isin(['카페','치킨','편의점','미용실'])).any(): raise ValueError('지원 업종: 카페, 치킨, 편의점, 미용실')
            if df.duplicated(['brand_id','year','region']).any(): raise ValueError('브랜드·연도·지역 중복 행이 있습니다.')
            nums=['year','region_stores','stores','opened','closed','annual_sales_krw']
            for c in nums:
                invalid=(df[c]!='') & ~df[c].str.fullmatch(r'\d+')
                if invalid.any(): raise ValueError(f'{c}: 음수·소수·문자·쉼표가 포함된 숫자는 허용하지 않습니다.')
                df[c]=pd.to_numeric(df[c].replace('',None),errors='raise').astype('Int64')
            if not df['year'].between(1900,2100).all(): raise ValueError('연도 범위는 1900~2100입니다.')
            for _,g in df.groupby('brand_id'):
                if any(g[c].nunique(dropna=False)>1 for c in ['name','category']):raise ValueError('같은 브랜드의 이름·업종이 다릅니다.')
            for (slug,year),g in df.groupby(['brand_id','year']):
                nationwide=['name','category','stores','opened','closed','annual_sales_krw','source_label','source_url']
                if any(g[c].nunique(dropna=False)>1 for c in nationwide):raise ValueError(f'{slug}/{year}: 지역 행의 전국 통계·출처가 다릅니다.')
                row=g.iloc[0]
                if len(g)!=17 or set(g['region'])!=set(REGIONS): raise ValueError(f'{slug}/{year}: 17개 지역 행이 모두 필요합니다. 미제공 수치는 빈칸으로 남겨두세요.')
                if pd.notna(row['stores']) and g['region_stores'].notna().all() and int(g['region_stores'].sum())!=int(row['stores']):raise ValueError(f'{slug}/{year}: 지역 매장 합계와 전국 매장 수가 다릅니다.')
                existing=Brand.objects.filter(slug=slug).first()
                if existing and existing.is_demo != opts['demo']:raise ValueError(f'{slug}: 예시·실제 데이터 식별자가 충돌합니다. 다른 brand_id를 사용하세요.')
                b,_=Brand.objects.update_or_create(slug=slug,defaults={'name':row['name'],'category':row['category'],'is_demo':opts['demo']})
                number=lambda v: None if pd.isna(v) else int(v)
                s,_=AnnualStat.objects.update_or_create(brand=b,year=int(year),defaults={**{c:number(row[c]) for c in ['stores','opened','closed','annual_sales_krw']},'source_label':row['source_label'],'source_url':row['source_url']})
                for _,r in g.iterrows(): RegionalStat.objects.update_or_create(annual_stat=s,region=r['region'],defaults={'stores':number(r['region_stores'])})
        except (ValueError,TypeError,OSError,OverflowError) as e:raise CommandError(str(e)) from e
        self.stdout.write(self.style.SUCCESS(f'{len(df)}개 지역 통계 행 입력 완료'))
