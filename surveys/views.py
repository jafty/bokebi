from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from domain.entities import STANDARD_QUESTIONS, SurveyId
from domain.use_cases import CheckSurveyPassword, CreateSurvey, DeleteSurvey, SubmitAnswers, SubmitContactOptIn, ViewSurveyResults
from contacts.repositories import DjangoContactRepository
from .gateways import DjangoSecretGateway, SecureTokenGateway, SystemClock
from .repositories import DjangoParticipationRepository, DjangoSurveyRepository

surveys, participations = DjangoSurveyRepository(), DjangoParticipationRepository()

def home(request): return render(request, "home.html", {"questions": STANDARD_QUESTIONS})


FOOTER_PAGES = {
    "legal": {
        "title": "Mentions légales",
        "intro": "Les informations essentielles sur l'édition et l'utilisation de Bokebi.",
        "sections": (
            ("Éditeur du site", "Le site Bokebi est édité à titre non professionnel par un particulier au sens de l'article 6, III, 2 de la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique (LCEN). Les coordonnées personnelles de l'auteur ont été transmises à l'hébergeur du site."),
            ("Contact", "Pour toute question ou demande de modération : contact@bokebi.org"),
            ("Hébergement", "Le site est hébergé par :\nRailway Corp.\n548 Market St, Suite 500\nSan Francisco, CA 94104, États-Unis\nSite web : https://railway.app"),
            ("Données personnelles", "Aucun nom ni e-mail n'est demandé avec les réponses. Les coordonnées fournies pour une demande de contact sont conservées séparément. Dans un petit groupe, il peut néanmoins être possible de deviner une réponse."),
        ),
    },
    "privacy": {
        "title": "Confidentialité et sécurité",
        "intro": "Voici ce que Bokebi recueille et les limites de la confidentialité.",
        "sections": (
            ("Sondages sans compte", "Aucun compte n'est nécessaire. Les réponses ne demandent ni nom, ni matricule, ni texte libre susceptible d'identifier son auteur."),
            ("Résultats", "Les moyennes apparaissent à partir de trois participations. Dans un petit groupe, ou en comparant les résultats au fil du temps, il peut être possible de deviner une réponse."),
            ("Demandes de contact séparées", "Si tu demandes à être contacté, l'équipe Bokebi voit ton e-mail, tes choix et le nom du groupe. Ces informations et leur date sont conservées séparément des réponses, sans identifiant de sondage. Le nom du groupe et les horaires peuvent néanmoins permettre des rapprochements."),
            ("Partage du lien", "Toute personne ayant le lien peut répondre et consulter les résultats disponibles. Un mot de passe peut en limiter l'accès. Partage-le séparément et choisis un mot de passe différent de tes mots de passe habituels."),
        ),
    },
    "ethics": {
        "title": "Charte éthique",
        "intro": "Bokebi aide à faire émerger un constat collectif en limitant les informations recueillies.",
        "sections": (
            ("Confidentialité", "Nous minimisons les données collectées et ne revendons aucune donnée personnelle."),
            ("Libre choix", "Répondre, demander une mise en relation ou solliciter un organisme reste toujours facultatif."),
            ("Neutralité", "Les résultats restituent les réponses reçues. Ils ne servent ni à noter individuellement des salariés, ni à désigner une personne."),
            ("Usage responsable", "Le service ne doit pas être utilisé pour harceler, identifier ou surveiller des collègues, ni pour diffuser un lien hors du groupe concerné."),
        ),
    },
    "contact": {
        "title": "Contact",
        "intro": "Une question sur Bokebi, un signalement de sécurité ou une demande relative à tes données ?",
        "sections": (
            ("Nous écrire", "Pour contacter l'équipe, utilise le canal par lequel elle t'a présenté Bokebi."),
            ("Urgence", "Bokebi n'est pas un service d'urgence. En cas de danger immédiat, contacte les services d'urgence ou les interlocuteurs compétents de ton pays."),
        ),
    },
}


