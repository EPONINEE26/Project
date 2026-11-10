from django.conf import settings
from django.db import models
class SavedBrand(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    brand = models.ForeignKey('brands.Brand', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'brand'], name='unique_user_saved_brand')]


class MemberProfile(models.Model):
    """회원가입 추가 정보와 동의 기록. 주민등록번호는 앞 6자리(생년월일)만 날짜로 저장합니다."""
    PURPOSES = [('living', '생계형 창업(직접 운영)'), ('invest', '투자형 창업(오토 운영)'),
                ('convert', '업종 전환'), ('side', '부업·소자본 창업'), ('other', '기타')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='member_profile')
    birth_date = models.DateField('생년월일', null=True, blank=True)  # 2026-10-26 이후 회원가입에서 받지 않음(예전 값만 보관)
    email_verified_at = models.DateTimeField('이메일 인증 일시', null=True, blank=True)
    wants_startup = models.BooleanField('창업 목적 가입', null=True, blank=True)
    phone = models.CharField('휴대전화', max_length=13, blank=True)
    postcode = models.CharField('우편번호', max_length=5, blank=True)
    address = models.CharField('주소', max_length=200, blank=True)
    address_detail = models.CharField('상세주소', max_length=100, blank=True)
    startup_purpose = models.CharField('창업 목적', max_length=10, choices=PURPOSES, blank=True)
    budget_manwon = models.PositiveIntegerField('창업 예산(만원)', null=True, blank=True)
    target_monthly_sales_manwon = models.PositiveIntegerField('목표 월 매출(만원)', null=True, blank=True)
    desired_region = models.CharField('희망 지역', max_length=10, blank=True)
    desired_category = models.CharField('희망 업종', max_length=10, blank=True)
    agree_privacy_at = models.DateTimeField('개인정보 수집·이용 동의 일시', null=True, blank=True)
    agree_marketing = models.BooleanField('마케팅 정보 수신 동의', default=False)
    agree_proposal = models.BooleanField('브랜드 사업제안 수신(정보제공) 동의', default=False)
    agree_proposal_at = models.DateTimeField(null=True, blank=True)
    signup_source = models.CharField(max_length=10, default='local')
    is_complete = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return f'{self.user} 프로필'


class EmailVerification(models.Model):
    """이메일 인증번호. 번호는 해시로만 저장하고 10분 뒤 만료, 5회 틀리면 다시 받아야 합니다."""
    email = models.EmailField(db_index=True)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return f'{self.email} ({"인증됨" if self.verified_at else "대기"})'
