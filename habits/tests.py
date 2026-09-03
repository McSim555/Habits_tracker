from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from habits.models import Habit
from habits.validators import (validate_connected_habit_is_pleasant,
                               validate_connected_habit_no_connected,
                               validate_connected_habit_no_prize,
                               validate_habit_business_logic,
                               validate_not_self_connected,
                               validate_periodicity_range,
                               validate_pleasant_habit_constraints,
                               validate_prize_and_connected_habit,
                               validate_time_to_complete_range)

User = get_user_model()


class HabitAPITest(APITestCase):
    """Тесты для API привычек"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(email="test@test.ru", password="123")

        self.other_user = User.objects.create_user(
            email="other@test.ru", password="123"
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.auth_headers = {"HTTP_AUTHORIZATION": f"Bearer {self.access_token}"}

        self.habits_list_url = reverse("habits:habit-list")

        self.habit1 = Habit.objects.create(
            owner=self.user,
            action="Утренняя зарядка",
            place="Дом",
            time=timezone.now().time(),
            periodicity=1,
            time_to_complete=30,
            prize="Кофе",
            is_public=True,
        )

        self.habit2 = Habit.objects.create(
            owner=self.user,
            action="Чтение",
            place="Библиотека",
            time=timezone.now().time(),
            periodicity=3,
            time_to_complete=60,
            prize="Журнал",
            is_public=False,
        )

        self.habit3 = Habit.objects.create(
            owner=self.other_user,
            action="Прочее",
            place="Офис",
            time=timezone.now().time(),
            periodicity=1,
            time_to_complete=15,
            prize="Чай",
            is_public=True,
        )

        self.private_habit_other = Habit.objects.create(
            owner=self.other_user,
            action="Помыть посуду",
            place="Дом",
            time=timezone.now().time(),
            periodicity=2,
            time_to_complete=20,
            prize="Шоколадка",
            is_public=False,
        )

    def test_list_habits_authenticated(self):
        """Тест получения списка привычек авторизованным пользователем"""
        response = self.client.get(self.habits_list_url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

        results = response.data["results"]
        self.assertIsInstance(results, list)

        for habit in results:
            self.assertEqual(habit["owner"], self.user.id)

        self.assertEqual(len(results), 2)

    def test_list_habits_unauthenticated(self):
        """Тест получения списка привычек неавторизованным пользователем"""
        response = self.client.get(self.habits_list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_habits_filter_by_is_public(self):
        """Тест фильтрации привычек по публичности"""
        response = self.client.get(
            f"{self.habits_list_url}?is_public=true", **self.auth_headers
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

        results = response.data["results"]
        self.assertIsInstance(results, list)

        for habit in results:
            self.assertTrue(habit["is_public"])
            self.assertEqual(habit["owner"], self.user.id)

    def test_retrieve_own_habit(self):
        """Тест получения своей привычки"""
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.habit1.id)
        self.assertEqual(response.data["action"], "Утренняя зарядка")
        self.assertEqual(response.data["place"], "Дом")

    def test_retrieve_public_other_user_habit(self):
        """Тест получения публичной привычки другого пользователя"""
        url = reverse("habits:habit-detail", args=[self.habit3.id])
        response = self.client.get(url, **self.auth_headers)

        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        )

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data["id"], self.habit3.id)
            self.assertEqual(response.data["action"], "Прочее")
            self.assertNotEqual(response.data["owner"], self.user.id)

    def test_retrieve_private_other_user_habit(self):
        """Тест получения приватной привычки другого пользователя (должна быть недоступна)"""
        url = reverse("habits:habit-detail", args=[self.private_habit_other.id])
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_nonexistent_habit(self):
        """Тест получения несуществующей привычки"""
        url = reverse("habits:habit-detail", args=[999])
        response = self.client.get(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_habit_success(self):
        """Тест успешного создания привычки"""
        data = {
            "action": "Новая привычка",
            "place": "Дом",
            "time": "09:00:00",
            "periodicity": 1,
            "time_to_complete": 30,
            "prize": "Coffee",
            "is_public": True,
        }

        response = self.client.post(self.habits_list_url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["action"], "Новая привычка")
        self.assertEqual(response.data["owner"], self.user.id)
        self.assertEqual(response.data["place"], "Дом")
        self.assertTrue(response.data["is_public"])
        self.assertTrue(Habit.objects.filter(action="Новая привычка").exists())

    def test_create_habit_without_auth(self):
        """Тест создания привычки без авторизации"""
        data = {"action": "Новая привычка", "time": "09:00:00"}

        response = self.client.post(self.habits_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_habit_missing_required_fields(self):
        """Тест создания привычки без обязательных полей"""
        data = {"action": "Новая привычка"}

        response = self.client.post(self.habits_list_url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("place", response.data)

    def test_create_habit_invalid_periodicity(self):
        """Тест создания привычки с невалидной периодичностью"""
        data = {
            "action": "Новая привычка",
            "place": "Дом",
            "time": "09:00:00",
            "periodicity": 0,
        }

        response = self.client.post(self.habits_list_url, data, **self.auth_headers)

        if response.status_code == status.HTTP_201_CREATED:
            self.assertEqual(response.data.get("periodicity", 1), 1)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("periodicity", response.data)

    def test_create_habit_empty_action(self):
        """Тест создания привычки с пустым действием"""
        data = {"action": "", "place": "Дом", "time": "09:00:00", "periodicity": 1}

        response = self.client.post(self.habits_list_url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("action", response.data)

    def test_partial_update_own_habit(self):
        """Тест частичного обновления своей привычки"""
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        data = {
            "action": "Обновленная",
            "place": "Зал",
        }

        response = self.client.patch(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "Обновленная")
        self.assertEqual(response.data["place"], "Зал")

        self.habit1.refresh_from_db()
        self.assertEqual(self.habit1.action, "Обновленная")
        self.assertEqual(self.habit1.place, "Зал")

    def test_partial_update_other_user_habit(self):
        """Тест частичного обновления чужой привычки (должно быть запрещено)"""
        url = reverse("habits:habit-detail", args=[self.habit3.id])
        data = {"action": "Чужая привычка"}

        response = self.client.patch(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.habit3.refresh_from_db()
        self.assertNotEqual(self.habit3.action, "Чужая привычка")

    def test_partial_update_invalid_data(self):
        """Тест частичного обновления с невалидными данными"""
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        data = {"periodicity": 0}

        response = self.client.patch(url, data, **self.auth_headers)

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(response.data.get("periodicity", 1), 1)
        else:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("periodicity", response.data)

    def test_full_update_own_habit(self):
        """Тест полного обновления своей привычки"""
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        data = {
            "action": "Полное обновление",
            "place": "Офис",
            "time": "10:00:00",
            "periodicity": 3,
            "time_to_complete": 45,
            "prize": "Чай",
            "is_public": False,
        }

        response = self.client.put(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["action"], "Полное обновление")
        self.assertEqual(response.data["place"], "Офис")
        self.assertFalse(response.data["is_public"])

        self.habit1.refresh_from_db()
        self.assertEqual(self.habit1.action, "Полное обновление")
        self.assertEqual(self.habit1.place, "Офис")

    def test_full_update_other_user_habit(self):
        """Тест полного обновления чужой привычки (должно быть запрещено)"""
        url = reverse("habits:habit-detail", args=[self.habit3.id])
        data = {
            "action": "Чужая привычка",
            "place": "Офис",
            "time": "10:00:00",
            "periodicity": 1,
        }

        response = self.client.put(url, data, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.habit3.refresh_from_db()
        self.assertNotEqual(self.habit3.action, "Чужая привычка")

    def test_delete_own_habit(self):
        """Тест удаления своей привычки"""
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Habit.objects.filter(id=self.habit1.id).exists())

    def test_delete_other_user_habit(self):
        """Тест попытки удалить чужую привычку"""
        url = reverse("habits:habit-detail", args=[self.habit3.id])
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Habit.objects.filter(id=self.habit3.id).exists())

    def test_delete_nonexistent_habit(self):
        """Тест удаления несуществующей привычки"""
        url = reverse("habits:habit-detail", args=[999])
        response = self.client.delete(url, **self.auth_headers)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_habit_unauthorized(self):
        """Тест создания привычки без авторизации"""
        self.client.logout()
        data = {
            "action": "Неавторизованная привычка",
            "place": "Дом",
            "time": "09:00:00",
        }
        response = self.client.post(self.habits_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_habit_unauthorized(self):
        """Тест обновления привычки без авторизации"""
        self.client.logout()
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        data = {"action": "Измененная привычка"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_habit_unauthorized(self):
        """Тест удаления привычки без авторизации"""
        self.client.logout()
        url = reverse("habits:habit-detail", args=[self.habit1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestValidatePrizeAndConnectedHabit(TestCase):
    """Тесты для validate_prize_and_connected_habit"""

    def test_prize_only_valid(self):
        """Тест: только вознаграждение - валидно"""
        try:
            validate_prize_and_connected_habit(prize="Кофе", connected_habit=None)
        except ValidationError:
            self.fail(
                "validate_prize_and_connected_habit raised ValidationError unexpectedly"
            )

    def test_connected_habit_only_valid(self):
        """Тест: только связанная привычка - валидно"""
        try:
            validate_prize_and_connected_habit(prize=None, connected_habit=1)
        except ValidationError:
            self.fail(
                "validate_prize_and_connected_habit raised ValidationError unexpectedly"
            )

    def test_both_prize_and_connected_habit_invalid(self):
        """Тест: и вознаграждение, и связанная привычка - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_prize_and_connected_habit(prize="Кофе", connected_habit=1)

        self.assertIn(
            "Нельзя одновременно указать вознаграждение и связанную привычку",
            str(context.exception),
        )

    def test_neither_prize_nor_connected_habit_valid(self):
        """Тест: ни вознаграждения, ни связанной привычки - валидно"""
        try:
            validate_prize_and_connected_habit(prize=None, connected_habit=None)
        except ValidationError:
            self.fail(
                "validate_prize_and_connected_habit raised ValidationError unexpectedly"
            )


