from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from accounts.models import SavedBrand
from brands.models import Brand


class HomeSessionTests(TestCase):
    def test_home_does_not_create_session_for_anonymous_visit(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.session.modified)
        self.assertFalse(any(
            query['sql'].lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE'))
            for query in queries
        ))

    def test_compare_selection_survives_home_without_session_write(self):
        brand = Brand.objects.create(slug='home-check', name='Home check', is_demo=False)
        response = self.client.post(f'/brands/compare/toggle/{brand.slug}/')
        self.assertEqual(response.status_code, 302)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.wsgi_request.session['tantan-compare'], [brand.slug])
        self.assertFalse(response.wsgi_request.session.modified)

    def test_login_and_saved_brand(self):
        user = get_user_model().objects.create_user(username='home-member', password='home-test-password')
        brand = Brand.objects.create(slug='saved-check', name='Saved check', is_demo=False)
        response = self.client.post('/accounts/login/', {'username': user.username, 'password': 'home-test-password'})
        self.assertEqual(response.status_code, 302)
        response = self.client.post(f'/brands/saved/toggle/{brand.slug}/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SavedBrand.objects.filter(user=user, brand=brand).exists())
        self.assertEqual(self.client.get('/brands/bsaved/').status_code, 200)
        response = self.client.post(f'/brands/saved/toggle/{brand.slug}/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SavedBrand.objects.filter(user=user, brand=brand).exists())
