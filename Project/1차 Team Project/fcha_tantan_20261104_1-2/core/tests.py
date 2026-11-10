import json
from datetime import date,timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase,override_settings,Client
from django.urls import reverse
from django.utils import timezone
from brands.models import Brand,OwnerVerification
from community.models import Post,Comment
from market.models import StoreLocation,TransferListing
from market.maps import listing_point
from core.models import SupportTicket,ModerationPolicy,FAQ
from core.moderation import sanitize


class PlatformFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User=get_user_model()
        cls.owner=User.objects.create_user('owner',password='safe-pass-391',first_name='점주닉네임')
        cls.other=User.objects.create_user('other',password='safe-pass-392',first_name='다른점주')
        cls.visitor=User.objects.create_user('visitor',password='safe-pass-393')
        cls.staff=User.objects.create_user('staff',password='safe-pass-394',is_staff=True)
        cls.brand=Brand.objects.create(slug='coffee_one',name='테스트카페',category='커피',is_demo=False)
        cls.brand2=Brand.objects.create(slug='coffee_two',name='두번째카페',category='커피',is_demo=False)
        cls.brand3=Brand.objects.create(slug='coffee_three',name='세번째카페',category='커피',is_demo=False)
        for user in [cls.owner,cls.other]:
            OwnerVerification.objects.create(user=user,brand=cls.brand,store_name='비공개지점',contract_start_date=date(2020,1,1),contract_file='contracts/private.pdf',business_file='contracts/business.pdf',status='approved')
        cls.post=Post.objects.create(author=cls.owner,brand=cls.brand,title='운영 이야기',content='좋은 경험을 공유합니다.')

    def login(self,user=None):self.client.force_login(user or self.owner)

    def test_calculator_initial_is_empty(self):
        self.login();response=self.client.get('/brands/calculator/')
        self.assertIsNone(response.context['calculator_brand'])
        self.assertEqual(response.context['form'].initial['brand'],'')
        self.assertContains(response,'선택 안 함 · 직접 입력')
        response=self.client.post('/brands/calculator/',{'brand':'','investment':10000,'sales':1000,'rent':100,'labor':200,'other':'','variable_rate':30})
        self.assertEqual(response.context['result']['profit'],400)

    def test_region_checkbox_first_and_no_icons(self):
        self.login();response=self.client.get('/brands/bregion/')
        self.assertContains(response,'data-compare-checkbox')
        self.assertNotContains(response,'table-icon')
        text=response.content.decode();self.assertLess(text.index('scope="col">비교'),text.index('scope="col">브랜드'))

    def test_comparison_idempotent_and_limit(self):
        for brand in [self.brand,self.brand,self.brand2]:
            response=self.client.post(reverse('brands:compare_toggle',args=[brand.slug]),{'selected':'1'},HTTP_X_REQUESTED_WITH='fetch')
            self.assertEqual(response.status_code,200)
        self.assertEqual(len(response.json()['ids']),2)
        response=self.client.post(reverse('brands:compare_toggle',args=[self.brand3.slug]),{'selected':'1'},HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(response.status_code,200)
        extra=[Brand.objects.create(slug=f'extra_{i}',name=f'추가브랜드{i}',is_demo=False) for i in range(8)]
        for item in extra[:7]:
            response=self.client.post(reverse('brands:compare_toggle',args=[item.slug]),{'selected':'1'},HTTP_X_REQUESTED_WITH='fetch')
            self.assertEqual(response.status_code,200)
        response=self.client.post(reverse('brands:compare_toggle',args=[extra[7].slug]),{'selected':'1'},HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(response.status_code,409)
        self.assertEqual(len(response.json()['ids']),10)
        response=self.client.post(reverse('brands:compare_toggle',args=[self.brand.slug]),{'selected':'0'},HTTP_X_REQUESTED_WITH='fetch')
        self.assertEqual(len(response.json()['ids']),9);self.assertNotIn(self.brand.slug,response.json()['ids'])

    def test_unverified_cannot_post_or_comment(self):
        self.login(self.visitor)
        response=self.client.post('/community/new/',{'brand':self.brand.pk,'title':'제목','content':'본문','topic':'free'})
        self.assertRedirects(response,'/community/verify/')
        response=self.client.post(f'/community/{self.post.pk}/comments/',{'brand':self.brand.pk,'content':'댓글'})
        self.assertRedirects(response,'/community/verify/')
        self.assertFalse(Comment.objects.exists())

    def test_verified_post_and_comment_crud(self):
        self.login();response=self.client.post('/community/new/',{'brand':self.brand.pk,'title':'새 운영글','content':'오늘의 운영 경험','topic':'operation'})
        self.assertEqual(response.status_code,302);post=Post.objects.get(title='새 운영글')
        response=self.client.post(f'/community/{post.pk}/edit/',{'brand':self.brand.pk,'title':'수정 운영글','content':'수정 본문','topic':'free'})
        self.assertEqual(response.status_code,302);post.refresh_from_db();self.assertEqual(post.title,'수정 운영글')
        response=self.client.post(f'/community/{post.pk}/comments/',{'brand':self.brand.pk,'content':'댓글 작성'})
        self.assertEqual(response.status_code,302);comment=post.comments.get()
        self.client.post(f'/community/comments/{comment.pk}/edit/',{'brand':self.brand.pk,'content':'댓글 수정'})
        comment.refresh_from_db();self.assertEqual(comment.content,'댓글 수정')
        self.client.post(f'/community/comments/{comment.pk}/delete/')
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())
        self.client.post(f'/community/{post.pk}/delete/')
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_other_owner_cannot_edit_delete(self):
        comment=Comment.objects.create(author=self.owner,brand=self.brand,post=self.post,content='내 댓글')
        self.login(self.other)
        for url in [f'/community/{self.post.pk}/edit/',f'/community/{self.post.pk}/delete/',f'/community/comments/{comment.pk}/edit/',f'/community/comments/{comment.pk}/delete/']:
            self.assertEqual(self.client.post(url,{}).status_code,404)
        self.assertTrue(Post.objects.filter(pk=self.post.pk).exists())

    def test_brand_cannot_be_spoofed_and_expired_not_eligible(self):
        self.login()
        response=self.client.post('/community/new/',{'brand':self.brand2.pk,'title':'제목','content':'내용','topic':'free'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.context['form'].errors)
        OwnerVerification.objects.filter(user=self.owner).update(contract_end_date=timezone.localdate()-timedelta(days=1))
        response=self.client.get('/community/new/')
        self.assertRedirects(response,'/community/verify/')

    def test_server_profanity_filter_and_blind_no_public_leak(self):
        self.login()
        self.client.post('/community/new/',{'brand':self.brand.pk,'title':'운영 제목','content':'씨 발 공격 본문','topic':'free'})
        item=Post.objects.get(title='운영 제목');self.assertEqual(item.moderation_state,'blind');self.assertNotIn('씨 발',item.content)
        self.assertIn('씨 발',item.moderation_original['content'])
        self.client.logout();response=self.client.get(f'/community/{item.pk}/')
        self.assertNotContains(response,'공격 본문');self.assertNotContains(response,'씨 발')
        self.assertContains(response,'검토 중')
        item.moderation_state='removed';item.save()
        response=self.client.get(f'/community/{item.pk}/');self.assertContains(response,'일방적 비난 혹은 근거없는 욕설로 삭제되었습니다.')

    def test_frontend_filtered_original_is_validated(self):
        self.login()
        self.client.post('/community/new/',{'brand':self.brand.pk,'title':'제거 테스트','content':'안녕','topic':'free','__filtered_originals':json.dumps({'content':'씨발 안녕'})})
        item=Post.objects.get(title='제거 테스트');self.assertEqual(item.moderation_state,'blind');self.assertEqual(item.content,'안녕')
        self.client.post('/community/new/',{'brand':self.brand.pk,'title':'변조 테스트','content':'내가 입력한 글','topic':'free','__filtered_originals':json.dumps({'content':'씨발 다른 글'})})
        item=Post.objects.get(title='변조 테스트');self.assertEqual(item.content,'내가 입력한 글');self.assertEqual(item.moderation_state,'visible')

    def test_edit_does_not_unblind(self):
        self.post.moderation_state='removed';self.post.save();self.login()
        self.client.post(f'/community/{self.post.pk}/edit/',{'brand':self.brand.pk,'title':'수정','content':'정상 문장','topic':'free','moderation_state':'visible'})
        self.post.refresh_from_db();self.assertEqual(self.post.moderation_state,'removed')

    def test_constructive_criticism_not_filtered(self):
        self.assertEqual(sanitize('서비스가 아쉬웠고 개선이 필요합니다.'),('서비스가 아쉬웠고 개선이 필요합니다.',False))
        self.assertEqual(sanitize('classic shop'),('classic shop',False))

    def test_post_author_brand_but_not_branch(self):
        response=self.client.get(f'/community/{self.post.pk}/')
        self.assertContains(response,'테스트카페 점주');self.assertContains(response,'점주닉네임');self.assertNotContains(response,'비공개지점')

    def test_support_is_private(self):
        item=SupportTicket.objects.create(user=self.owner,category='account',title='비공개제목',content='개인문의')
        self.login(self.other);self.assertEqual(self.client.get(f'/help/tickets/{item.pk}/').status_code,404)
        self.login();self.assertContains(self.client.get(f'/help/tickets/{item.pk}/'),'개인문의')

    def test_language_cookie_and_safe_redirect(self):
        response=self.client.post('/help/language/',{'language':'en','next':'https://evil.example/'})
        self.assertEqual(response.url,'/');self.assertEqual(response.cookies['tantan-language'].value,'en')
        self.assertContains(self.client.get('/help/'),'lang="en"')

    def test_chatbot_local_faq_and_no_external_call(self):
        call_command('seed_site_content',no_demo=True,verbosity=0)
        with patch('requests.post',side_effect=AssertionError('No external AI calls')):
            response=self.client.post('/help/chat/',{'question':'비교하는 방법','language':'ko'})
        self.assertEqual(response.status_code,200);self.assertEqual(response.json()['mode'],'local_search')
        self.assertIn('체크박스',response.json()['answer'])
        response=self.client.post('/help/chat/',{'question':'verification','language':'en'})
        self.assertEqual(response.status_code,200);self.assertTrue(response.json()['sources'])

    def test_csrf_and_get_delete_prohibited(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.owner)
        self.assertEqual(client.post('/community/new/',{}).status_code,403)
        self.login();self.assertEqual(self.client.get(f'/community/{self.post.pk}/delete/').status_code,405)

    def test_document_private_routes_and_mime_validation(self):
        from core.documents import validate_evidence
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):validate_evidence(SimpleUploadedFile('fake.pdf',b'<html>not a pdf</html>'))
        validate_evidence(SimpleUploadedFile('test.pdf',b'%PDF-1.4 test'))
        verification=OwnerVerification.objects.filter(user=self.owner).first()
        self.login(self.other)
        self.assertEqual(self.client.get(f'/help/evidence/owner/{verification.pk}/contract/').status_code,404)

    def test_public_map_respects_opt_in_brand_verification_and_filters(self):
        self.login()
        common={'owner':self.owner,'brand':self.brand,'store_name':'매장','address':'주소','sido':'서울','sigungu':'관악구','dong':'신림동','latitude':37.48,'longitude':126.93,'status':'operating'}
        hidden=StoreLocation.objects.create(**common)
        public=StoreLocation.objects.create(**common,is_public=True)
        wrong=StoreLocation.objects.create(**{**common,'brand':self.brand2},is_public=True)
        data=self.client.get('/market/map/locations/?region=서울&sigungu=관악구&dong=신림동').json()
        self.assertEqual(data['total'],1);self.assertEqual(data['points'][0]['id'],public.pk)
        data=self.client.get('/market/map/locations/?region=서울&sigungu=강남구').json();self.assertEqual(data['total'],0)
        response=self.client.get('/brands/bregion/?region=서울&sigungu=관악구&dong=신림동')
        self.assertEqual(response.context['total'],1);self.assertTrue(response.context['is_local_scope'])

    def test_listing_location_rounding_filters_and_owner_permissions(self):
        listing=TransferListing.objects.create(owner=self.owner,brand=self.brand,title='매물',description='시설',sido='서울',sigungu='관악구',latitude=Decimal('37.487654'),longitude=Decimal('126.932123'),premium_manwon=1000,monthly_rent_manwon=100)
        point=listing_point(listing);self.assertEqual(point['lat'],37.488);self.assertEqual(point['lng'],126.932)
        response=self.client.get('/market/transfer/?max_premium=500');self.assertEqual(response.context['total_count'],0)
        response=self.client.get('/market/transfer/?max_rent=200');self.assertEqual(response.context['total_count'],1)
        listing.moderation_state='blind';listing.save()
        response=self.client.get(f'/market/transfer/{listing.pk}/');self.assertNotContains(response,'시설')
        self.login(self.other);self.assertEqual(self.client.post(f'/market/transfer/{listing.pk}/delete/',{}).status_code,404)
        self.login();self.client.post(f'/market/transfer/{listing.pk}/delete/',{});self.assertFalse(TransferListing.objects.filter(pk=listing.pk).exists())

    def test_evidence_upload_and_precheck(self):
        from core.documents import precheck
        with TemporaryDirectory() as folder,override_settings(MEDIA_ROOT=folder):
            self.login()
            payload={'store_name':'인증 지점','contract_start_date':'2020-01-01',
                     'contract_file':SimpleUploadedFile('contract.pdf',b'%PDF-1.4 contract'),
                     'business_file':SimpleUploadedFile('business.pdf',b'%PDF-1.4 certificate')}
            response=self.client.post(f'/brands/bview/{self.brand.slug}/verify/',payload)
            self.assertEqual(response.status_code,302)
            item=OwnerVerification.objects.filter(user=self.owner).latest('pk')
            self.assertEqual(item.status,'pending');self.assertFalse(item.document_check['ai_performed'])
            self.assertTrue(all(check['ok'] for check in item.document_check['checks']))

    def test_default_local_region_does_not_mix_cities(self):
        self.login()
        common={'owner':self.owner,'brand':self.brand,'store_name':'점포','address':'주소','sigungu':'중구','dong':'중앙동','status':'operating','is_public':True}
        StoreLocation.objects.create(**common,sido='서울')
        StoreLocation.objects.create(**common,sido='부산')
        response=self.client.get('/brands/bregion/?sigungu=중구')
        self.assertEqual(response.context['total'],1)

    def test_specific_brand_question_beats_generic_faq(self):
        call_command('seed_site_content',no_demo=True,verbosity=0)
        self.login()
        data=self.client.post('/help/chat/',{'question':'테스트카페 매출'}).json()
        self.assertIn('테스트카페',data['answer'])
        self.assertEqual(data['sources'][0]['url'],f'/brands/bview/{self.brand.slug}/')

    def test_review_uses_configured_removal_message(self):
        from brands.models import BrandReview
        ModerationPolicy.objects.create(removed_message='관리자가 설정한 삭제 안내')
        review=BrandReview(moderation_state='removed')
        self.assertEqual(review.visibility_message,'관리자가 설정한 삭제 안내')

    def test_moderation_policy_rejects_non_list_and_long_terms(self):
        from django.core.exceptions import ValidationError
        for value in [{'term':'bad'},'bad',['x'*41]]:
            with self.assertRaises(ValidationError):ModerationPolicy(blocked_terms=value).clean()

    def test_demo_seed_is_idempotent_and_never_verifies_fake_owners(self):
        # The seed deliberately does not add demos to a community with real posts.
        self.post.delete()
        before=OwnerVerification.objects.count()
        call_command('seed_site_content',verbosity=0)
        self.assertEqual(Post.objects.filter(is_demo=True).count(),10)
        self.assertEqual(Comment.objects.filter(is_demo=True).count(),10)
        call_command('seed_site_content',verbosity=0)
        self.assertEqual(Post.objects.filter(is_demo=True).count(),10)
        self.assertEqual(OwnerVerification.objects.count(),before)
        self.assertFalse(get_user_model().objects.filter(username__startswith='tantan_demo_owner_',is_active=True).exists())

    def test_removed_content_stays_removed_when_automatic_blind_disabled(self):
        ModerationPolicy.objects.create(blind_on_match=False)
        self.post.moderation_state='removed';self.post.save();self.login()
        self.client.post(f'/community/{self.post.pk}/edit/',{'brand':self.brand.pk,'title':'수정','content':'씨발 수정','topic':'free'})
        self.post.refresh_from_db();self.assertEqual(self.post.moderation_state,'removed')

    def test_calculator_includes_full_catalogue_grouped_and_raw_names(self):
        from html.parser import HTMLParser
        class Picker(HTMLParser):
            in_picker=False
            slugs=[]
            def handle_starttag(self,tag,attrs):
                attrs=dict(attrs)
                if tag=='select' and 'data-reference-select' in attrs:self.in_picker=True
                if tag=='option' and self.in_picker and attrs.get('value'):self.slugs.append(attrs['value'])
            def handle_endtag(self,tag):
                if tag=='select':self.in_picker=False
        Brand.objects.bulk_create([Brand(slug=f'catalogue_{i}',name=f'가나다브랜드{i:03}',category='한식',is_demo=False) for i in range(45)])
        last=Brand.objects.create(slug='mega_test',name='메가엠지씨커피(MEGA MGC COFFEE)',category='카페',is_demo=False)
        self.login();response=self.client.get('/brands/calculator/')
        parser=Picker();parser.slugs=[];parser.feed(response.content.decode())
        self.assertEqual(set(parser.slugs),set(Brand.objects.values_list('slug',flat=True)))
        self.assertEqual(len(parser.slugs),Brand.objects.count())
        self.assertContains(response,last.name)
        self.assertContains(response,'optgroup label="카페 (1)"')
        response=self.client.get('/brands/calculator/',{'brand':last.slug})
        self.assertEqual(response.context['calculator_brand'],last)

    def test_lookup_contains_and_case_insensitive_names(self):
        a=Brand.objects.create(slug='mega_a',name='메가엠지씨커피(MEGA MGC COFFEE)',is_demo=False)
        b=Brand.objects.create(slug='mega_b',name='더메가카페',is_demo=False)
        self.assertEqual({row['slug'] for row in self.client.get('/brands/lookup/?q=메가').json()['results']},{a.slug,b.slug})
        self.assertEqual([row['slug'] for row in self.client.get('/brands/lookup/?q=mgc').json()['results']],[a.slug])

    def test_menu_ends_with_community_then_help_for_both_sessions(self):
        for authenticated in [False,True]:
            if authenticated:self.login(self.staff)
            response=self.client.get('/help/');html=response.content.decode()
            panel=html.split('id="account-panel"',1)[1].split('</header>',1)[0]
            bottom=panel.split('class="account-menu-bottom"',1)[1]
            self.assertLess(bottom.index('href="/community/"'),bottom.index('href="/help/"'))
            self.assertEqual(bottom.count('<a '),2)

    def test_ten_brand_comparison_and_csv_keep_selection_order(self):
        import csv
        self.login()
        more=[Brand.objects.create(slug=f'multi_{i}',name=f'여러브랜드{i}',is_demo=False) for i in range(7)]
        ordered=[self.brand3,self.brand,self.brand2]+more
        for brand in ordered:self.client.post(reverse('brands:compare_toggle',args=[brand.slug]),{'selected':'1'})
        response=self.client.get('/brands/bcompare/')
        self.assertEqual([row['brand'].slug for row in response.context['rows']],[b.slug for b in ordered])
        self.assertEqual(len(response.context['comparison_data']['brands']),10)
        self.assertTrue(all(len(metric['values'])==10 for metric in response.context['comparison_data']['metrics']))
        rows=list(csv.reader(self.client.get('/brands/compare/csv/').content.decode('utf-8-sig').splitlines()))
        self.assertEqual(len(rows),11)
        self.assertEqual([row[2] for row in rows[1:]],[b.name for b in ordered])
