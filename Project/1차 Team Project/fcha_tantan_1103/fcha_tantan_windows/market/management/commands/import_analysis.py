"""명시적 필드만 허용하고 전체 검증·원자적 저장을 하는 상권 JSON 입력."""
import json
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import transaction
from market import analysis_models as m

MODELS={x.__name__:x for x in [m.DataSource,m.CommercialArea,m.IndustryCode,m.PopulationStat,m.IndustrySales,m.StoreTrend,m.PublicStore,m.Attractor,m.BrandOperation]}
class Command(BaseCommand):
    help='상권 DB JSON 검증/적재. 기본은 검증만 수행; --commit을 지정해야 저장합니다.'
    def add_arguments(self,parser):
        parser.add_argument('path')
        parser.add_argument('--commit',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        try:
            with open(options['path'],encoding='utf-8-sig') as f: records=json.load(f,parse_float=Decimal)
            if not isinstance(records,list): raise ValueError('최상위는 배열이어야 합니다.')
            for index,row in enumerate(records,1):
                if set(row)!={'model','fields'}: raise ValueError(f'{index}행: model, fields만 허용합니다.')
                model=MODELS.get(row['model'])
                if model is None: raise ValueError(f'{index}행: 지원하지 않는 모델')
                fields=row['fields'].copy()
                allowed={f.attname for f in model._meta.fields}
                if set(fields)-allowed: raise ValueError(f'{index}행: 알 수 없는 컬럼 {set(fields)-allowed}')
                pk=fields.pop('id',None)
                obj=model.objects.get(pk=pk) if pk is not None and model.objects.filter(pk=pk).exists() else model(pk=pk)
                for key,value in fields.items():
                    field=next(f for f in model._meta.fields if f.attname == key)
                    # JSON 내 좌표는 원본 숫자 표기 보존을 위해 숫자 대신 문자열을 권장합니다.
                    if isinstance(field,m.models.JSONField):
                        def convert(v):
                            if isinstance(v,Decimal): return str(v)
                            if isinstance(v,dict): return {k:convert(a) for k,a in v.items()}
                            if isinstance(v,list): return [convert(a) for a in v]
                            return v
                        value=convert(value)
                    setattr(obj,key,value)
                if isinstance(obj,m.CommercialArea) and obj.boundary is not None:
                    geometry=obj.boundary
                    if geometry.get('type') not in ['Polygon','MultiPolygon']: raise ValueError(f'{index}행: Polygon/MultiPolygon Geometry만 허용')
                    polys=[geometry['coordinates']] if geometry['type']=='Polygon' else geometry['coordinates']
                    if not polys: raise ValueError(f'{index}행: 경계가 비었습니다.')
                    for poly in polys:
                        if not poly: raise ValueError('빈 폴리곤')
                        for ring in poly:
                            if len(ring)<4 or ring[0]!=ring[-1]: raise ValueError('경계 링은 닫힌 4개 이상 좌표여야 합니다.')
                            for pair in ring:
                                if len(pair)!=2 or not -180<=Decimal(str(pair[0]))<=180 or not -90<=Decimal(str(pair[1]))<=90: raise ValueError('잘못된 경도·위도')
                obj.full_clean()
                obj.save()
            if not options['commit']: transaction.set_rollback(True)
        except (ValueError,KeyError,TypeError,ValidationError,OSError) as e: raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(f'{len(records)}건 '+('저장 완료' if options['commit'] else '검증 완료 (저장하지 않음)')))
