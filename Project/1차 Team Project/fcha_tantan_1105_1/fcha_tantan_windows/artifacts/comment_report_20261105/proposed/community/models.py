from django.conf import settings
from django.db import models


# 데이터: 게시물 공개/블라인드 상태 공통 필드 → 게시글·댓글 추상 기반(별도 테이블 없음)
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


# 데이터: 점주 게시글 → 커뮤니티 목록·상세·작성자 글 목록
class Post(ModeratedContent):
    # TOPICS=[('free','자유 이야기'),('operation','매장 운영'),('marketing','홍보·마케팅'),('question','점주 질문'),('transfer','양도·양수 경험')]
    TOPICS=[('free','자유 이야기'),('operation','매장 운영'),('marketing','홍보·마케팅'),('question','점주 질문'),('transfer','양도·양수 경험'),('store_tips','매장 준비 꿀팁')]
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='community_posts')
    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT)    
    # 게시글마다 선택한 분류를 최대 12글자로 저장하며, choices=TOPICS로 선택 목록을 연결하고 기본값은 자유 이야기인 free로 지정
    topic=models.CharField('분류',max_length=12,choices=TOPICS,default='free')
    title=models.CharField('제목',max_length=120)
    content=models.TextField('내용',max_length=10000)
    class Meta:ordering=['-created_at']
    def __str__(self):return self.title
    @property
    def public_title(self):return self.title if self.moderation_state=='visible' else self.visibility_message


# 데이터: 게시글 댓글 → 커뮤니티 상세 댓글 목록
# class Comment(ModeratedContent):
#     brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT,null=True,blank=True)
#     post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments')
#     author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='community_comments')
#     brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT)
#     content=models.TextField('댓글',max_length=2000)
#     class Meta:ordering=['created_at']
#     def __str__(self):return f'{self.post_id}번 글 댓글 {self.pk}'


# 꿀팁 댓글은 브랜드 선택 없이 내용만 입력받으며, 세 줄 높이의 입력칸에 최대 2,000글자 제한과 안내 문구를 지정
class Comment(ModeratedContent):
    post=models.ForeignKey(Post,on_delete=models.CASCADE,related_name='comments')
    author=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='community_comments')
    # 댓글에 브랜드를 연결하되 null=True로 DB의 빈 값을 허용하고 blank=True로 입력 생략을 허용하여 일반회원도 댓글을 작성하게 함
    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT,null=True,blank=True)
    content=models.TextField('댓글',max_length=2000)
    class Meta:ordering=['created_at']
    def __str__(self):return f'{self.post_id}번 글 댓글 {self.pk}'


# 데이터: 게시글·댓글 신고 → 관리자 신고 검토 목록
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
