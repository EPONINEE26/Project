from django.conf import settings
from django.db import models


def default_terms():
    return ['씨발', '시발', '씨팔', '씨바', '병신', '개새끼', '씹새끼', '좆', '지랄', '꺼져', '닥쳐', 'ㅅㅂ', 'ㅆㅂ', 'ㅂㅅ', 'fuck', 'fucking', 'shit', 'asshole', 'bitch']


# 데이터: 비속어·공개 제한 정책 → 게시물 필터·삭제 안내 문구
class ModerationPolicy(models.Model):
    enabled = models.BooleanField('비속어 자동 제거', default=True)
    blind_on_match = models.BooleanField('공개 글에서 탐지 시 1차 블라인드', default=True)
    blocked_terms = models.JSONField('제외 단어', default=default_terms, help_text='문자열 목록. 일반적인 비판 표현은 추가하지 마세요.')
    removed_message = models.CharField('2차 삭제 안내', max_length=200, default='일방적 비난 혹은 근거없는 욕설로 삭제되었습니다.')
    def clean(self):
        from django.core.exceptions import ValidationError
        if not isinstance(self.blocked_terms,list) or len(self.blocked_terms)>500 or any(not isinstance(term,str) or not term.strip() or len(term)>40 for term in self.blocked_terms):
            raise ValidationError({'blocked_terms':'40자 이내 문자열 목록을 입력하세요(최대 500개).'})
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    def __str__(self): return '사이트 공통 게시물 관리 정책'


# 데이터: 게시물 검토 작업 이력 → 관리자 검토 로그(일반 화면 비공개)
class ModerationEvent(models.Model):
    target_type = models.CharField(max_length=80)
    target_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=20)
    reason = models.CharField(max_length=200, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']


# 데이터: 공개 FAQ·분류·대상 → 고객센터·챗봇 답변 자료
class FAQ(models.Model):
    CATEGORIES = [('account', '회원·로그인'), ('brand', '브랜드·비교'), ('region', '지역·지도'), ('calculator', '회수 계산기'), ('owner', '점주 인증·커뮤니티'), ('partner', '본사 입점'), ('transfer', '양도양수'), ('policy', '게시물 관리')]
    category = models.CharField('분류', max_length=20, choices=CATEGORIES)
    audience = models.CharField('대상', max_length=10, choices=[('all','전체'),('member','일반회원'),('owner','점주'),('partner','본사')], default='all')
    question = models.CharField('질문', max_length=200, unique=True)
    answer = models.TextField('답변')
    question_en = models.CharField('영문 질문', max_length=250, blank=True)
    answer_en = models.TextField('영문 답변', blank=True)
    link = models.CharField('관련 페이지', max_length=200, blank=True, help_text='/로 시작하는 사이트 내부 경로')
    order = models.PositiveIntegerField('순서', default=0)
    is_published = models.BooleanField('공개', default=True)
    class Meta: ordering = ['order','id']
    def __str__(self): return self.question


# 데이터: 공개 공지 → 고객센터 공지 목록
class Notice(models.Model):
    title = models.CharField('제목', max_length=200)
    content = models.TextField('내용')
    is_published = models.BooleanField('공개', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return self.title


# 데이터: 회원 문의·관리자 답변 → 내 문의 목록/상세
class SupportTicket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    category = models.CharField('문의 분류', max_length=20, choices=FAQ.CATEGORIES)
    title = models.CharField('제목', max_length=120)
    content = models.TextField('문의 내용', max_length=3000)
    status = models.CharField('처리 상태', max_length=10, choices=[('open','접수'),('answered','답변 완료'),('closed','종료')], default='open')
    answer = models.TextField('관리자 답변', blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ['-created_at']
    def __str__(self): return self.title
