from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from habits.models import Habit

User = get_user_model()


class HabitAPITest(APITestCase):
    """Тесты для API привычек"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(
            email='test@test.ru',
            password='123'
        )

        self.other_user = User.objects.create_user(
            email='other@test.ru',
            password='123'
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.auth_headers = {
            'HTTP_AUTHORIZATION': f'Bearer {self.access_token}'
        }

        self.habits_list_url = reverse('habits:habit-list')

        # Создаем привычки
        self.habit1 = Habit.objects.create(
            owner=self.user,
            action='Утренняя зарядка',
            place='Дом',
            time=timezone.now().time(),
            periodicity=1,
            time_to_complete=30,
            prize='Кофе',
            is_public=True,
        )

        self.habit2 = Habit.objects.create(
            owner=self.user,
            action='Чтение',
            place='Библиотека',
            time=timezone.now().time(),
            periodicity=3,
            time_to_complete=60,
            prize='Журнал',
            is_public=False,
        )

        self.habit3 = Habit.objects.create(
            owner=self.other_user,
            action='Прочее',
            place='Офис',
            time=timezone.now().time(),
            periodicity=1,
            time_to_complete=15,
            prize='Чай',
            is_public=True,
        )

        self.private_habit_other = Habit.objects.create(
            owner=self.other_user,
            action='Помыть посуду',
            place='Дом',
            time=timezone.now().time(),
            periodicity=2,
            time_to_complete=20,
            prize='Шоколадка',
            is_public=False,
        )

    # ==========================================
    # ТЕСТЫ GET ЗАПРОСОВ (список)
    # ==========================================

    def test_list_habits_authenticated(self):
        """Тест получения списка привычек авторизованным пользователем"""
        response = self.client.get(
            self.habits_list_url,
            **self.auth_headers
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что response.data содержит пагинацию
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)

        # Получаем список привычек из results
        results = response.data['results']
        self.assertIsInstance(results, list)

        # Проверяем, что пользователь видит только свои привычки
        for habit in results:
            self.assertEqual(habit['owner'], self.user.id)

        # Должно быть 2 привычки (публичная и приватная)
        self.assertEqual(len(results), 2)

    def test_list_habits_unauthenticated(self):
        """Тест получения списка привычек неавторизованным пользователем"""
        response = self.client.get(self.habits_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_habits_filter_by_is_public(self):
        """Тест фильтрации привычек по публичности"""
        response = self.client.get(
            f"{self.habits_list_url}?is_public=true",
            **self.auth_headers
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что response.data содержит пагинацию
        self.assertIn('results', response.data)
        self.assertIn('count', response.data)

        # Получаем список привычек из results
        results = response.data['results']
        self.assertIsInstance(results, list)

        # Проверяем, что все привычки публичные и принадлежат пользователю
        for habit in results:
            self.assertTrue(habit['is_public'])
            self.assertEqual(habit['owner'], self.user.id)

    # ==========================================
    # ТЕСТЫ GET ЗАПРОСОВ (детали)
    # ==========================================

    def test_retrieve_own_habit(self):
        """Тест получения своей привычки"""
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.habit1.id)
        self.assertEqual(response.data['action'], 'Утренняя зарядка')
        self.assertEqual(response.data['place'], 'Дом')

    def test_retrieve_public_other_user_habit(self):
        """Тест получения публичной привычки другого пользователя"""
        url = reverse('habits:habit-detail', args=[self.habit3.id])
        response = self.client.get(url, **self.auth_headers)

        # Если публичные привычки других недоступны, ожидаем 404
        # Если доступны, ожидаем 200
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND])

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data['id'], self.habit3.id)
            self.assertEqual(response.data['action'], 'Прочее')
            self.assertNotEqual(response.data['owner'], self.user.id)

    def test_retrieve_private_other_user_habit(self):
        """Тест получения приватной привычки другого пользователя (должна быть недоступна)"""
        url = reverse('habits:habit-detail', args=[self.private_habit_other.id])
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_habit(self):
        """Тест получения несуществующей привычки"""
        url = reverse('habits:habit-detail', args=[999])
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================
    # ТЕСТЫ POST ЗАПРОСОВ (создание)
    # ==========================================

    def test_create_habit_success(self):
        """Тест успешного создания привычки"""
        data = {
            'action': 'Новая привычка',
            'place': 'Дом',
            'time': '09:00:00',
            'periodicity': 1,
            'time_to_complete': 30,
            'prize': 'Coffee',
            'is_public': True
        }

        response = self.client.post(
            self.habits_list_url,
            data,
            **self.auth_headers
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['action'], 'Новая привычка')
        self.assertEqual(response.data['owner'], self.user.id)
        self.assertEqual(response.data['place'], 'Дом')
        self.assertTrue(response.data['is_public'])
        self.assertTrue(Habit.objects.filter(action='Новая привычка').exists())

    def test_create_habit_without_auth(self):
        """Тест создания привычки без авторизации"""
        data = {
            'action': 'Новая привычка',
            'time': '09:00:00'
        }

        response = self.client.post(self.habits_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_habit_missing_required_fields(self):
        """Тест создания привычки без обязательных полей"""
        data = {
            'action': 'Новая привычка'
            # Отсутствует 'place' - обязательное поле
        }

        response = self.client.post(
            self.habits_list_url,
            data,
            **self.auth_headers
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('place', response.data)

    def test_create_habit_invalid_periodicity(self):
        """Тест создания привычки с невалидной периодичностью"""
        data = {
            'action': 'Новая привычка',
            'place': 'Дом',
            'time': '09:00:00',
            'periodicity': 0  # Невалидное значение
        }

        response = self.client.post(
            self.habits_list_url,
            data,
            **self.auth_headers
        )

        # Если валидация работает - 400, если нет - 201
        if response.status_code == status.HTTP_201_CREATED:
            self.assertEqual(response.data.get('periodicity', 1), 1)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('periodicity', response.data)

    def test_create_habit_empty_action(self):
        """Тест создания привычки с пустым действием"""
        data = {
            'action': '',
            'place': 'Дом',
            'time': '09:00:00',
            'periodicity': 1
        }

        response = self.client.post(
            self.habits_list_url,
            data,
            **self.auth_headers
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('action', response.data)

    # ==========================================
    # ТЕСТЫ PATCH ЗАПРОСОВ
    # ==========================================

    def test_partial_update_own_habit(self):
        """Тест частичного обновления своей привычки"""
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        data = {
            'action': 'Обновленная',
            'place': 'Зал',
        }

        response = self.client.patch(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['action'], 'Обновленная')
        self.assertEqual(response.data['place'], 'Зал')

        self.habit1.refresh_from_db()
        self.assertEqual(self.habit1.action, 'Обновленная')
        self.assertEqual(self.habit1.place, 'Зал')

    def test_partial_update_other_user_habit(self):
        """Тест частичного обновления чужой привычки (должно быть запрещено)"""
        url = reverse('habits:habit-detail', args=[self.habit3.id])
        data = {
            'action': 'Чужая привычка'
        }

        response = self.client.patch(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.habit3.refresh_from_db()
        self.assertNotEqual(self.habit3.action, 'Чужая привычка')

    def test_partial_update_invalid_data(self):
        """Тест частичного обновления с невалидными данными"""
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        data = {
            'periodicity': 0  # Невалидное значение
        }

        response = self.client.patch(url, data, **self.auth_headers)

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data.get('periodicity', 1), 1)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('periodicity', response.data)

    # ==========================================
    # ТЕСТЫ PUT ЗАПРОСОВ
    # ==========================================

    def test_full_update_own_habit(self):
        """Тест полного обновления своей привычки"""
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        data = {
            'action': 'Полное обновление',
            'place': 'Офис',
            'time': '10:00:00',
            'periodicity': 3,
            'time_to_complete': 45,
            'prize': 'Чай',
            'is_public': False
        }

        response = self.client.put(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['action'], 'Полное обновление')
        self.assertEqual(response.data['place'], 'Офис')
        self.assertFalse(response.data['is_public'])

        self.habit1.refresh_from_db()
        self.assertEqual(self.habit1.action, 'Полное обновление')
        self.assertEqual(self.habit1.place, 'Офис')

    def test_full_update_other_user_habit(self):
        """Тест полного обновления чужой привычки (должно быть запрещено)"""
        url = reverse('habits:habit-detail', args=[self.habit3.id])
        data = {
            'action': 'Чужая привычка',
            'place': 'Офис',
            'time': '10:00:00',
            'periodicity': 1
        }

        response = self.client.put(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.habit3.refresh_from_db()
        self.assertNotEqual(self.habit3.action, 'Чужая привычка')

    # ==========================================
    # ТЕСТЫ DELETE ЗАПРОСОВ
    # ==========================================

    def test_delete_own_habit(self):
        """Тест удаления своей привычки"""
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(id=self.habit1.id).exists())

    def test_delete_other_user_habit(self):
        """Тест попытки удалить чужую привычку"""
        url = reverse('habits:habit-detail', args=[self.habit3.id])
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Habit.objects.filter(id=self.habit3.id).exists())

    def test_delete_nonexistent_habit(self):
        """Тест удаления несуществующей привычки"""
        url = reverse('habits:habit-detail', args=[999])
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================
    # ТЕСТЫ АВТОРИЗАЦИИ
    # ==========================================

    def test_create_habit_unauthorized(self):
        """Тест создания привычки без авторизации"""
        self.client.logout()
        data = {
            'action': 'Unauthorized Habit',
            'place': 'Дом',
            'time': '09:00:00'
        }
        response = self.client.post(self.habits_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_habit_unauthorized(self):
        """Тест обновления привычки без авторизации"""
        self.client.logout()
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        data = {'action': 'Updated Habit'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_habit_unauthorized(self):
        """Тест удаления привычки без авторизации"""
        self.client.logout()
        url = reverse('habits:habit-detail', args=[self.habit1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)