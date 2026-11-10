"""실행: uvicorn api:app --app-dir code --host 127.0.0.1 --port 8000
실제 명령은 사용설명서 참조. GET은 읽기 전용, POST/budget은 비용입력 계산만 수행한다.
"""
from pathlib import Path
from typing import Literal
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from analysis import load_tables,aggregate,compare_sales,scenario,records,validate
ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='원본 보존 프랜차이즈 분석',version='1.0')
def data():return load_tables(ROOT/'json')

@app.get('/summary')
def summary(year:int,region:Literal['전국','서울','경기'],by:Literal['industry','brand','region']='industry'):
    try:
        s,t,_,_=data();return records(aggregate(s,t,year,region,by))
    except ValueError as e:raise HTTPException(422,str(e))

@app.get('/sales')
def sales(year:int,region:Literal['전국','서울','경기'],industry:str|None=None):
    try:return records(compare_sales(data()[0],year,region,industry))
    except ValueError as e:raise HTTPException(422,str(e))

@app.get('/validation')
def validation():
    s,t,_,w=data();return {'analysis':validate(s,t),'excluded_ambiguous_years':w}

class Budget(BaseModel):
    year:Literal[2024,2025]
    region:Literal['전국','서울','경기']
    industry:Literal['치킨','커피','이미용','편의점']
    costs:dict[str,float]
    startup_cost:float|None=Field(default=None,ge=0)
    period:Literal['annual','monthly']='annual'

@app.post('/budget')
def budget(body:Budget):
    try:return scenario(data()[0],body.year,body.region,body.industry,body.costs,body.startup_cost,body.period)
    except ValueError as e:raise HTTPException(422,str(e))