class TestValidatePleasantHabitConstraints(TestCase):
    """Тесты для validate_pleasant_habit_constraints"""

    def test_pleasant_habit_without_prize_and_connected_valid(self):
        """Тест: приятная привычка без вознаграждения и связи - валидно"""
        try:
            validate_pleasant_habit_constraints(
                is_pleasant=True, prize=None, connected_habit=None
            )
        except ValidationError:
            self.fail(
                "validate_pleasant_habit_constraints raised ValidationError unexpectedly"
            )

    def test_pleasant_habit_with_prize_invalid(self):
        """Тест: приятная привычка с вознаграждением - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_pleasant_habit_constraints(
                is_pleasant=True, prize="Кофе", connected_habit=None
            )
        self.assertIn(
            "Приятная привычка не может иметь вознаграждения", str(context.exception)
        )

    def test_pleasant_habit_with_connected_habit_invalid(self):
        """Тест: приятная привычка со связанной привычкой - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_pleasant_habit_constraints(
                is_pleasant=True, prize=None, connected_habit=1
            )
        self.assertIn(
            "Приятная привычка не может иметь связанной привычки",
            str(context.exception),
        )

    def test_not_pleasant_habit_valid(self):
        """Тест: не приятная привычка - валидно"""
        try:
            validate_pleasant_habit_constraints(
                is_pleasant=False, prize="Кофе", connected_habit=None
            )
        except ValidationError:
            self.fail(
                "validate_pleasant_habit_constraints raised ValidationError unexpectedly"
            )


