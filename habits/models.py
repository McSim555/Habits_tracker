from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from .validators import (
    validate_habit_business_logic,
    validate_time_to_complete_range,
    validate_periodicity_range,
)


class Habit(models.Model):
    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Создатель привычки",
        help_text="Введите создателя привычки",
    )

    place = models.CharField(
        max_length=255,
        verbose_name="Место",
        help_text="Укажите место",
    )

    date = models.DateField(verbose_name="Дата",
        help_text="Укажите дату",
                            null=True, blank=True)

    time = models.TimeField(
        verbose_name="Время",
        help_text="Укажите время", null=True, blank=True
    )

    action = models.CharField(
        max_length=500,
        verbose_name="Действие, которое нужно выполнить",
        help_text="Укажите действие",
    )

    is_pleasant = models.BooleanField(
        verbose_name="Приятная привычка",
        help_text="Укажите признак приятной привычки",
        default=False,
    )

    connected_habit = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Связанная привычка',
        related_name='connected_habits'
    )

    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[validate_periodicity_range],
        verbose_name="Периодичность (дни)",
        help_text="Периодичность выполнения привычки в днях (от 1 до 7 дней)"
    )

    prize = models.CharField(
        max_length=500,
        verbose_name="Вознаграждение",
        help_text="Укажите вознаграждение",
        null=True,
        blank=True,
    )

    time_to_complete = models.PositiveSmallIntegerField(
        default=30,
        validators=[validate_time_to_complete_range],
        verbose_name="Время на выполнение (секунды)",
        help_text="Время, которое предположительно потратит пользователь на выполнение привычки (10-120 секунд)"
    )

    is_public = models.BooleanField(
        default=False,
        verbose_name="Признак публичности",
        help_text="Отметьте, если хотите опубликовать привычку в общий доступ"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"
        ordering = ['-created_at']
        constraints = [
            # Проверка: нельзя одновременно иметь prize и connected_habit
            models.CheckConstraint(
                check=~models.Q(prize__isnull=False, connected_habit__isnull=False),
                name='no_both_prize_and_connected_habit'
            ),
            # Проверка: приятная привычка не может иметь prize
            models.CheckConstraint(
                check=~models.Q(is_pleasant=True, prize__isnull=False),
                name='pleasant_no_prize'
            ),
            # Проверка: приятная привычка не может иметь connected_habit
            models.CheckConstraint(
                check=~models.Q(is_pleasant=True, connected_habit__isnull=False),
                name='pleasant_no_connected_habit'
            ),
        ]

    def clean(self):
        """Валидация на уровне модели с использованием валидаторов"""
        try:
            validate_habit_business_logic(self)
        except ValidationError as e:
            errors = {}
            for field, messages in e.message_dict.items():
                errors[field] = messages
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Публичная" if self.is_public else "Закрыта"
        pleasant = "Приятная" if self.is_pleasant else ""
        return f"{status}{pleasant} {self.action} ({self.owner.username if self.owner else 'No owner'})"