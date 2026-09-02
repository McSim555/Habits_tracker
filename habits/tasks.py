from celery import shared_task
from django.utils import timezone

from users.models import User

from .models import Habit
from .telegram import TelegramBot, format_habit_message


@shared_task(name="send_habit_reminder", bind=True, max_retries=2)
def send_habit_reminder(self, habit_id, user_id):
    """Отправка напоминания о привычке"""

    habit = Habit.objects.get(id=habit_id)
    user = User.objects.get(id=user_id)

    message = format_habit_message(habit)

    TelegramBot.send_message(user.chat_id, message)


@shared_task(name="check_habits_reminders")
def check_habits_reminders():
    """Проверка привычек и отправка напоминаний по расписанию"""

    now = timezone.now()
    current_time = now.time()
    today = now.date()

    habits = Habit.objects.filter(
        time__lte=current_time,
    )

    for habit in habits:
        try:
            send_habit_reminder.delay(habit.id, habit.owner.id)
        except Exception as e:
            print(f"Ошибка при отправке для привычки {habit.id}: {e}")

    return f"Обработано {habits.count()} привычек"