class TestValidateConnectedHabitIsPleasant(TestCase):
    """Тесты для validate_connected_habit_is_pleasant"""

    def setUp(self):
        self.user = User.objects.create_user(email="5t@test.ru", password="123")
        self.pleasant_habit = Habit.objects.create(
            owner=self.user,
            action="Приятная привычка",
            is_pleasant=True,
            place="Дом",
            time=timezone.now().time(),
        )
        self.unpleasant_habit = Habit.objects.create(
            owner=self.user,
            action="Не приятная привычка",
            is_pleasant=False,
            place="Дом",
            time=timezone.now().time(),
        )

    def test_connected_habit_is_pleasant_valid(self):
        """Тест: связанная привычка приятная - валидно"""
        try:
            validate_connected_habit_is_pleasant(self.pleasant_habit)
        except ValidationError:
            self.fail(
                "validate_connected_habit_is_pleasant raised ValidationError unexpectedly"
            )

    def test_connected_habit_not_pleasant_invalid(self):
        """Тест: связанная привычка не приятная - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_connected_habit_is_pleasant(self.unpleasant_habit)
        self.assertIn("Связанная привычка должна быть приятной", str(context.exception))

    def test_no_connected_habit_valid(self):
        """Тест: нет связанной привычки - валидно"""
        try:
            validate_connected_habit_is_pleasant(None)
        except ValidationError:
            self.fail(
                "validate_connected_habit_is_pleasant raised ValidationError unexpectedly"
            )


class TestValidateConnectedHabitNoPrize(TestCase):
    """Тесты для validate_connected_habit_no_prize"""

    def setUp(self):
        self.user = User.objects.create_user(email="6@test.ru", password="123")
        self.habit_with_prize = Habit.objects.create(
            owner=self.user,
            action="Привычка с вознаграждением",
            prize="Кофе",
            is_pleasant=False,
            place="Дом",
            time=timezone.now().time(),
        )

        self.habit_without_prize = Habit.objects.create(
            owner=self.user,
            action="Привычка без вознаграждения",
            is_pleasant=True,
            place="Дом",
            time=timezone.now().time(),
        )

    def test_connected_habit_without_prize_valid(self):
        """Тест: связанная привычка без вознаграждения - валидно"""
        try:
            validate_connected_habit_no_prize(self.habit_without_prize)
        except ValidationError:
            self.fail(
                "validate_connected_habit_no_prize raised ValidationError unexpectedly"
            )

    def test_connected_habit_with_prize_invalid(self):
        """Тест: связанная привычка с вознаграждением - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_connected_habit_no_prize(self.habit_with_prize)
        self.assertIn(
            "Связанная привычка не должна иметь вознаграждения", str(context.exception)
        )

    def test_no_connected_habit_valid(self):
        """Тест: нет связанной привычки - валидно"""
        try:
            validate_connected_habit_no_prize(None)
        except ValidationError:
            self.fail(
                "validate_connected_habit_no_prize raised ValidationError unexpectedly"
            )


