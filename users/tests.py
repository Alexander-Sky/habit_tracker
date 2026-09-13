from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit
from users.models import User

PASSWORD = 'Str0ngPass!42'


class RegistrationTestCase(APITestCase):
    """Регистрация."""

    def setUp(self):
        self.url = reverse('users:register')
        User.objects.create(email='taken@test.ru')

    def test_registration_without_token(self):
        response = self.client.post(self.url, {'email': 'new@test.ru', 'password': PASSWORD})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='new@test.ru').exists())

    def test_password_is_hashed_and_hidden(self):
        response = self.client.post(self.url, {'email': 'new@test.ru', 'password': PASSWORD})
        user = User.objects.get(email='new@test.ru')

        self.assertNotIn('password', response.json())
        self.assertNotEqual(user.password, PASSWORD)
        self.assertTrue(user.check_password(PASSWORD))

    def test_duplicate_email_rejected(self):
        response = self.client.post(self.url, {'email': 'taken@test.ru', 'password': PASSWORD})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.json())

    def test_duplicate_email_is_case_insensitive(self):
        response = self.client.post(self.url, {'email': 'TAKEN@test.ru', 'password': PASSWORD})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_rejected(self):
        response = self.client.post(self.url, {'email': 'new@test.ru', 'password': '12345678'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.json())


class AuthTestCase(APITestCase):
    """JWT-токены."""

    def setUp(self):
        self.user = User.objects.create(email='user@test.ru')
        self.user.set_password(PASSWORD)
        self.user.save()

    def test_login_returns_token_pair(self):
        response = self.client.post(
            reverse('users:login'), {'email': 'user@test.ru', 'password': PASSWORD},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())

    def test_wrong_password_rejected(self):
        response = self.client.post(
            reverse('users:login'), {'email': 'user@test.ru', 'password': 'nope'},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_returns_new_access(self):
        refresh = self.client.post(
            reverse('users:login'), {'email': 'user@test.ru', 'password': PASSWORD},
        ).json()['refresh']

        response = self.client.post(reverse('users:token-refresh'), {'refresh': refresh})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.json())

    def test_token_opens_closed_endpoint(self):
        access = self.client.post(
            reverse('users:login'), {'email': 'user@test.ru', 'password': PASSWORD},
        ).json()['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        self.assertEqual(
            self.client.get(reverse('habits:habit-list')).status_code, status.HTTP_200_OK,
        )

    def test_broken_token_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer not.a.token')
        self.assertEqual(
            self.client.get(reverse('habits:habit-list')).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class ProfileTestCase(APITestCase):
    """Профиль пользователя."""

    def setUp(self):
        self.user = User.objects.create(email='user@test.ru', first_name='Александр')
        self.url = reverse('users:profile')

    def test_anonymous_has_no_access(self):
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_returns_own_data(self):
        self.client.force_authenticate(user=self.user)
        data = self.client.get(self.url).json()

        self.assertEqual(data['email'], 'user@test.ru')
        self.assertNotIn('password', data)

    def test_habits_count(self):
        Habit.objects.create(user=self.user, action='пить воду', time='08:00', place='кухня')
        self.client.force_authenticate(user=self.user)

        self.assertEqual(self.client.get(self.url).json()['habits_count'], 1)

    def test_telegram_chat_id_can_be_saved(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(self.url, {'telegram_chat_id': '123456789'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.telegram_chat_id, '123456789')

    def test_email_is_read_only(self):
        self.client.force_authenticate(user=self.user)
        self.client.patch(self.url, {'email': 'hacked@test.ru'})

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'user@test.ru')


class UserModelTestCase(APITestCase):
    """Менеджер пользователей."""

    def test_create_user(self):
        user = User.objects.create_user(email='manager@test.ru', password=PASSWORD)

        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password=PASSWORD)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email='admin@test.ru', password=PASSWORD)

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_str_is_email(self):
        self.assertEqual(str(User.objects.create(email='str@test.ru')), 'str@test.ru')


class DocumentationTestCase(APITestCase):
    """Документация доступна без токена."""

    def test_schema_swagger_and_redoc_are_public(self):
        for url in ('/api/schema/', '/api/docs/', '/api/redoc/'):
            self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK, url)

    def test_schema_contains_all_endpoints(self):
        paths = self.client.get('/api/schema/', {'format': 'json'}).json()['paths']

        for path in (
            '/api/register/',
            '/api/login/',
            '/api/token/refresh/',
            '/api/profile/',
            '/api/habits/',
            '/api/habits/{id}/',
            '/api/habits/public/',
        ):
            self.assertIn(path, paths, f'В схеме нет {path}')

    def test_home_page_points_to_docs(self):
        self.assertIn('swagger', self.client.get('/').json()['docs'])


class CorsTestCase(APITestCase):
    """CORS: фронтенд с другого домена должен получить заголовки."""

    def test_allowed_origin_gets_header(self):
        response = self.client.get('/api/schema/', HTTP_ORIGIN='http://localhost:3000')

        self.assertEqual(
            response.headers.get('Access-Control-Allow-Origin'), 'http://localhost:3000',
        )

    def test_foreign_origin_gets_no_header(self):
        response = self.client.get('/api/schema/', HTTP_ORIGIN='http://evil.example.com')
        self.assertIsNone(response.headers.get('Access-Control-Allow-Origin'))
