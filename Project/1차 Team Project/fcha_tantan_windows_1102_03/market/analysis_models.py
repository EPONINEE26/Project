"""공공 상권 자료. 개인 후보지(StoreLocation)와 분리하여 저장합니다."""
from django.db import models
from django.conf import settings
from .fields import ExactCoordinateField
from django.core.validators import MinValueValidator, MaxValueValidator

class StartupCondition(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='startup_condition')
    location = models.CharField('희망 위치 (주소 또는 동)', max_length=200)
    location_scope = models.CharField('위치 정밀도', max_length=10, choices=[('dong','동 단위 예비분석'),('address','정확한 주소')], default='dong')
    latitude = ExactCoordinateField('위도', null=True, blank=True, validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude = ExactCoordinateField('경도', null=True, blank=True, validators=[MinValueValidator(-180),MaxValueValidator(180)])
    store_status = models.CharField('점포 확보 여부', max_length=12, choices=[('secured','확보'),('reviewing','검토 중'),('none','아직 없음')])
    total_budget_manwon = models.PositiveBigIntegerField('총 투입 가능 예산 (만원)', help_text='보증금·권리금·운영자금을 포함한 총예산입니다.')
    operation = models.CharField('운영 방식', max_length=10, choices=[('direct','직접 운영'),('staff','직원 중심'),('unknown','미정')])
    category = models.CharField('희망 업종', max_length=30, blank=True)
    channels = models.JSONField('판매 방식', default=list, blank=True)
    available_slots = models.JSONField('본인 투입 가능 시간', default=list, blank=True)
    weekend = models.BooleanField('주말 운영 가능', null=True, blank=True)
    staff_count = models.PositiveSmallIntegerField('투입 가능 인원', null=True, blank=True)
    area = models.DecimalField('점포 면적', max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    area_unit = models.CharField('면적 단위', max_length=6, choices=[('pyeong','평'),('sqm','㎡')], default='pyeong')
    floor = models.CharField('층수', max_length=20, blank=True)
    rent_manwon = models.PositiveBigIntegerField('월세 (만원)', null=True, blank=True)
    management_manwon = models.PositiveBigIntegerField('월 관리비 (만원)', null=True, blank=True)
    deposit_manwon = models.PositiveBigIntegerField('보증금 (만원)', null=True, blank=True)
    premium_manwon = models.PositiveBigIntegerField('권리금 (만원)', null=True, blank=True)
    reserve_manwon = models.PositiveBigIntegerField('별도로 확보할 운영자금 (만원)', null=True, blank=True)
    target_profit_manwon = models.PositiveBigIntegerField('목표 월 순이익 (만원)', null=True, blank=True, help_text='희망 목표이며 예측 수익이 아닙니다.')
    experience = models.CharField('창업·운영 경험', max_length=300, blank=True)
    can_cook = models.BooleanField('조리 가능', null=True, blank=True)
    opening_date = models.DateField('희망 오픈일', null=True, blank=True)
    radius_m = models.PositiveSmallIntegerField('매장 집계 반경', choices=[(300,'300m'),(500,'500m'),(1000,'1km')], default=500)
    target_ages = models.JSONField('주 고객 연령대', default=list, blank=True)
    preferred_area_types = models.JSONField('선호 상권', default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

class DataSource(models.Model):
    name = models.CharField('출처', max_length=200)
    url = models.URLField(blank=True)
    collected_on = models.DateField('수집일')
    note = models.TextField(blank=True)
    def __str__(self): return self.name

class CommercialArea(models.Model):
    code = models.CharField('공식 상권코드', max_length=30)
    version = models.CharField('경계 버전', max_length=40)
    name = models.CharField('상권명', max_length=100)
    area_type = models.CharField('상권유형', max_length=50)
    admin_code = models.CharField('행정구역코드', max_length=20)
    boundary = models.JSONField('GeoJSON Geometry (경도, 위도)', null=True, blank=True)
    effective_on = models.DateField('기준일')
    verified = models.BooleanField('코드·경계 검증 완료', default=False)
    source = models.ForeignKey(DataSource,on_delete=models.PROTECT)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['code','version'], name='unique_commercial_area_version')]
    def __str__(self): return f'{self.code} {self.name} ({self.version})'

class IndustryCode(models.Model):
    system = models.CharField('코드 체계·버전', max_length=50)
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    brand_category = models.CharField('검수된 브랜드 업종 대응', max_length=30, blank=True)
    verified = models.BooleanField(default=False)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['system','code'],name='unique_industry_system_code')]
    def __str__(self): return self.name

