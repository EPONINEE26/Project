from django.db import models

class Brand(models.Model):
    slug = models.SlugField(unique=True) # SlugField는 기본적으로 영문 소문자, 숫자, 하이픈(-), 밑줄(_) 등을 사용가능
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=30)
    tagline = models.CharField(max_length=200, blank=True)
    english_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=100, default='coffee.jpg')
    color = models.CharField(max_length=7, default='#f4ef76')
    initial_cost_krw = models.PositiveBigIntegerField(null=True, blank=True)
    costs = models.JSONField(default=dict)
    area_sqm = models.FloatField(default=33)
    is_demo = models.BooleanField(default=True)
    def __str__(self): return self.name


#  연간 평당 매출
class AnnualStat(models.Model):
    brand = models.ForeignKey(Brand,on_delete=models.CASCADE,related_name='annual_stats')
    year = models.PositiveSmallIntegerField()
    stores = models.PositiveIntegerField(null=True,blank=True)
    direct_stores = models.PositiveIntegerField(null=True, blank=True) #추가
    total_stores = models.PositiveIntegerField(null=True, blank=True) #추가
    opened = models.PositiveIntegerField(null=True,blank=True)
    closed = models.PositiveIntegerField(null=True,blank=True)
    annual_sales_krw = models.PositiveBigIntegerField(null=True,blank=True)
    source_label = models.CharField(max_length=200)
    source_url = models.URLField(blank=True)
    updated_at = models.DateField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['brand','year'],name='unique_brand_year')]
        ordering = ['year']
    def __str__(self): return f'{self.brand.name} / {self.year}'

class RegionalStat(models.Model):
    annual_stat = models.ForeignKey(AnnualStat,on_delete=models.CASCADE,related_name='regional_stats')
    region = models.CharField(max_length=30)
    stores = models.PositiveIntegerField(null=True,blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['annual_stat','region'],name='unique_year_region')]


class AreaSales(models.Model):
    """공시 원단위가 확인된 평당 매출만 연결합니다. 기존 통계는 수정하지 않습니다."""
    annual_stat = models.OneToOneField(AnnualStat, on_delete=models.CASCADE, related_name='area_sales')
    annual_sales_per_pyeong_krw = models.PositiveBigIntegerField(null=True, blank=True)
    source_label = models.CharField(max_length=250)
    source_url = models.URLField(blank=True)
    def __str__(self): return str(self.annual_stat)

# ===== 19개 브랜드 업종별 창업비용 및 출처 관리 (추가) =====
# 업종별 창업비용 항목
class CostItem(models.Model):
    """업종별로 사용할 비용 항목 (예: 카페/커피머신)."""
    category = models.CharField(max_length=30)
    code = models.SlugField(max_length=80)
    name = models.CharField(max_length=100)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['category', 'code'], name='unique_category_cost_code')]
        ordering = ['category', 'display_order', 'id']

    def __str__(self):
        return f'{self.category} / {self.name}'

# 데이터 출처 및 검증 상태
class DataSource(models.Model):
    """수치의 근거 및 검증 상태. 원본 위치와 가공본 위치를 구분해 기록."""
    STATUS_CHOICES = [
        ('verified', '원자료 확인'),
        ('needs_review', '출처 확인 필요'),
        ('estimated', '추정값'),
        ('conflict', '자료 간 충돌'),
    ]
    source_name = models.CharField(max_length=255)
    source_url = models.URLField(blank=True)
    original_file = models.CharField(max_length=255, blank=True)
    original_sheet = models.CharField(max_length=100, blank=True)
    original_cell = models.CharField(max_length=100, blank=True)
    json_path = models.CharField(max_length=500, blank=True)
    verification_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='needs_review')
    note = models.TextField(blank=True)

    def __str__(self):
        return self.source_name

#  브랜드별 창업비용 금액
class StartupCost(models.Model):
    """브랜드/연도/비용항목별 금액. 비공개/미제공은 NULL로 유지."""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='startup_cost_items')
    year = models.PositiveSmallIntegerField()
    item = models.ForeignKey(CostItem, on_delete=models.PROTECT, related_name='brand_costs')
    amount_krw = models.PositiveBigIntegerField(null=True, blank=True)
    source = models.ForeignKey(DataSource, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['brand', 'year', 'item'], name='unique_brand_year_cost_item')]
        ordering = ['brand', 'year', 'item']

    def __str__(self):
        return f'{self.brand.name} / {self.year} / {self.item.name}'
