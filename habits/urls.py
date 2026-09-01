from django.urls import path
from rest_framework.routers import SimpleRouter

app_name = HabitsConfig.name

router = SimpleRouter()
router.register("courses", HabitsViewSet, basename="course")

urlpatterns = []

urlpatterns += router.urls