def information_page(request, page):
    content = FOOTER_PAGES.get(page)
    if content is None:
        raise Http404
    return render(request, "information_page.html", content)

@never_cache
def create_survey(request):
    context = {}
    if request.method == "POST":
        try:
            team_name = request.POST.get("team_name", "")
            if len(team_name.strip()) > 200:
                return render(request, "create.html", {"error": "Le nom doit contenir 200 caractères au maximum.", "team_name": team_name}, status=400)
            created = CreateSurvey(surveys, SecureTokenGateway(), DjangoSecretGateway(), SystemClock()).execute(team_name, request.POST.get("password") or None)
            if created.survey.password_hash:
                request.session[f"survey_access_{created.survey.id}"] = True
            context = {"created": created}
        except ValueError: context = {"error": "Indique un nom pour ton équipe ou ton lieu de travail.", "team_name": request.POST.get("team_name", "")}
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
        if CheckSurveyPassword(DjangoSecretGateway()).execute(survey, request.POST["survey_password"]):
            request.session[f"survey_access_{survey.id}"] = True
            return redirect(request.path)
        context["error"] = "Mot de passe incorrect"
    return render(request, "survey_password.html", context, status=403)

def take_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    password_response = _require_survey_password(request, survey)
    if password_response is not None:
        return password_response
    if request.method == "POST":
        try:
            answers = tuple(int(request.POST[f"q{i}"]) for i in range(1, len(STANDARD_QUESTIONS) + 1))
            count = SubmitAnswers(surveys, participations).execute(SurveyId(survey_id), answers)
            return render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS, "submitted": True, "count": count})
        except (KeyError, ValueError) as error:
            return render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS, "error": str(error)}, status=400)
    return render(request, "take_survey.html", {"survey": survey, "questions": STANDARD_QUESTIONS})

def contact_opt_in(request, survey_id):
    survey = _survey_or_404(survey_id)
    password_response = _require_survey_password(request, survey)
    if password_response is not None:
        return password_response
    if request.method == "POST" and (request.POST.get("wants_colleagues") or request.POST.get("wants_organization")):
        try: SubmitContactOptIn(DjangoContactRepository()).execute(request.POST.get("email", ""), bool(request.POST.get("wants_colleagues")), bool(request.POST.get("wants_organization")), survey.team_name)
        except ValueError: return render(request, "take_survey.html", {"survey": survey, "submitted": True, "error": "Indique une adresse e-mail valide.", "email": request.POST.get("email", ""), "wants_colleagues": request.POST.get("wants_colleagues"), "wants_organization": request.POST.get("wants_organization")}, status=400)
    return redirect("share-survey", survey_id=survey_id)

def share_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    password_response = _require_survey_password(request, survey)
    if password_response is not None:
        return password_response
    return render(request, "share.html", {"survey": survey, "poll_url": request.build_absolute_uri(reverse("take-survey", args=[survey.id]))})

def results(request, survey_id):
    survey = _survey_or_404(survey_id)
    password_response = _require_survey_password(request, survey)
    if password_response is not None:
        return password_response
    result = ViewSurveyResults(surveys, participations).execute(SurveyId(survey_id))
    rows = tuple(zip(STANDARD_QUESTIONS, result.averages or ()))
    return render(request, "results.html", {
        "survey": survey,
        "result": result,
        "rows": rows,
        "poll_url": request.build_absolute_uri(reverse("take-survey", args=[survey.id])),
        "results_url": request.build_absolute_uri(),
    })

def delete_survey(request, survey_id):
    survey = _survey_or_404(survey_id)
    context = {"survey": survey}
    if request.method == "POST":
        try:
            DeleteSurvey(surveys, DjangoSecretGateway()).execute(SurveyId(survey_id), request.POST.get("deletion_key", ""))
            return redirect("home")
        except PermissionError as error: context["error"] = str(error)
    return render(request, "delete_survey.html", context)