class AreaObservation(models.Model):
    area = models.ForeignKey(CommercialArea,on_delete=models.PROTECT)
    source = models.ForeignKey(DataSource,on_delete=models.PROTECT)
    period = models.CharField('기준기간 (예: 2026Q2)',max_length=20)
    unit = models.CharField('단위',max_length=30)
    class Meta: abstract=True

class PopulationStat(AreaObservation):
    kind = models.CharField('인구 종류',max_length=12,choices=[('floating','유동'),('resident','상주'),('worker','직장')])
    total = models.PositiveBigIntegerField('총 인구',null=True,blank=True)
    households = models.PositiveBigIntegerField('총 가구',null=True,blank=True)
    single_households = models.PositiveBigIntegerField('1인 가구',null=True,blank=True)
    by_age = models.JSONField('연령별 (미제공 항목은 null)',default=dict,blank=True)
    by_time = models.JSONField('시간대별',default=dict,blank=True)
    by_day = models.JSONField('요일별',default=dict,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['area','period','kind'],name='unique_area_population')]

class IndustrySales(AreaObservation):
    industry = models.ForeignKey(IndustryCode,on_delete=models.PROTECT)
    amount = models.PositiveBigIntegerField('매출액',null=True,blank=True)
    transactions = models.PositiveBigIntegerField('매출 건수',null=True,blank=True)
    by_age = models.JSONField(default=dict,blank=True)
    by_time = models.JSONField(default=dict,blank=True)
    by_day = models.JSONField(default=dict,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['area','period','industry'],name='unique_area_industry_sales')]

class StoreTrend(AreaObservation):
    industry = models.ForeignKey(IndustryCode,on_delete=models.PROTECT)
    operating = models.PositiveIntegerField(null=True,blank=True)
    opened = models.PositiveIntegerField(null=True,blank=True)
    closed = models.PositiveIntegerField(null=True,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['area','period','industry'],name='unique_area_store_trend')]

class PublicStore(models.Model):
    source = models.ForeignKey(DataSource,on_delete=models.PROTECT)
    external_id = models.CharField('원본 업소 식별자',max_length=100)
    name = models.CharField(max_length=200)
    industry = models.ForeignKey(IndustryCode,on_delete=models.PROTECT,null=True,blank=True)
    brand = models.ForeignKey('brands.Brand',on_delete=models.SET_NULL,null=True,blank=True)
    area = models.ForeignKey(CommercialArea,on_delete=models.PROTECT,null=True,blank=True)
    address = models.CharField(max_length=300)
    postcode = models.CharField(max_length=5,blank=True)
    latitude = ExactCoordinateField(validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude = ExactCoordinateField(validators=[MinValueValidator(-180),MaxValueValidator(180)])
    reference_on = models.DateField()
    raw = models.JSONField('원본 보존',default=dict,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['source','external_id','reference_on'],name='unique_public_store_snapshot')]

class Attractor(models.Model):
    area = models.ForeignKey(CommercialArea,on_delete=models.PROTECT)
    source = models.ForeignKey(DataSource,on_delete=models.PROTECT)
    kind = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    scale = models.DecimalField(max_digits=20,decimal_places=3,null=True,blank=True)
    unit = models.CharField(max_length=30,blank=True)
    reference_on = models.DateField()

class BrandOperation(models.Model):
    brand = models.OneToOneField('brands.Brand',on_delete=models.CASCADE,related_name='operation_conditions')
    source = models.ForeignKey(DataSource,on_delete=models.PROTECT)
    checked_on = models.DateField()
    price_min_krw = models.PositiveIntegerField(null=True,blank=True)
    price_max_krw = models.PositiveIntegerField(null=True,blank=True)
    channels = models.JSONField(default=list,blank=True)
    minimum_area_sqm = models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    required_staff = models.PositiveSmallIntegerField(null=True,blank=True)
    required_slots = models.JSONField(default=list,blank=True)
    staff_operation_allowed = models.BooleanField(null=True,blank=True)
    restrictions = models.TextField('출점 제한·본사 확인 사항',blank=True)
