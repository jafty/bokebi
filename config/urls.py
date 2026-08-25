from django.urls import include, path
from surveys.views import home

urlpatterns = [path("", home, name="home"), path("", include("surveys.urls"))]
