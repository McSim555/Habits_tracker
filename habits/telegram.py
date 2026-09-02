import requests
from django.conf import settings


class TelegramBot:
    """Класс для работы с Telegram ботом"""

    BASE_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"

    @classmethod
    def send_message(cls, chat_id, message):
        """
        Отправка сообщения пользователю
        """
        if not chat_id:
            print("chat_id не указан")
            return False

        try:
            url = f"{cls.BASE_URL}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
            }

            print(f"Отправка сообщения в чат {chat_id}")

            requests.post(url, json=payload, timeout=30)

        except requests.exceptions.Timeout:
            print(f"Таймаут при отправке сообщения в чат {chat_id}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"Ошибка подключения к Telegram API")
            return False
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при отправке сообщения: {e}")
            return False


def format_habit_message(habit):
    """
    Форматирование сообщения о привычке
    """
    message = "Напоминание о привычке!\n\n"
    message += f"Действие: {habit.action}\n"

    if habit.place:
        message += f"Место: {habit.place}\n"

    message += f"Время: {habit.time.strftime('%H:%M')}\n"

    if habit.periodicity == 1:
        message += f"Периодичность: Ежедневно\n"
    else:
        message += f"Периодичность: Каждые {habit.periodicity} дней\n"

    if habit.time_to_complete:
        message += f"Время выполнения: {habit.time_to_complete} сек\n"

    if habit.prize:
        message += f"Вознаграждение: {habit.prize}\n"

    return message
