from django.conf import settings
from django.db import models
from pathlib import Path
from uuid import uuid4
from django.core.validators import FileExtensionValidator
from brands.constants import REGIONS

REGION_CHOICES = [(r, r) for r in REGIONS]


def transfer_document_path(instance, filename):
    return f'transfer_documents/{instance.listing_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


# 데이터: 회원 등록 매장·후보지 위치 → 내 매장 목록/상세·공개 점주 지도
class StoreLocation(models.Model):
    """매장(예정지 포함) 위치. 주소 검색 + 지도 좌표(카카오 지도 키가 있을 때)로 설정합니다."""
    STATUS = [('planned', '오픈 예정/후보지'), ('operating', '운영 중'), ('transfer', '양도 예정')]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='store_locations')
    brand = models.ForeignKey('brands.Brand', on_delete=models.SET_NULL, null=True, blank=True, related_name='store_locations')
    store_name = models.CharField('매장명/후보지명', max_length=100)
    status = models.CharField('상태', max_length=10, choices=STATUS, default='planned')
    is_public = models.BooleanField('지역 지도에 매장 위치 공개', default=False, help_text='점주 인증이 승인된 운영 매장만 표시됩니다. 체크하면 매장 좌표가 공개됩니다.')
    postcode = models.CharField('우편번호', max_length=5, blank=True)
    address = models.CharField('주소', max_length=200)
    address_detail = models.CharField('상세주소', max_length=100, blank=True)
    sido = models.CharField('시·도', max_length=10, choices=REGION_CHOICES)
    sigungu = models.CharField('시·군·구', max_length=30, blank=True)
    dong = models.CharField('읍·면·동', max_length=30, blank=True)
    latitude = models.DecimalField('위도', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('경도', max_digits=9, decimal_places=6, null=True, blank=True)
    area_pyeong = models.DecimalField('면적(평)', max_digits=6, decimal_places=1, null=True, blank=True)
    opened_on = models.DateField('오픈(예정)일', null=True, blank=True)
    memo = models.TextField('메모', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-updated_at']
    def __str__(self): return self.store_name

    @property
    def category(self):
        """Return the linked brand's category, or an empty string without a brand."""
        return self.brand.category if self.brand_id is not None else ''


# 데이터: 회원 매장별 유동인구 측정 기록 → 내 매장 상세(공공 상권·자치구 통계와 별개)
class FloatingPopulation(models.Model):
    """유동인구 기록. 직접 계측·공공데이터 등 출처를 함께 남겨 추정값과 구분합니다."""
    TIME_SLOTS = [('all', '하루 전체'), ('06-11', '06~11시'), ('11-14', '11~14시'), ('14-17', '14~17시'),
                  ('17-21', '17~21시'), ('21-24', '21~24시'), ('00-06', '00~06시')]
    DAY_TYPES = [('all', '전체'), ('weekday', '평일'), ('weekend', '주말')]
    METHODS = [('manual', '직접 계측'), ('public', '공공데이터'), ('vendor', '상권분석 업체'), ('other', '기타')]
    store = models.ForeignKey(StoreLocation, on_delete=models.CASCADE, related_name='populations')
    measured_on = models.DateField('측정일(기준일)')
    day_type = models.CharField('요일 구분', max_length=10, choices=DAY_TYPES, default='all')
    time_slot = models.CharField('시간대', max_length=10, choices=TIME_SLOTS, default='all')
    count = models.PositiveIntegerField('유동인구(명)')
    method = models.CharField('측정 방법', max_length=10, choices=METHODS, default='manual')
    source_note = models.CharField('출처·메모', max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-measured_on', 'time_slot']
    def __str__(self): return f'{self.store} {self.measured_on} {self.get_time_slot_display()} {self.count}명'


# 데이터: 양도양수 매물·금액·공개 상태 → 매물 목록/상세·내 매물
class TransferListing(models.Model):
    """양도양수 매물. 금액은 모두 등록자가 입력한 값이며 플랫폼이 검증한 수치가 아닙니다."""
    CONTRACT_STATUS = [('active', '가맹계약 기간 중'), ('ending', '계약 만료 예정(6개월 이내)'), ('ended', '계약 만료')]
    STATUS = [('open', '거래 가능'), ('negotiating', '협의 중'), ('closed', '거래 완료')]
    approval_status = models.CharField('승인 상태', max_length=10, default='pending',
        choices=[('pending', '승인 대기'), ('approved', '승인 완료'), ('rejected', '반려')])
    approval_note = models.TextField('승인·반려 메모', blank=True)
    reviewed_at = models.DateTimeField('검토일', null=True, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='검토 관리자',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_transfer_listings')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transfer_listings')
    brand = models.ForeignKey('brands.Brand', on_delete=models.CASCADE, related_name='transfer_listings')
    store = models.ForeignKey(StoreLocation, on_delete=models.SET_NULL, null=True, blank=True, related_name='transfer_listings')
    title = models.CharField('제목', max_length=80)
    address = models.CharField('매장 주소', max_length=200, blank=True)
    address_detail = models.CharField('상세주소', max_length=100, blank=True)
    latitude = models.DecimalField('위도', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('경도', max_digits=9, decimal_places=6, null=True, blank=True)
    floor = models.CharField('층수', max_length=20, blank=True)
    management_fee_manwon = models.PositiveIntegerField('월 관리비(만원)', null=True, blank=True)
    parking_spaces = models.PositiveSmallIntegerField('주차 가능 대수', null=True, blank=True)
    available_from = models.DateField('인수 가능일', null=True, blank=True)
    facilities = models.CharField('포함 시설·집기', max_length=300, blank=True)
    moderation_state = models.CharField('검토 상태', max_length=10, choices=[('visible','공개'),('blind','1차 블라인드'),('removed','2차 삭제 안내')], default='visible')
    moderation_reason = models.CharField('검토 사유', max_length=200, blank=True)
    moderation_original = models.JSONField('검토용 원문', default=dict, blank=True, editable=False)
    sido = models.CharField('시·도', max_length=10, choices=REGION_CHOICES)
    sigungu = models.CharField('시·군·구', max_length=30)
    dong = models.CharField('읍·면·동', max_length=30, blank=True)
    area_pyeong = models.DecimalField('면적(평)', max_digits=6, decimal_places=1, null=True, blank=True)
    premium_manwon = models.PositiveIntegerField('권리금(만원)', null=True, blank=True)
    deposit_manwon = models.PositiveIntegerField('보증금(만원)', null=True, blank=True)
    monthly_rent_manwon = models.PositiveIntegerField('월세(만원)', null=True, blank=True)
    monthly_sales_manwon = models.PositiveIntegerField('최근 월평균 매출(만원)', null=True, blank=True)
    monthly_profit_manwon = models.IntegerField('최근 월평균 순이익(만원)', null=True, blank=True)
    contract_status = models.CharField('가맹계약 상태', max_length=10, choices=CONTRACT_STATUS, default='active')
    contract_end_date = models.DateField('가맹계약 종료일', null=True, blank=True)
    description = models.TextField('상세 설명')
    status = models.CharField('거래 상태', max_length=12, choices=STATUS, default='open')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return self.title


# 데이터: 매물 문의·연락처 공개 동의 → 매물 상세의 문의 내역
class TransferDocument(models.Model):
    listing = models.ForeignKey(TransferListing, on_delete=models.CASCADE, related_name='documents')
    file = models.FileField('증빙 서류', upload_to=transfer_document_path,
        validators=[FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])])
    original_name = models.CharField('파일명', max_length=255)
    uploaded_at = models.DateTimeField('첨부일', auto_now_add=True)

    class Meta:
        verbose_name = '양도양수 증빙 서류'
        verbose_name_plural = '양도양수 증빙 서류'

    def __str__(self):
        return self.original_name


class TransferInquiry(models.Model):
    listing = models.ForeignKey(TransferListing, on_delete=models.CASCADE, related_name='inquiries')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transfer_inquiries')
    kind = models.CharField('문의 유형', max_length=10, choices=[('acquire', '양수 희망'), ('question', '조건 문의'), ('offer', '가격 제안')], default='acquire')
    message = models.TextField('문의 내용', max_length=1000)
    share_phone = models.BooleanField('내 휴대전화 번호를 등록자에게 공개', default=False)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return f'{self.listing} ← {self.sender}'

from .analysis_models import (StartupCondition, DataSource, CommercialArea, IndustryCode, PopulationStat, IndustrySales, StoreTrend, PublicStore, Attractor, BrandOperation)


class TransferChatMessage(models.Model):
    inquiry = models.ForeignKey(TransferInquiry, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField('메시지', max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
