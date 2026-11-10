"""원본 보존 JSON을 직접 읽는 분석 함수. 원본 금액을 공시값으로 교체하지 않는다.

pandas: DataFrame(표 생성), groupby(동일 기준 집계), agg(통계),
rank(동점 순위), merge(전년 비교), to_json(API용 결측 변환)을 사용한다.
실행: python code/analysis.py --json json --output 분석결과.json
"""
from pathlib import Path
from decimal import Decimal,InvalidOperation
import argparse,json,math
import pandas as pd
from preserve_workbooks import save_json

def _v(sheet,row,col):
    return sheet['cells'].get(f'{col}{row}',{}).get('value')

def _year(value):
    """단일 실적연도만 허용한다. 2024~2028을 임의로2024로 바꾸지 않는다."""
    return int(value) if str(value) in ('2024','2025') else None

def load_tables(directory):
    """4개 원본 보존JSON의 지정 시트만 읽는다. 원본의 다른 업종 행도 삭제하지 않는다.

    분석에서는 파일 업종과 같은 행만 사용하므로 커피 파일에 남아 있는
    치킨 원본행을 다시 합산하지 않는다. 원본JSON에는 그 행이 그대로 있다.
    """
    sales=[];stores=[];costs=[];warnings=[]
    for path in sorted(Path(directory).glob('*.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        if 'sheets' not in obj:continue
        industry=obj['source_filename'].split('_')[1]
        sheets={s['name']:s for s in obj['sheets']}
        for name,out,cols in [('05_매출비교',sales,[('C','전국'),('D','서울'),('E','경기')]),('03_지역집계',stores,[('E','전국'),('C','서울'),('D','경기')])]:
            s=sheets[name];last=max(int(''.join(filter(str.isdigit,c))) for c in s['cells'])
            for row in range(3,last+1):
                brand=_v(s,row,'A')
                if _v(s,row,'B')!=industry:continue
                year=_year(_v(s,row,'F'))
                for col,region in cols:
                    value=_v(s,row,col);patch=next((p for p in obj['changes'] if p['sheet']==name and p['cell']==f'{col}{row}'),None)
                    actual_year=year or (patch['year'] if patch else None)
                    if actual_year is None:
                        warnings.append({'file':path.name,'sheet':name,'cell':f'{col}{row}','issue':'원본 연도 범위가 모호해 연도별 분석 제외','original_year':_v(s,row,'F'),'preserved_value':value});continue
                    if isinstance(value,(int,float)) and not isinstance(value,bool):
                        out.append({'year':actual_year,'industry':industry,'brand':brand,'region':region,'value':value,'source_file':obj['source_filename'],'source_cell':f'{name}!{col}{row}','origin':'filled_blank' if patch else 'preserved_original'})
        s=sheets['01_창업비용'];last=max(int(''.join(filter(str.isdigit,c))) for c in s['cells'])
        for row in range(3,last+1):
            if _v(s,row,'B')!=industry:continue
            values={key:_v(s,row,col) for key,col in [('fee','C'),('education','D'),('deposit','E'),('interior','F'),('equipment_other','G'),('reported_total','I')]}
            subtotal=sum(v for k,v in values.items() if k!='reported_total' and isinstance(v,(int,float)))
            costs.append({'brand':_v(s,row,'A'),'industry':industry,**values,'original_formula_total':subtotal,'reported_minus_original_formula':values['reported_total']-subtotal,'year':None,'note':'원본 비용 표의 적용연도 미표기. 원본 SUM 계산을 재현하며 인테리어 중복 가능성 별도 검토'})
    s=pd.DataFrame(sales);t=pd.DataFrame(stores);c=pd.DataFrame(costs)
    if s.duplicated(['year','industry','brand','region']).any():raise ValueError('매출 복합키 중복')
    return s,t,c,warnings

def select(frame,year,region,industry=None):
    """전국과 서울·경기의 중복 합산을 막도록 한 연도·한 지역을 필수 지정한다."""
    if isinstance(year,bool) or year not in (2024,2025):raise ValueError('연도는2024 또는2025')
    if region not in ['전국','서울','경기']:raise ValueError('지역은 전국/서울/경기')
    mask=frame.year.eq(year)&frame.region.eq(region)
    if industry is not None:mask&=frame.industry.eq(industry)
    return frame.loc[mask].copy()

def aggregate(sales,stores,year,region,by='industry',industry=None):
    """by=업종/브랜드/지역에 따라 groupby 집계. 매출은 점포당 평균의 단순평균이다.

    agg는 평균·개수·최소·최대를 한 표로 만든다. 지역점포 수는 같은 연도·지역만
    sum(min_count=1)으로 합산한다. 매출 평균에 점포 수를 곱해 총매출로 오인하지 않는다.
    """
    if by not in ['industry','brand','region']:raise ValueError('잘못된 집계기준')
    s=select(sales,year,region,industry);t=select(stores,year,region,industry)
    a=s.groupby(by,as_index=False).agg(mean_revenue=('value','mean'),observed_brands=('brand','nunique'),min_revenue=('value','min'),max_revenue=('value','max'))
    n=t.groupby(by,as_index=False)['value'].sum(min_count=1).rename(columns={'value':'observed_store_count'})
    return a.merge(n,on=by,how='outer').assign(year=year,region=region)

def industry_average(sales,year,region):
    """선정 브랜드의 해당 연도·지역 점포당 평균매출 단순평균. 업종 전체 공식 평균 아님."""
    return select(sales,year,region).groupby('industry',as_index=False).agg(mean_annual_revenue=('value','mean'),brand_count=('brand','nunique'))

def compare_sales(sales,year,region,industry=None):
    """rank(method=min)은 공동1위 두 개 다음을3위로 계산한다. 매출차도 함께 계산한다."""
    s=select(sales,year,region,industry)
    s['industry_rank']=s.groupby('industry')['value'].rank(method='min',ascending=False)
    s['industry_mean']=s.groupby('industry')['value'].transform('mean')
    s['difference_from_mean']=s['value']-s['industry_mean']
    return s.sort_values(['industry','industry_rank','brand'])

def year_on_year(sales,region):
    """merge로 같은 브랜드·지역의2024와2025를 연결. 한쪽이 없으면 성장률을 만들지 않는다."""
    a=select(sales,2024,region);b=select(sales,2025,region)
    out=a.merge(b,on=['industry','brand','region'],how='outer',suffixes=('_2024','_2025'))
    out['change']=out.value_2025-out.value_2024
    out['growth_rate']=out['change']/out.value_2024.where(out.value_2024.gt(0))
    return out

def _amount(value,label):
    if isinstance(value,bool):raise ValueError(label+'은 숫자여야 함')
    try:d=Decimal(str(value))
    except (InvalidOperation,ValueError):raise ValueError(label+'은 숫자여야 함')
    if not d.is_finite() or d<0:raise ValueError(label+'은 유한한0이상 숫자여야 함')
    return d

def budget_profit(annual_revenue,costs,startup_cost=None,period='annual'):
    """운영이익=연매출−재료비−인건비−임차료−기타운영비−추가운영비.

    Decimal은 금액의 이진 부동소수점 오차를 줄인다. monthly 비용은12배로
    연환산한다. 이익률=운영이익/연매출, 회수기간=입력창업비용/양수운영이익.
    세금·감가상각·로열티 등은 해당 비용 항목에 포함해 입력해야 한다.
    """
    required={'material','labor','rent','other'}
    if not isinstance(costs,dict) or not required<=set(costs):raise ValueError('material,labor,rent,other 비용 필수')
    if period not in ['annual','monthly']:raise ValueError('period는 annual 또는monthly')
    revenue=_amount(annual_revenue,'연매출');factor=12 if period=='monthly' else 1
    annual={k:_amount(v,k)*factor for k,v in costs.items()};total=sum(annual.values(),Decimal(0));profit=revenue-total
    startup=None if startup_cost is None else _amount(startup_cost,'창업비용')
    return {'annual_revenue':float(revenue),'annual_costs':{k:float(v) for k,v in annual.items()},'annual_total_cost':float(total),'operating_profit':float(profit),'margin':float(profit/revenue) if revenue else None,'payback_years':float(startup/profit) if startup is not None and profit>0 else None,'basis':'사용자가 입력한 비용. 기본 공시비용이나 추정비율을 실제 비용으로 자동 대체하지 않음'}

def scenario(sales,year,region,industry,costs,startup_cost=None,period='annual'):
    """해당 업종 평균 매출에 사용자가 입력한 비용을 적용한다."""
    s=select(sales,year,region,industry)
    if s.empty:raise ValueError('해당 연도·지역·업종에 매출 없음')
    return {'year':year,'region':region,'industry':industry,'brand_count':int(s.brand.nunique()),**budget_profit(float(s.value.mean()),costs,startup_cost,period)}

def break_even(fixed_cost,variable_rate):
    """손익분기매출=연간고정비/(1−변동비율). 변동비율은0이상1미만이어야 한다."""
    f=_amount(fixed_cost,'고정비');r=_amount(variable_rate,'변동비율')
    if r>=1:raise ValueError('변동비율은1미만')
    return float(f/(1-r))

def records(frame):
    """DataFrame의 NaN을 JSON null로 바꿔 API가 유효한JSON을 반환하게 한다."""
    return json.loads(frame.to_json(orient='records',force_ascii=False))

def validate(sales,stores):
    """부호·연도·복합키를 확인한다. 원본0은 삭제하지 않고 별도 검토 대상으로 기록한다."""
    result={'sales_records':len(sales),'store_records':len(stores),'duplicate_sales_keys':int(sales.duplicated(['year','industry','brand','region']).sum()),'negative_values':int(sales.value.lt(0).sum()+stores.value.lt(0).sum()),'outside_years':int((~sales.year.isin([2024,2025])).sum()),'original_zero_revenue_rows':records(sales.loc[sales.value.eq(0)]),'note':'원본 값 보존 검증이며 공시와의 일치 보증이 아님. 원본 오류는 별도 내역 참조'}
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--json',default='json');p.add_argument('--output',default='분석결과.json');args=p.parse_args()
    s,t,c,w=load_tables(args.json)
    out={'validation':validate(s,t),'costs_original_preserved':records(c),'excluded_ambiguous_years':w,'industry_averages':[],'sales_comparisons':[],'aggregates':[],'year_on_year':{}}
    for year in [2024,2025]:
        for region in ['전국','서울','경기']:
            out['industry_averages']+=records(industry_average(s,year,region).assign(year=year,region=region))
            out['sales_comparisons']+=records(compare_sales(s,year,region))
            out['aggregates']+=records(aggregate(s,t,year,region))
    out['year_on_year']={r:records(year_on_year(s,r)) for r in ['전국','서울','경기']}
    save_json(out,args.output)
