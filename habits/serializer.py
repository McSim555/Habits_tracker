from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import Habit
from .validators import (validate_connected_habit_is_pleasant,
                         validate_habit_business_logic,
                         validate_periodicity_range,
                         validate_time_to_complete_range)


class HabitSerializer(serializers.ModelSerializer):
    time_display = serializers.SerializerMethodField()
    periodicity_display = serializers.SerializerMethodField()

    class Meta:
        model = Habit
        fields = [
            "id",
            "owner",
            "place",
            "time_display",
            "action",
            "is_pleasant",
            "is_public",
            "periodicity_display",
            "time_to_complete",
            "connected_habit",
            "prize",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["owner", "created_at", "updated_at"]

    def validate_time_to_complete(self, value):
        """Валидация времени выполнения"""
        try:
            validate_time_to_complete_range(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate_periodicity(self, value):
        """Валидация периодичности"""
        try:
            validate_periodicity_range(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate_connected_habit(self, value):
        """Валидация связанной привычки"""
        if value:
            try:
                validate_connected_habit_is_pleasant(value)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        """
        Основная валидация с использованием комплексного валидатора
        """
        instance = self.instance if self.instance else Habit()

        for field, value in data.items():
            setattr(instance, field, value)

        try:
            validate_habit_business_logic(instance, data)
        except ValidationError as e:
            errors = {}
            for field, messages in e.message_dict.items():
                errors[field] = messages
            raise serializers.ValidationError(errors)

        return data

    def get_time_display(self, obj):
        if obj.time:
            if hasattr(obj, "date") and obj.date:
                return obj.date.strftime("%d.%m.%Y") + " " + obj.time.strftime("%H:%M")
            if hasattr(obj, "created_at") and obj.created_at:
                return obj.created_at.strftime("%d.%m.%Y %H:%M")
        return None

    def get_periodicity_display(self, obj):
        return f"Каждые {obj.periodicity} дней"
