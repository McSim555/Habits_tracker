from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_prize_and_connected_habit(prize, connected_habit):
    """
    Валидатор: исключить одновременный выбор связанной привычки и указания вознаграждения.
    Можно заполнить только одно из двух полей.
    """
    if prize and connected_habit:
        raise ValidationError(
            _("Нельзя одновременно указать вознаграждение и связанную привычку. "
              "Можно заполнить только одно из двух полей."),
            code='invalid_prize_connected_habit'
        )


def validate_pleasant_habit_constraints(is_pleasant, prize, connected_habit):
    """
    Валидатор: у приятной привычки не может быть вознаграждения или связанной привычки.
    """
    if is_pleasant:
        if prize:
            raise ValidationError(
                _("Приятная привычка не может иметь вознаграждения."),
                code='pleasant_habit_has_prize'
            )
        if connected_habit:
            raise ValidationError(
                _("Приятная привычка не может иметь связанной привычки."),
                code='pleasant_habit_has_connected_habit'
            )


def validate_connected_habit_is_pleasant(connected_habit):
    """
    Валидатор: в связанные привычки могут попадать только привычки с признаком приятной привычки.
    """
    if connected_habit and not connected_habit.is_pleasant:
        raise ValidationError(
            _("Связанная привычка должна быть приятной."),
            code='connected_habit_not_pleasant'
        )


def validate_connected_habit_no_prize(connected_habit):
    """
    Валидатор: связанная привычка не должна иметь вознаграждения.
    """
    if connected_habit and connected_habit.prize:
        raise ValidationError(
            _("Связанная привычка не должна иметь вознаграждения."),
            code='connected_habit_has_prize'
        )


def validate_connected_habit_no_connected(connected_habit):
    """
    Валидатор: связанная привычка не должна иметь свою связанную привычку.
    """
    if connected_habit and connected_habit.connected_habit:
        raise ValidationError(
            _("Связанная привычка не должна иметь свою связанную привычку."),
            code='connected_habit_has_connected'
        )


def validate_not_self_connected(instance, connected_habit):
    """
    Валидатор: привычка не может быть связана сама с собой.
    """
    if connected_habit and instance and connected_habit.id == instance.id:
        raise ValidationError(
            _("Привычка не может быть связана сама с собой."),
            code='self_connected_habit'
        )


def validate_periodicity_range(value):
    """
    Валидатор: периодичность должна быть от 1 до 7 дней.
    Нельзя выполнять привычку реже, чем 1 раз в 7 дней.
    """
    if value < 1:
        raise ValidationError(
            _("Периодичность не может быть меньше 1 дня."),
            code='periodicity_too_low',
            params={'value': value}
        )
    if value > 7:
        raise ValidationError(
            _("Привычку нельзя выполнять реже, чем 1 раз в 7 дней. "
              "Максимальная периодичность - 7 дней."),
            code='periodicity_too_high',
            params={'value': value}
        )


def validate_time_to_complete_range(value):
    """
    Валидатор: время выполнения должно быть от 10 до 120 секунд.
    """
    if value < 10:
        raise ValidationError(
            _("Время выполнения должно быть не менее 10 секунд."),
            code='time_too_short',
            params={'value': value}
        )
    if value > 120:
        raise ValidationError(
            _("Время выполнения не должно превышать 120 секунд."),
            code='time_too_long',
            params={'value': value}
        )


def validate_habit_business_logic(instance, data=None):
    """
    Комплексный валидатор для всей бизнес-логики привычки.
    """
    errors = {}

    prize = data.get('prize') if data else instance.prize
    connected_habit = data.get('connected_habit') if data else instance.connected_habit
    is_pleasant = data.get('is_pleasant') if data else instance.is_pleasant
    periodicity = data.get('periodicity') if data else instance.periodicity

    try:
        validate_prize_and_connected_habit(prize, connected_habit)
    except ValidationError as e:
        errors['prize'] = e.messages
        errors['connected_habit'] = e.messages

    try:
        validate_pleasant_habit_constraints(is_pleasant, prize, connected_habit)
    except ValidationError as e:
        if 'prize' in str(e):
            errors['prize'] = e.messages
        if 'connected_habit' in str(e):
            errors['connected_habit'] = e.messages

    try:
        validate_connected_habit_is_pleasant(connected_habit)
    except ValidationError as e:
        errors['connected_habit'] = e.messages

    try:
        validate_connected_habit_no_prize(connected_habit)
    except ValidationError as e:
        errors['connected_habit'] = e.messages

    try:
        validate_connected_habit_no_connected(connected_habit)
    except ValidationError as e:
        errors['connected_habit'] = e.messages

    try:
        validate_not_self_connected(instance, connected_habit)
    except ValidationError as e:
        errors['connected_habit'] = e.messages

    try:
        validate_periodicity_range(periodicity)
    except ValidationError as e:
        errors['periodicity'] = e.messages

    if errors:
        raise ValidationError(errors)

