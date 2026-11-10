from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from accounts.models import MemberProfile
from .models import Comment, Post


class FounderPostTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.founder = User.objects.create_user('founder', first_name='예비사장')
        MemberProfile.objects.create(user=self.founder, wants_startup=True)
        self.member = User.objects.create_user('member')
        MemberProfile.objects.create(user=self.member, wants_startup=False)

    def test_founder_question_button_post_and_label(self):
        index = self.client.get(reverse('community:index'))
        self.assertContains(index, '?topic=founder')  # 예비 창업주 질문하기 버튼
        self.client.force_login(self.founder)
        form = self.client.get(reverse('community:new') + '?topic=founder')
        self.assertEqual(form.status_code, 200)
        self.assertNotContains(form, 'name="brand"')  # 브랜드 없이 작성
        self.assertContains(form, '<option value="founder" selected>')
        r = self.client.post(reverse('community:new'), {'topic': 'founder', 'title': '첫 창업 질문', 'content': '가맹비는 협상 가능한가요?'})
        post = Post.objects.get()
        self.assertRedirects(r, reverse('community:detail', args=[post.pk]), fetch_redirect_response=False)
        self.assertIsNone(post.brand)
        detail = self.client.get(reverse('community:detail', args=[post.pk]))
        self.assertContains(detail, '예비 창업주')
        self.client.post(reverse('community:comment_create', args=[post.pk]), {'content': '감사합니다'})
        self.assertIsNone(Comment.objects.get().brand)
        self.assertContains(self.client.get(reverse('community:index') + '?topic=founder'), '첫 창업 질문')

    def test_member_without_founder_or_verification_still_blocked(self):
        self.client.force_login(self.member)
        r = self.client.post(reverse('community:new'), {'topic': 'free', 'title': 't', 'content': 'c'})
        self.assertRedirects(r, reverse('community:verify'), fetch_redirect_response=False)
        self.assertFalse(Post.objects.exists())
