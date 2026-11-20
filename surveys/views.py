from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from contacts.notifications import DjangoHelpNotifications
from contacts.repositories import DjangoHelpRepository
from domain.entities import SurveyId
from domain.use_cases import CreateSurvey, DeleteSurvey, RequestHelp

from .forms import BallotForm, CreateSurveyForm, DeleteSurveyForm, HelpForm, SITUATIONS, SurveyPasswordForm
from .gateways import DjangoSecretGateway, SystemClock
from .repositories import DjangoSurveyRepository
from .session import (
    FLOW_LIFETIME, browser_key, confirm_help, private_token, read_confirmation, read_help,
    start_help, vote_receipt,
)

surveys = DjangoSurveyRepository()
help_requests = DjangoHelpRepository()
secrets = DjangoSecretGateway()
clock = SystemClock()

FOOTER_PAGES = {
    "legal": (
        "Mentions légales",
        (
            ("Éditeur du site", "Le site Bokebi est édité à titre non professionnel par un particulier au sens de l’article 6, III, 2 de la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l’économie numérique (LCEN). Ses coordonnées ont été transmises à l’hébergeur."),
            ("Hébergement", "Railway Corp., 548 Market St, Suite 500, San Francisco, CA 94104, États-Unis."),
            ("Contact", "Pour toute question, écris à entraide@bokebi.fr."),
        ),
    ),
    "privacy": (
        "Confidentialité",
        (
            ("Demander de l’aide", "Bokebi reçoit ton adresse e-mail et les situations que tu as choisies pour te répondre. Les demandes faites depuis un sondage ou suivies de sa création peuvent être regroupées par sondage dans l’espace réservé à l’équipe."),
            ("Répondre à un sondage", "Le sondage ne demande ni nom ni adresse e-mail. Les résultats regroupés sont accessibles avec le lien à partir de trois réponses. Dans un petit groupe, certaines réponses peuvent être devinées en comparant les résultats."),
            ("Mises en relation", "Les coordonnées sont partagées avec d’autres personnes uniquement avec l’accord explicite des personnes concernées."),
            ("Conservation", "Les demandes sont supprimées de l’application 30 jours après leur clôture. Les résultats restent disponibles tant que le sondage existe. La suppression dans l’application ne supprime pas les messages déjà échangés par e-mail. Les copies de sauvegarde expirent selon le cycle de sauvegarde de l’hébergement."),
        ),
    ),
    "ethics": (
        "Charte éthique",
        (
            ("Libre choix", "Chacun décide de demander de l’aide, de participer à un sondage ou d’accepter une mise en relation."),
            ("Usage responsable", "Utilise les résultats pour discuter des conditions de travail. Respecte la confidentialité des personnes qui y participent."),
        ),
    ),
    "contact": ("Contact", (("Nous écrire", "Écris à entraide@bokebi.fr."),)),
}


def home(request):
    return render(request, "home.html")


def information_page(request, page):
    if page not in FOOTER_PAGES:
        raise Http404
    title, sections = FOOTER_PAGES[page]
    return render(request, "information_page.html", {"title": title, "sections": sections})


def _survey_or_404(survey_id):
    survey = surveys.get(SurveyId(survey_id))
    if survey is None:
        raise Http404
    return survey


def _password_response(request, survey):
    if survey.password_hash is None or request.session.get(f"survey_access_{survey.id}"):
        return None
    form = SurveyPasswordForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        if secrets.matches(form.cleaned_data["survey_password"], survey.password_hash):
            request.session[f"survey_access_{survey.id}"] = True
            return redirect(request.path)
        form.add_error("survey_password", "Mot de passe incorrect.")
    return render(request, "survey_password.html", {"form": form}, status=403)


def _flow_request(request, token):
    request_id = read_confirmation(request, token)
    record = None if request_id is None else help_requests.get(request_id)
    if record is None or clock.now() - record.created_at > timedelta(seconds=FLOW_LIFETIME):
        raise Http404
    return record


