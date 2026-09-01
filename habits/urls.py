from django.urls import path
from rest_framework.routers import SimpleRouter
from habits.apps import HabitsConfig

app_name = HabitsConfig.name

router = SimpleRouter()
router.register("courses", HabitViewSet, basename="course")

urlpatterns = []

urlpatterns += router.urls
