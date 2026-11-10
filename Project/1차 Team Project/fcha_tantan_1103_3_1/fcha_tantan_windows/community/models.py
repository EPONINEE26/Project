from django.conf import settings
from django.db import models
from .closure_models import ClosureVerification, ClosureReview


class ModeratedContent(models.Model):
    moderation_state=models.CharField('검토 상태',max_length=10,choices=[('visible','공개'),('blind','1차 블라인드'),('removed','2차 삭제 안내')],default='visible')
    moderation_reason=models.CharField('검토 사유',max_length=200,blank=True)
    moderation_original=models.JSONField('검토용 원문(관리자 전용)',default=dict,blank=True,editable=False)
    is_demo=models.BooleanField('예시 콘텐츠',default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: abstract=True
    @property
    def visibility_message(self):
        from core.moderation import public_message
        return public_message(self)


class Post(ModeratedContent):
    TOPICS=[('free','자유 이야기'),('operation','매장 운영'),('marketing','홍보·마케팅'),('question','점주 질문'),('transfer','양도·양수 경험')]
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='community_posts')
    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT)
    topic=models.CharField('분류',max_length=12,choices=TOPICS,default='free')
    title=models.CharField('제목',max_length=120)
    content=models.TextField('내용',max_length=10000)
    class Meta:ordering=['-created_at']
    def __str__(self):return self.title
    @property
    def public_title(self):return self.title if self.moderation_state=='visible' else self.visibility_message


class Comment(ModeratedContent):
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='community_comments')
    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT)
    content=models.TextField('댓글',max_length=2000)
    class Meta:ordering=['created_at']
    def __str__(self):return f'{self.post_id}번 글 댓글 {self.pk}'


class Report(models.Model):
    reporter=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    post=models.ForeignKey(Post,on_delete=models.CASCADE,null=True,blank=True)
    comment=models.ForeignKey(Comment,on_delete=models.CASCADE,null=True,blank=True)
    reason=models.CharField('신고 사유',max_length=300)
    processed=models.BooleanField('검토 완료',default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints=[models.CheckConstraint(condition=(models.Q(post__isnull=False,comment__isnull=True)|models.Q(post__isnull=True,comment__isnull=False)),name='report_one_target'),
                     models.UniqueConstraint(fields=['reporter','post'],name='unique_post_report'),models.UniqueConstraint(fields=['reporter','comment'],name='unique_comment_report')]