@never_cache
@require_http_methods(["GET", "POST"])
def help_form(request, survey_id=None):
    if survey_id is not None:
        survey = _survey_or_404(survey_id)
        blocked = _password_response(request, survey)
        if blocked is not None:
            return blocked
    form = HelpForm()
    token = start_help(request, survey_id)
    if request.method == "POST":
        form = HelpForm(request.POST)
        submitted_token = request.POST.get("flow", "")
        payload = read_help(request, submitted_token)
        if payload is None or payload["survey"] != survey_id:
            form.add_error(None, "Le formulaire a expiré. Tu peux l’envoyer à nouveau.")
        elif form.is_valid():
            RequestHelp(help_requests, clock, DjangoHelpNotifications()).execute(
                payload["id"], form.cleaned_data["email"], form.cleaned_data["situations"],
                SurveyId(survey_id or uuid4().hex), from_survey=survey_id is not None,
            )
            return redirect("help-sent", token=confirm_help(request, payload["id"]))
        else:
            token = submitted_token
    return render(request, "help_form.html", {"form": form, "flow": token, "survey_id": survey_id},
                  status=400 if request.method == "POST" else 200)


@never_cache
@require_http_methods(["GET"])
def help_sent(request, token):
    record = _flow_request(request, token)
    linked_survey_id = record.survey_id if record.from_survey else None
    return render(request, "help_sent.html", {"linked_survey_id": linked_survey_id, "flow": token})


def _share_context(request, survey):
    poll_url = request.build_absolute_uri(reverse("take-survey", args=[survey.id]))
    share_text = f"Salut ! Voici un petit sondage sur nos conditions de travail. Si tu veux y répondre : {poll_url}"
    return {"poll_url": poll_url, "whatsapp_url": f"https://wa.me/?{urlencode({'text': share_text})}"}


@never_cache
@require_http_methods(["GET", "POST"])
def create_survey(request, token):
    record = _flow_request(request, token)
    if record.from_survey:
        raise Http404
    form = CreateSurveyForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        deletion_key = private_token(request, "bokebi.delete", record.id)[:32]
        survey = CreateSurvey(surveys, secrets, clock).execute(
            record, form.cleaned_data["name"], form.cleaned_data["password"], deletion_key,
            include_situations=form.cleaned_data["include_situations"],
            receipt=vote_receipt(request, record.survey_id),
        )
        if survey is None:
            raise Http404
        request.session[f"survey_access_{survey.id}"] = True
        return redirect("survey-ready", token=token)
    return render(request, "create.html", {"form": form, "can_seed": bool(record.situations)},
                  status=400 if request.method == "POST" else 200)


@never_cache
@require_http_methods(["GET"])
def survey_ready(request, token):
    record = _flow_request(request, token)
    if record.from_survey:
        raise Http404
    survey = _survey_or_404(record.survey_id)
    return render(request, "survey_ready.html", {
        "survey": survey,
        "deletion_key": private_token(request, "bokebi.delete", record.id)[:32],
        **_share_context(request, survey),
    })


@never_cache
@require_http_methods(["GET", "POST"])
def take_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    blocked = _password_response(request, survey)
    if blocked is not None:
        return blocked
    browser_key(request)
    form = BallotForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        try:
            created = surveys.add_ballot(
                survey.id, vote_receipt(request, survey.id), form.cleaned_data["ballot"],
            )
        except LookupError as error:
            raise Http404 from error
        notice = "Merci. Ta réponse a été enregistrée." if created else "Une réponse a déjà été enregistrée depuis ce navigateur."
        messages.info(request, notice, extra_tags=survey.id)
        return redirect("results", survey_id=survey.id)
    return render(request, "take_survey.html", {"survey": survey, "form": form},
                  status=400 if request.method == "POST" else 200)


@never_cache
@require_http_methods(["GET", "POST"])
def results(request, survey_id):
    survey = _survey_or_404(survey_id)
    blocked = _password_response(request, survey)
    if blocked is not None:
        return blocked
    counts = survey.results
    rows = None if counts is None else tuple(zip(SITUATIONS.values(), counts, strict=True))
    return render(request, "results.html", {"survey": survey, "rows": rows, **_share_context(request, survey)})


@never_cache
@require_http_methods(["GET", "POST"])
def delete_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    form = DeleteSurveyForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        try:
            DeleteSurvey(surveys, secrets).execute(survey, form.cleaned_data["deletion_key"])
        except PermissionError as error:
            form.add_error("deletion_key", str(error))
        else:
            return redirect("home")
    return render(request, "delete_survey.html", {"form": form},
                  status=400 if request.method == "POST" else 200)
