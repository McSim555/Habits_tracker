from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractUser):
    username = None
    email = models.EmailField(
        max_length=255, unique=True, verbose_name="Email", help_text="Укажите e-mail"
    )
    phone = models.CharField(
        max_length=11,
        verbose_name="Номер телефона",
        blank=True,
        null=True,
        help_text="Укажите номер телефона",
    )
    avatar = models.ImageField(
        upload_to="users/images/",
        blank=True,
        null=True,
        verbose_name="Аватар",
        help_text="Вставьте аватар",
    )
    city = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Город",
        help_text="Укажите город",
    )

    chat_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Telegram Chat ID",
        help_text="ID чата в Telegram для получения уведомлений",
    )

    is_telegram_verified = models.BooleanField(
        default=False, verbose_name="Telegram верифицирован"
    )

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
