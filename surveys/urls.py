from django.urls import path
from . import views

urlpatterns = [
    path("surveys/new/", views.create_survey, name="create"),
    path("s/<str:survey_id>/", views.take_survey, name="take-survey"),
    path("s/<str:survey_id>/contact/", views.contact_opt_in, name="contact-opt-in"),
    path("s/<str:survey_id>/results/", views.results, name="results"),
    path("s/<str:survey_id>/delete/", views.delete_survey, name="delete-survey"),
]
