from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken

from users.serializer import CustomTokenObtainPairSerializer, UserSerializer

User = get_user_model()


class UserSerializerTest(TestCase):
    """Тесты для UserSerializer"""

    def setUp(self):
        self.user_data = {
            "email": "11@test.ru",
            "password": "123",
            "first_name": "Test",
            "last_name": "User",
        }

    def test_create_user_success(self):
        """Тест успешного создания пользователя"""
        serializer = UserSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()
        self.assertEqual(user.email, "11@test.ru")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.check_password("123"))

    def test_create_user_without_password(self):
        """Тест создания пользователя без пароля"""
        data = {
            "email": "12@test.ru",
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()
        self.assertEqual(user.email, "12@test.ru")
        self.assertEqual(user.password, "")

    def test_create_user_missing_email(self):
        """Тест создания пользователя без email"""
        data = {"password": "123", "first_name": "Test"}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_create_user_duplicate_email(self):
        """Тест создания пользователя с существующим email"""
        User.objects.create_user(email="11@test.ru", password="123")

        data = {"email": "11@test.ru", "password": "456"}
        serializer = UserSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_update_user_success(self):
        """Тест успешного обновления пользователя"""
        user = User.objects.create_user(email="old@test.ru", password="123")

        data = {"email": "new@test.ru", "first_name": "New", "last_name": "Name"}

        serializer = UserSerializer(instance=user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_user = serializer.save()
        self.assertEqual(updated_user.email, "new@test.ru")
        self.assertEqual(updated_user.first_name, "New")
        self.assertEqual(updated_user.last_name, "Name")
        self.assertTrue(updated_user.check_password("123"))

    def test_update_user_password(self):
        """Тест обновления пароля пользователя"""
        user = User.objects.create_user(email="12@test.ru", password="123")

        data = {"password": "456"}

        serializer = UserSerializer(instance=user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())

        updated_user = serializer.save()
        self.assertTrue(updated_user.check_password("456"))

    def test_serializer_fields(self):
        """Тест полей сериализатора"""
        serializer = UserSerializer()
        fields = set(serializer.fields.keys())
        expected_fields = {"id", "email", "first_name", "last_name", "password"}
        self.assertEqual(fields, expected_fields)

        self.assertTrue(serializer.fields["password"].write_only)

    def test_read_only_fields(self):
        """Тест read_only полей"""
        serializer = UserSerializer()
        self.assertIn("id", serializer.Meta.read_only_fields)


class CustomTokenObtainPairSerializerTest(TestCase):
    """Тесты для CustomTokenObtainPairSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(email="13@test.ru", password="123")
        self.serializer_class = CustomTokenObtainPairSerializer

    def test_valid_credentials(self):
        """Тест валидных учетных данных"""
        data = {"email": "13@test.ru", "password": "123"}
        serializer = self.serializer_class(data=data)
        self.assertTrue(serializer.is_valid())

        result = serializer.validated_data
        self.assertIn("access", result)
        self.assertIn("refresh", result)

        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_login)

    def test_invalid_email(self):
        """Тест с несуществующим email"""
        data = {"email": "nonexistent@test.ru", "password": "123"}
        serializer = self.serializer_class(data=data)

        try:
            self.assertFalse(serializer.is_valid())
            self.assertIn("detail", serializer.errors)
        except AuthenticationFailed:
            pass

    def test_invalid_password(self):
        """Тест с неправильным паролем"""
        data = {"email": "11@test.ru", "password": "wrongpass"}
        serializer = self.serializer_class(data=data)

        try:
            self.assertFalse(serializer.is_valid())
            self.assertIn("detail", serializer.errors)
        except AuthenticationFailed:
            pass

    def test_missing_email(self):
        """Тест без email"""
        data = {"password": "123"}
        serializer = self.serializer_class(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_missing_password(self):
        """Тест без password"""
        data = {"email": "12@test.ru"}
        serializer = self.serializer_class(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_serializer_returns_tokens_and_user_data(self):
        """Тест, что сериализатор возвращает токены и данные пользователя"""
        data = {"email": "13@test.ru", "password": "123"}
        serializer = self.serializer_class(data=data)
        self.assertTrue(serializer.is_valid())

        result = serializer.validated_data
        self.assertIn("access", result)
        self.assertIn("refresh", result)

        refresh = RefreshToken(result["refresh"])
        self.assertIsNotNone(refresh)
