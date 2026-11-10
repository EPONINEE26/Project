from django.conf import settings
from django.db import models
from brands.models import contract_upload_path


# 데이터: 본사 서비스 요금제 → 입점/광고 요금제 화면
class PartnerPlan(models.Model):
    """브랜드(가맹본부)용 서비스 요금제. 금액·구성은 관리자 페이지에서 수정합니다."""
    name = models.CharField('요금제명', max_length=40)
    order = models.PositiveSmallIntegerField('표시 순서', default=0)
    monthly_price_krw = models.PositiveIntegerField('월 요금(원, VAT 별도)', null=True, blank=True, help_text='비우면 “별도 협의”로 표시')
    summary = models.CharField('한 줄 설명', max_length=120)
    features = models.JSONField('포함 기능', default=list, help_text='["기능1", "기능2"] 형식')
    monthly_proposal_limit = models.PositiveIntegerField('월 사업제안 발송 한도', default=0)
    includes_ad_slot = models.BooleanField('상단 광고 자리 포함', default=False)
    is_highlighted = models.BooleanField('추천 표시', default=False)
    is_active = models.BooleanField('노출', default=True)
    is_example = models.BooleanField('예시 요금(확정 전)', default=True)
    class Meta:
        ordering = ['order', 'id']
    def __str__(self): return self.name


# 데이터: 본사 입점·광고 문의 접수 → 관리자 문의 목록
class PartnerInquiry(models.Model):
    STATUS = [('new', '접수'), ('contacted', '연락 완료'), ('closed', '종료')]
    company = models.CharField('회사명(가맹본부)', max_length=100)
    brand_name = models.CharField('브랜드명', max_length=100)
    contact_name = models.CharField('담당자명', max_length=30)
    phone = models.CharField('연락처', max_length=13)
    email = models.EmailField('이메일')
    plan = models.ForeignKey(PartnerPlan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='관심 요금제')
    ad_position = models.PositiveSmallIntegerField('광고 구좌', choices=[(1, 'AD 1번 구좌'), (2, 'AD 2번 구좌')], null=True, blank=True)
    cpc_bid_krw = models.PositiveIntegerField('희망 CPC(원/클릭)', null=True, blank=True)
    message = models.TextField('문의 내용', blank=True)
    agree_privacy_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return f'{self.company} · {self.brand_name}'


# 데이터: 본사 계정·소속 브랜드·승인 상태 → 본사 신청·사업제안 접근 확인
class PartnerAccount(models.Model):
    """브랜드 파트너 계정. 관리자가 승인해야 예비창업자 사업제안 기능을 쓸 수 있습니다."""
    STATUS = [('pending', '승인 대기'), ('approved', '승인'), ('rejected', '반려')]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='partner_account')
    brand = models.ForeignKey('brands.Brand', on_delete=models.CASCADE, related_name='partner_accounts')
    company = models.CharField('회사명', max_length=100)
    contact_name = models.CharField('담당자명', max_length=30)
    contact_phone = models.CharField('담당자 연락처', max_length=13)
    business_number = models.CharField('사업자등록번호', max_length=12)
    plan = models.ForeignKey(PartnerPlan, on_delete=models.SET_NULL, null=True, blank=True)
    business_file = models.FileField('사업자등록증', upload_to=contract_upload_path, blank=True)
    authorization_file = models.FileField('본사 재직·권한 증빙', upload_to=contract_upload_path, blank=True)
    document_check = models.JSONField('서류 사전점검(진위 판단 아님)', default=dict, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    def __str__(self): return f'{self.company} · {self.brand.name} · {self.get_status_display()}'
    @property
    def is_approved(self): return self.status == 'approved'


# 데이터: 본사→회원 사업제안·수락 상태 → 제안 발송 목록·회원 수신함
class BusinessProposal(models.Model):
    """브랜드 → 예비창업자 사업제안. 연락처는 회원이 수락한 경우에만 브랜드에 공개됩니다."""
    STATUS = [('sent', '확인 전'), ('accepted', '수락(연락처 공개)'), ('declined', '거절')]
    partner = models.ForeignKey(PartnerAccount, on_delete=models.CASCADE, related_name='proposals')
    member = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_proposals')
    title = models.CharField('제목', max_length=80)
    message = models.TextField('제안 내용', max_length=2000)
    status = models.CharField(max_length=10, choices=STATUS, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self): return f'{self.partner.brand.name} → {self.member} ({self.get_status_display()})'