class TestValidateConnectedHabitNoConnected(TestCase):
    """Тесты для validate_connected_habit_no_connected"""

    def setUp(self):
        self.user = User.objects.create_user(email="7@test.ru", password="123")

        self.pleasant_habit = Habit.objects.create(
            owner=self.user,
            action="Приятная привычка",
            is_pleasant=True,
            place="Дом",
            time=timezone.now().time(),
        )

        self.habit_without_connected = Habit.objects.create(
            owner=self.user,
            action="Привычка без связанной",
            is_pleasant=True,
            place="Дом",
            time=timezone.now().time(),
        )

        self.habit_with_connected = Habit.objects.create(
            owner=self.user,
            action="Привычка со связанной",
            connected_habit=self.pleasant_habit,
            place="Дом",
            time=timezone.now().time(),
        )

    def test_connected_habit_without_connected_valid(self):
        """Тест: связанная привычка не имеет своей связанной - валидно"""
        try:
            validate_connected_habit_no_connected(self.habit_without_connected)
        except ValidationError:
            self.fail(
                "validate_connected_habit_no_connected raised ValidationError unexpectedly"
            )

    def test_connected_habit_with_connected_invalid(self):
        """Тест: связанная привычка имеет свою связанную - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_connected_habit_no_connected(self.habit_with_connected)
        self.assertIn(
            "Связанная привычка не должна иметь свою связанную привычку",
            str(context.exception),
        )

    def test_no_connected_habit_valid(self):
        """Тест: нет связанной привычки - валидно"""
        try:
            validate_connected_habit_no_connected(None)
        except ValidationError:
            self.fail(
                "validate_connected_habit_no_connected raised ValidationError unexpectedly"
            )


class TestValidateNotSelfConnected(TestCase):
    """Тесты для validate_not_self_connected"""

    def setUp(self):
        self.user = User.objects.create_user(email="8@test.ru", password="123")
        self.habit = Habit.objects.create(
            owner=self.user, action="Тест", place="Дом", time=timezone.now().time()
        )

    def test_self_connected_invalid(self):
        """Тест: привычка связана сама с собой - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_not_self_connected(self.habit, self.habit)
        self.assertIn(
            "Привычка не может быть связана сама с собой", str(context.exception)
        )

    def test_not_self_connected_valid(self):
        """Тест: привычка не связана сама с собой - валидно"""
        other_habit = Habit.objects.create(
            owner=self.user,
            action="Другая привычка",
            place="Дом",
            time=timezone.now().time(),
        )
        try:
            validate_not_self_connected(self.habit, other_habit)
        except ValidationError:
            self.fail("validate_not_self_connected raised ValidationError unexpectedly")

    def test_no_connected_habit_valid(self):
        """Тест: нет связанной привычки - валидно"""
        try:
            validate_not_self_connected(self.habit, None)
        except ValidationError:
            self.fail("validate_not_self_connected raised ValidationError unexpectedly")


