from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from domain.entities import STANDARD_QUESTIONS, SurveyId
from domain.use_cases import CreateSurvey, DeleteSurvey, SubmitAnswers, SubmitContactOptIn, ViewSurveyResults
from contacts.repositories import DjangoContactRepository
from .gateways import DjangoSecretGateway, SecureTokenGateway, SystemClock
from .repositories import DjangoParticipationRepository, DjangoSurveyRepository

surveys, participations = DjangoSurveyRepository(), DjangoParticipationRepository()

def home(request): return render(request, "home.html")

def create_survey(request):
    context = {}
    if request.method == "POST":
        try:
            created = CreateSurvey(surveys, SecureTokenGateway(), DjangoSecretGateway(), SystemClock()).execute(request.POST.get("team_name", ""), request.POST.get("password") or None)
            context = {"created": created, "survey_url": request.build_absolute_uri(reverse("take-survey", args=[created.survey.id]))}
        except ValueError as error: context["error"] = str(error)
    return render(request, "create.html", context)

def _survey_or_404(survey_id):
    survey = surveys.get(SurveyId(survey_id))
    if survey is None: raise Http404
    return survey

def take_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    if request.method == "POST":
        try:
            answers = tuple(int(request.POST[f"q{i}"]) for i in range(1, len(STANDARD_QUESTIONS) + 1))
            count = SubmitAnswers(surveys, participations).execute(SurveyId(survey_id), answers)
            return render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS, "submitted": True, "count": count})
        except (KeyError, ValueError) as error:
            return render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS, "error": str(error)}, status=400)
    return render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS})

def contact_opt_in(request, survey_id):
    _survey_or_404(survey_id)
    if request.method == "POST" and (request.POST.get("wants_colleagues") or request.POST.get("wants_organization")):
        try: SubmitContactOptIn(DjangoContactRepository()).execute(request.POST.get("email", ""), bool(request.POST.get("wants_colleagues")), bool(request.POST.get("wants_organization")))
        except ValueError as error: return render(request, "contact_error.html", {"error": str(error)}, status=400)
    return redirect("results", survey_id=survey_id)

def results(request, survey_id):
    survey = _survey_or_404(survey_id)
    result = ViewSurveyResults(surveys, participations).execute(SurveyId(survey_id))
    rows = zip(STANDARD_QUESTIONS, result.averages or ())
    return render(request, "results.html", {"survey": survey, "result": result, "rows": rows, "share_url": request.build_absolute_uri()})

def delete_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    context = {"survey": survey}
    if request.method == "POST":
        try:
            DeleteSurvey(surveys, DjangoSecretGateway()).execute(SurveyId(survey_id), request.POST.get("deletion_key", ""))
            return redirect("home")
        except PermissionError as error: context["error"] = str(error)
    return render(request, "delete_survey.html", context)
