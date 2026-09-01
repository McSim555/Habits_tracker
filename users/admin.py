from django.contrib import admin

from users.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "id",
        "is_active",
        "is_superuser",
        "last_login",
    )
    list_filter = ("is_active", "email", "id")
    search_fields = ("email",)