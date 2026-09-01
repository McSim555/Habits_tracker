from rest_framework import viewsets, permissions, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from .models import Habit
from .serializer import HabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    queryset = Habit.objects.all()
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]  # Только авторизованные
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_public', 'is_pleasant']
    search_fields = ['action', 'place']

    def get_queryset(self):
        user = self.request.user
        return Habit.objects.filter(
            models.Q(owner=user) | models.Q(is_public=True)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)