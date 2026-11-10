"""점주 이야기의 매장 준비 꿀팁과 일반회원 댓글 권한 검증."""
from datetime import date, timedelta
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse, resolve, Resolver404
from django.utils import timezone
from brands.models import Brand, OwnerVerification
from community.models import Post, Comment, Report, ClosureReview, ClosureVerification


class OwnerTipsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users=get_user_model()
        cls.owner=users.objects.create_user(username='tips-owner',first_name='검증점주')
        cls.member=users.objects.create_user(username='tips-member',first_name='일반독자')
        cls.other=users.objects.create_user(username='tips-other')
        cls.brand=Brand.objects.create(slug='tips-test',name='검증브랜드',category='카페',is_demo=False)
        cls.verification=OwnerVerification.objects.create(user=cls.owner,brand=cls.brand,store_name='검증점',contract_start_date=date(2020,1,1),contract_file='audit/contract.pdf',status='approved')
        cls.tips=Post.objects.create(author=cls.owner,brand=cls.brand,topic='store_tips',title='매장 준비 경험',content='준비 과정을 공유합니다.')
        cls.regular=Post.objects.create(author=cls.owner,brand=cls.brand,topic='free',title='검증용기존분류게시글',content='기존 게시판')

    def login(self,user):
        self.client.force_login(user)

    def comment(self,user=None,post=None,content='준비 과정이 궁금합니다.',**extra):
        if user:
            self.login(user)
        return self.client.post(reverse('community:comment_create',args=[(post or self.tips).pk]),{'content':content,**extra})

    def test_tips_is_last_and_closure_is_absent(self):
        self.assertEqual(Post.TOPICS[-1],('store_tips','매장 준비 꿀팁'))
        response=self.client.get(reverse('community:index'))
        self.assertContains(response,'매장 준비 꿀팁')
        self.assertNotContains(response,'폐점주 커뮤니티')
        self.assertNotContains(response,'/community/closure/')
        self.assertGreater(response.content.decode().index('>매장 준비 꿀팁</a>'),response.content.decode().index('>양도·양수 경험</a>'))

    def test_tips_filter(self):
        response=self.client.get(reverse('community:index'),{'topic':'store_tips'})
        self.assertEqual(list(response.context['page_obj']),[self.tips])
        self.assertContains(response,self.tips.title)
        self.assertNotContains(response,self.regular.title)

    def test_owner_can_write_tips(self):
        self.login(self.owner)
        response=self.client.post(reverse('community:new'),{'brand':self.brand.pk,'topic':'store_tips','title':'새 준비 팁','content':'운영 준비 경험입니다.'})
        self.assertEqual(response.status_code,302)
        post=Post.objects.get(title='새 준비 팁')
        self.assertEqual(post.topic,'store_tips')
        self.assertEqual(post.author,self.owner)

    def test_general_member_cannot_write_post(self):
        self.login(self.member)
        before=Post.objects.count()
        response=self.client.post(reverse('community:new'),{'brand':self.brand.pk,'topic':'store_tips','title':'허용 안 됨','content':'본문'})
        self.assertRedirects(response,reverse('community:verify'))
        self.assertEqual(Post.objects.count(),before)

    def test_expired_owner_cannot_write(self):
        self.verification.contract_end_date=timezone.localdate()-timedelta(days=1)
        self.verification.save()
        self.login(self.owner)
        response=self.client.post(reverse('community:new'),{'brand':self.brand.pk,'topic':'store_tips','title':'만료','content':'본문'})
        self.assertRedirects(response,reverse('community:verify'))

    def test_general_member_sees_content_only_comment_form(self):
        self.login(self.member)
        response=self.client.get(reverse('community:detail',args=[self.tips.pk]))
        self.assertTrue(response.context['can_comment'])
        self.assertEqual(list(response.context['form'].fields),['content'])
        self.assertContains(response,'댓글 등록')

    def test_member_comment_has_no_fake_brand(self):
        response=self.comment(self.member,brand=self.brand.pk)
        self.assertEqual(response.status_code,302)
        item=Comment.objects.get()
        self.assertEqual(item.author,self.member)
        self.assertIsNone(item.brand)
        response=self.client.get(reverse('community:detail',args=[self.tips.pk]))
        self.assertContains(response,'일반회원')
        self.assertContains(response,'일반독자')

    def test_owner_tip_comment_gets_own_verified_brand(self):
        self.comment(self.owner)
        self.assertEqual(Comment.objects.get().brand,self.brand)

    def test_guest_cannot_comment(self):
        response=self.comment()
        self.assertEqual(response.status_code,302)
        self.assertIn('/accounts/login/',response.url)
        self.assertFalse(Comment.objects.exists())

    def test_existing_board_permissions_stay_owner_only(self):
        response=self.comment(self.member,post=self.regular,brand=self.brand.pk)
        self.assertRedirects(response,reverse('community:verify'))
        self.assertFalse(Comment.objects.exists())
        self.login(self.member)
        response=self.client.get(reverse('community:detail',args=[self.regular.pk]))
        self.assertFalse(response.context['can_comment'])

    def test_member_can_edit_and_delete_own_comment(self):
        self.comment(self.member)
        item=Comment.objects.get()
        response=self.client.post(reverse('community:comment_edit',args=[item.pk]),{'content':'수정한 질문'})
        self.assertEqual(response.status_code,302)
        item.refresh_from_db()
        self.assertEqual(item.content,'수정한 질문')
        self.assertIsNone(item.brand)
        response=self.client.post(reverse('community:comment_delete',args=[item.pk]))
        self.assertEqual(response.status_code,302)
        self.assertFalse(Comment.objects.exists())

    def test_other_member_cannot_edit_or_delete_comment(self):
        self.comment(self.member)
        item=Comment.objects.get()
        self.login(self.other)
        self.assertEqual(self.client.post(reverse('community:comment_edit',args=[item.pk]),{'content':'타인 수정'}).status_code,404)
        self.assertEqual(self.client.post(reverse('community:comment_delete',args=[item.pk])).status_code,404)
        self.assertTrue(Comment.objects.filter(pk=item.pk).exists())

    def test_hidden_post_rejects_comments(self):
        self.tips.moderation_state='blind'
        self.tips.save()
        self.assertEqual(self.comment(self.member).status_code,404)
        self.assertFalse(Comment.objects.exists())

    def test_empty_comment_is_invalid(self):
        response=self.comment(self.member,content='')
        self.assertEqual(response.status_code,400)
        self.assertTrue(response.context['can_comment'])
        self.assertFalse(Comment.objects.exists())

    def test_member_comment_moderation_is_preserved(self):
        self.comment(self.member,content='씨발 포함된 댓글')
        item=Comment.objects.get()
        self.assertNotIn('씨발',item.content)
        self.assertEqual(item.moderation_state,'blind')

    def test_member_can_report_comment(self):
        self.comment(self.member)
        item=Comment.objects.get()
        self.login(self.other)
        response=self.client.post(reverse('community:report_comment',args=[item.pk]),{'reason':'검토 요청'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Report.objects.filter(comment=item,reporter=self.other).exists())

    def test_csrf_protection_is_preserved(self):
        client=Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        response=client.post(reverse('community:comment_create',args=[self.tips.pk]),{'content':'토큰 없음'})
        self.assertEqual(response.status_code,403)
        self.assertFalse(Comment.objects.exists())

    def test_retired_closure_routes_are_not_registered(self):
        for path in ['/community/closure/','/community/closure/new/','/community/closure/verify/','/community/closure/1/','/community/closure/documents/1/closure/']:
            with self.assertRaises(Resolver404):
                resolve(path)

    def test_retired_models_are_not_in_admin(self):
        self.assertFalse(admin.site.is_registered(ClosureReview))
        self.assertFalse(admin.site.is_registered(ClosureVerification))