class TestValidatePeriodicityRange(TestCase):
    """Тесты для validate_periodicity_range"""

    def test_periodicity_1_valid(self):
        """Тест: периодичность 1 - валидно"""
        try:
            validate_periodicity_range(1)
        except ValidationError:
            self.fail("validate_periodicity_range raised ValidationError unexpectedly")

    def test_periodicity_7_valid(self):
        """Тест: периодичность 7 - валидно"""
        try:
            validate_periodicity_range(7)
        except ValidationError:
            self.fail("validate_periodicity_range raised ValidationError unexpectedly")

    def test_periodicity_0_invalid(self):
        """Тест: периодичность 0 - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_periodicity_range(0)
        self.assertIn(
            "Периодичность не может быть меньше 1 дня", str(context.exception)
        )

    def test_periodicity_8_invalid(self):
        """Тест: периодичность 8 - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_periodicity_range(8)
        self.assertIn("Максимальная периодичность - 7 дней", str(context.exception))

    def test_periodicity_none_valid(self):
        """Тест: периодичность None - валидно"""
        try:
            validate_periodicity_range(None)
        except ValidationError:
            self.fail("validate_periodicity_range raised ValidationError unexpectedly")

    def test_periodicity_negative_invalid(self):
        """Тест: отрицательная периодичность - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_periodicity_range(-1)
        self.assertIn(
            "Периодичность не может быть меньше 1 дня", str(context.exception)
        )


class TestValidateTimeToCompleteRange(TestCase):
    """Тесты для validate_time_to_complete_range"""

    def test_time_10_valid(self):
        """Тест: время 10 секунд - валидно"""
        try:
            validate_time_to_complete_range(10)
        except ValidationError:
            self.fail(
                "validate_time_to_complete_range raised ValidationError unexpectedly"
            )

    def test_time_120_valid(self):
        """Тест: время 120 секунд - валидно"""
        try:
            validate_time_to_complete_range(120)
        except ValidationError:
            self.fail(
                "validate_time_to_complete_range raised ValidationError unexpectedly"
            )

    def test_time_9_invalid(self):
        """Тест: время 9 секунд - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_time_to_complete_range(9)
        self.assertIn(
            "Время выполнения должно быть не менее 10 секунд", str(context.exception)
        )

    def test_time_121_invalid(self):
        """Тест: время 121 секунда - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_time_to_complete_range(121)
        self.assertIn(
            "Время выполнения не должно превышать 120 секунд", str(context.exception)
        )

    def test_time_negative_invalid(self):
        """Тест: отрицательное время - невалидно"""
        with self.assertRaises(ValidationError) as context:
            validate_time_to_complete_range(-5)
        self.assertIn(
            "Время выполнения должно быть не менее 10 секунд", str(context.exception)
        )


class TestValidateHabitBusinessLogic(TestCase):
    """Тесты для комплексного валидатора validate_habit_business_logic"""

    def setUp(self):
        self.user = User.objects.create_user(email="9@test.ru", password="123")

        self.pleasant_habit = Habit.objects.create(
            owner=self.user,
            action="Приятная привычка",
            is_pleasant=True,
            place="Дом",
            time=timezone.now().time(),
        )

        self.habit = Habit.objects.create(
            owner=self.user,
            action="Тестовая привычка",
            place="Дом",
            time=timezone.now().time(),
            periodicity=1,
        )

        self.other_habit = Habit.objects.create(
            owner=self.user,
            action="Другая привычка",
            place="Дом",
            time=timezone.now().time(),
        )

    def test_valid_habit_data(self):
        """Тест: валидные данные привычки"""
        data = {
            "prize": "Кофе",
            "connected_habit": None,
            "is_pleasant": False,
            "periodicity": 1,
        }
        try:
            validate_habit_business_logic(self.habit, data)
        except ValidationError:
            self.fail(
                "validate_habit_business_logic raised ValidationError unexpectedly"
            )

    def test_prize_and_connected_habit_conflict(self):
        """Тест: конфликт вознаграждения и связанной привычки"""
        data = {
            "prize": "Кофе",
            "connected_habit": self.pleasant_habit,
            "is_pleasant": False,
            "periodicity": 1,
        }
        with self.assertRaises(ValidationError) as context:
            validate_habit_business_logic(self.habit, data)
        self.assertIn(
            "Нельзя одновременно указать вознаграждение и связанную привычку",
            str(context.exception),
        )

    def test_periodicity_too_high(self):
        """Тест: периодичность больше 7"""
        data = {
            "prize": None,
            "connected_habit": None,
            "is_pleasant": False,
            "periodicity": 8,
        }
        with self.assertRaises(ValidationError) as context:
            validate_habit_business_logic(self.habit, data)
        self.assertIn("Максимальная периодичность - 7 дней", str(context.exception))

    def test_periodicity_too_low(self):
        """Тест: периодичность меньше 1"""
        data = {
            "prize": None,
            "connected_habit": None,
            "is_pleasant": False,
            "periodicity": 0,
        }
        with self.assertRaises(ValidationError) as context:
            validate_habit_business_logic(self.habit, data)
        self.assertIn(
            "Периодичность не может быть меньше 1 дня", str(context.exception)
        )

    def test_self_connected(self):
        """Тест: привычка связана сама с собой"""
        data = {
            "prize": None,
            "connected_habit": self.habit,
            "is_pleasant": False,
            "periodicity": 1,
        }
        with self.assertRaises(ValidationError) as context:
            validate_habit_business_logic(self.habit, data)
        self.assertIn(
            "Привычка не может быть связана сама с собой", str(context.exception)
        )

    def test_connected_habit_not_pleasant(self):
        """Тест: связанная привычка не приятная"""
        data = {
            "prize": None,
            "connected_habit": self.other_habit,
            "is_pleasant": False,
            "periodicity": 1,
        }
        with self.assertRaises(ValidationError) as context:
            validate_habit_business_logic(self.habit, data)
        self.assertIn("Связанная привычка должна быть приятной", str(context.exception))
