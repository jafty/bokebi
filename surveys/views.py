import secrets

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

def _require_survey_password(request, survey):
    """Return a password response when access has not yet been granted."""
    if survey.password_hash is None or request.session.get(f"survey_access_{survey.id}"):
        return None
    context = {"survey": survey}
    if request.method == "POST" and "survey_password" in request.POST:
        if DjangoSecretGateway().matches(request.POST["survey_password"], survey.password_hash):
            request.session[f"survey_access_{survey.id}"] = True
            return redirect(request.path)
        context["error"] = "Mot de passe incorrect"
    return render(request, "survey_password.html", context, status=403)

def take_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    cookie_name = f"bokebi_participant_{survey_id}"
    submission_token = request.COOKIES.get(cookie_name) or secrets.token_urlsafe(32)
    if request.method == "POST":
        try:
            answers = tuple(int(request.POST[f"q{i}"]) for i in range(1, len(STANDARD_QUESTIONS) + 1))
            count = SubmitAnswers(surveys, participations).execute(SurveyId(survey_id), answers, submission_token)
            response = render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS, "submitted": True, "count": count})
        except (KeyError, ValueError) as error:
            response = render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS, "error": str(error)}, status=400)
    else:
        response = render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS})
    response.set_cookie(cookie_name, submission_token, max_age=60 * 60 * 24 * 365, httponly=True, samesite="Lax", secure=request.is_secure())
    return response

def contact_opt_in(request, survey_id):
    _survey_or_404(survey_id)
    if request.method == "POST" and (request.POST.get("wants_colleagues") or request.POST.get("wants_organization")):
        try: SubmitContactOptIn(DjangoContactRepository()).execute(request.POST.get("email", ""), bool(request.POST.get("wants_colleagues")), bool(request.POST.get("wants_organization")))
        except ValueError as error: return render(request, "contact_error.html", {"error": str(error)}, status=400)
    return redirect("results", survey_id=survey_id)

def results(request, survey_id):
    survey = _survey_or_404(survey_id)
    password_response = _require_survey_password(request, survey)
    if password_response is not None:
        return password_response
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
