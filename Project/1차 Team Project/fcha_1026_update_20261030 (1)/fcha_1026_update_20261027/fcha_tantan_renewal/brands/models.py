from django.db import models

class Brand(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=30, db_index=True)
    tagline = models.CharField(max_length=200, blank=True)
    english_name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    image = models.CharField(max_length=100, default='coffee.jpg')
    color = models.CharField(max_length=7, default='#f4ef76')
    initial_cost_krw = models.PositiveBigIntegerField(null=True, blank=True)
    costs = models.JSONField(default=dict, blank=True)
    area_sqm = models.FloatField(default=33, null=True, blank=True)
    is_demo = models.BooleanField(default=True)
    # 프차탄탄 JSON(정보공개서 가공본)에서 가져온 식별 정보입니다.
    official_brand_id = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=100, blank=True)
    source_category = models.CharField(max_length=50, blank=True)
    category_major = models.CharField('업종 대분류', max_length=10, blank=True, db_index=True)
    def save(self, *args, **kwargs):
        if not self.category_major:
            from .constants import LEGACY_MAJOR
            self.category_major = LEGACY_MAJOR.get(self.category, '')
        super().save(*args, **kwargs)
    def __str__(self): return self.name

class AnnualStat(models.Model):
    brand = models.ForeignKey(Brand,on_delete=models.CASCADE,related_name='annual_stats')
    year = models.PositiveSmallIntegerField()
    stores = models.PositiveIntegerField(null=True,blank=True)
    opened = models.PositiveIntegerField(null=True,blank=True)
    closed = models.PositiveIntegerField(null=True,blank=True)
    annual_sales_krw = models.PositiveBigIntegerField(null=True,blank=True)
    source_label = models.CharField(max_length=200)
    source_url = models.URLField(blank=True)
    updated_at = models.DateField(auto_now=True)
    # JSON 연동 필드. 값이 없으면 null(0으로 채우지 않음)입니다.
    source_accounting_year = models.PositiveSmallIntegerField(null=True, blank=True)
    direct_stores = models.PositiveIntegerField(null=True, blank=True)
    total_stores = models.PositiveIntegerField(null=True, blank=True)
    contract_ended = models.PositiveIntegerField(null=True, blank=True)
    contract_terminated = models.PositiveIntegerField(null=True, blank=True)
    ownership_changed = models.PositiveIntegerField(null=True, blank=True)
    sales_min_krw = models.PositiveBigIntegerField(null=True, blank=True)
    sales_max_krw = models.PositiveBigIntegerField(null=True, blank=True)
    sales_status = models.CharField(max_length=30, blank=True)
    startup_cost_krw = models.PositiveBigIntegerField(null=True, blank=True)
    startup_cost_breakdown = models.JSONField(default=dict, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['brand','year'],name='unique_brand_year')]
        ordering = ['year']
    def __str__(self): return f'{self.brand.name} / {self.year}'

class RegionalStat(models.Model):
    annual_stat = models.ForeignKey(AnnualStat,on_delete=models.CASCADE,related_name='regional_stats')
    region = models.CharField(max_length=30)
    stores = models.PositiveIntegerField(null=True,blank=True)
    # 지역 매출은 원자료가 범위값이라 하한/상한만 저장합니다.
    sales_min_krw = models.PositiveBigIntegerField(null=True, blank=True)
    sales_max_krw = models.PositiveBigIntegerField(null=True, blank=True)
    sales_status = models.CharField(max_length=30, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['annual_stat','region'],name='unique_year_region')]


class AreaSales(models.Model):
    """공시 원단위가 확인된 평당 매출만 연결합니다. 기존 통계는 수정하지 않습니다."""
    annual_stat = models.OneToOneField(AnnualStat, on_delete=models.CASCADE, related_name='area_sales')
    annual_sales_per_pyeong_krw = models.PositiveBigIntegerField(null=True, blank=True)
    source_label = models.CharField(max_length=250)
    source_url = models.URLField(blank=True)
    def __str__(self): return str(self.annual_stat)


class AdSlot(models.Model):
    """메인·브랜드 탐색 카드 최상단 1·2번 광고 자리. 정렬과 무관하게 맨 앞에 노출됩니다."""
    POSITIONS = [(1, '1번 자리'), (2, '2번 자리')]
    position = models.PositiveSmallIntegerField(choices=POSITIONS)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='ad_slots')
    advertiser = models.CharField('광고주', max_length=100, blank=True)
    starts_on = models.DateField('노출 시작일')
    ends_on = models.DateField('노출 종료일')
    is_active = models.BooleanField('노출', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['position', '-starts_on']
    def __str__(self): return f'{self.position}번 · {self.brand.name} ({self.starts_on}~{self.ends_on})'


def contract_upload_path(instance, filename):
    # 원래 파일명은 개인정보가 들어갈 수 있어 확장자만 남깁니다.
    import uuid
    from pathlib import Path
    return f'contracts/{instance.user_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class OwnerVerification(models.Model):
    """가맹 계약서 인증. 관리자 승인 + 계약 시작 6개월 경과 시 후기 작성 가능."""
    STATUS = [('pending', '검토 중'), ('approved', '승인'), ('rejected', '반려')]
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='owner_verifications')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='owner_verifications')
    store_name = models.CharField('가맹점명', max_length=100)
    contract_start_date = models.DateField('가맹계약 시작일')
    contract_end_date = models.DateField('가맹계약 종료일', null=True, blank=True)
    contract_file = models.FileField('가맹계약서 사본', upload_to=contract_upload_path)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    reject_reason = models.CharField('반려 사유', max_length=200, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-submitted_at']
    def __str__(self): return f'{self.user} · {self.brand.name} · {self.get_status_display()}'


class BrandReview(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='brand_reviews')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='reviews')
    verification = models.ForeignKey(OwnerVerification, on_delete=models.PROTECT, related_name='reviews')
    rating = models.PositiveSmallIntegerField('별점')
    title = models.CharField('제목', max_length=80)
    content = models.TextField('후기')
    is_hidden = models.BooleanField('숨김(관리자)', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['user', 'brand'], name='unique_user_brand_review'),
                       models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name='review_rating_1_5')]
    def __str__(self): return f'{self.brand.name} · {self.rating}점'
