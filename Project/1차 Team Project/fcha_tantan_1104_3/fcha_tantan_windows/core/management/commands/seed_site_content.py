from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import FAQ,Notice,ModerationPolicy
from core.seed_data import FAQ_DATA,DEMO_POSTS
from community.models import Post,Comment
from brands.models import Brand


class Command(BaseCommand):
    help='도움말과 명확히 표시된 커뮤니티 예시 10개를 최초 1회 준비합니다.'
    def add_arguments(self,parser):parser.add_argument('--no-demo',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        ModerationPolicy.objects.get_or_create(pk=1)
        for order,(category,audience,question,answer,question_en,answer_en,link) in enumerate(FAQ_DATA):
            FAQ.objects.get_or_create(question=question,defaults=dict(category=category,audience=audience,answer=answer,question_en=question_en,answer_en=answer_en,link=link,order=order))
        Notice.objects.get_or_create(title='점주 커뮤니티와 지역 지도 이용 안내',defaults={'content':'점주 인증 승인 후 글과 댓글을 작성할 수 있습니다. 예시로 표시된 콘텐츠는 화면 확인용 더미이며 실제 점주 의견이 아닙니다. 지도에는 공개에 동의한 등록 매장 또는 카카오 검색 결과가 표시됩니다.'})
        if options['no_demo']:return
        User=get_user_model()
        if User.objects.filter(username='tantan_demo_owner_01').exists():
            self.stdout.write('도움말 준비 완료 · 기존 커뮤니티 콘텐츠 유지');return
        if Post.objects.exists():return
        brands=list(Brand.objects.filter(is_demo=False).order_by('id')[:10]) or list(Brand.objects.order_by('id')[:10])
        if not brands:return
        nicknames=['오픈일기','오늘도운영','골목사장','차분한준비','좋은하루','작은노트','동선연구','친절한답글','다음시작','꾸준한점주']
        users=[]
        for i,nickname in enumerate(nicknames):
            user=User(username=f'tantan_demo_owner_{i+1:02d}',first_name=nickname,is_active=False)
            user.set_unusable_password();user.save();users.append(user)
        for i,(topic,title,content,comment) in enumerate(DEMO_POSTS):
            post=Post.objects.create(author=users[i],brand=brands[i%len(brands)],topic=topic,title=title,content=content,is_demo=True)
            Comment.objects.create(post=post,author=users[(i+1)%10],brand=brands[(i+1)%len(brands)],content=comment,is_demo=True)
        self.stdout.write(self.style.SUCCESS('도움말 20개 · 예시 게시글 10개 · 예시 댓글 10개 준비 완료'))
