from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from rest_framework.response import Response

from .models import Habit
from .paginators import HabitPagination
from .serializer import HabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    queryset = Habit.objects.all()
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HabitPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_public', 'is_pleasant']
    search_fields = ['action', 'place']

    def get_queryset(self):
        user = self.request.user
        return Habit.objects.filter(
            models.Q(owner=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['get'], url_path='public')
    def public_habits(self, request):
        habits = Habit.objects.filter(is_public=True)
        page = self.paginate_queryset(habits)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(habits, many=True)
        return Response(serializer.data)

