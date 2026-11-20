from django.urls import path

from . import views

urlpatterns = [
    path("informations/<str:page>/", views.information_page, name="information-page"),
    path("aide/", views.help_form, name="request-help"),
    path("aide/<str:token>/confirmation/", views.help_sent, name="help-sent"),
    path("aide/<str:token>/partage/", views.create_survey, name="create"),
    path("aide/<str:token>/lien/", views.survey_ready, name="survey-ready"),
    path("s/<str:survey_id>/", views.take_survey, name="take-survey"),
    path("s/<str:survey_id>/aide/", views.help_form, name="survey-help"),
    path("s/<str:survey_id>/results/", views.results, name="results"),
    path("s/<str:survey_id>/delete/", views.delete_survey, name="delete-survey"),
]
