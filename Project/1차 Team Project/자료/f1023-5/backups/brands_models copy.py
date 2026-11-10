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
