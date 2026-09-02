from django.contrib import admin

from habits.models import Habit


@admin.register(Habit)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "action",
        "id",
        "is_pleasant",
        "place",
        "time",
    )
    list_filter = ("is_pleasant", "id")
    search_fields = ("id",)
