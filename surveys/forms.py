from django import forms

from domain.entities import Ballot, Situation

SITUATIONS = {
    Situation.OVERTIME: "Mes heures supplémentaires ne sont ni payées ni récupérées.",
    Situation.SCHEDULE: "Mon planning est modifié au dernier moment ou mes horaires sont abusifs.",
    Situation.PRESSURE: "Je subis une pression, un manque de respect ou une mise à l’écart.",
    Situation.HEALTH: "Ma charge de travail pèse sur ma santé physique ou mentale.",
    Situation.PAY: "Mon salaire ou mon poste est bloqué malgré mes responsabilités.",
}


def situation_field():
    return forms.TypedMultipleChoiceField(
        choices=SITUATIONS.items(), coerce=Situation, required=False,
        widget=forms.CheckboxSelectMultiple, label="Coche les situations qui te concernent",
    )


class HelpForm(forms.Form):
    situations = situation_field()
    email = forms.EmailField(
        label="Ton adresse e-mail", help_text="Utilise de préférence ton adresse personnelle.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )


class BallotForm(forms.Form):
    situations = situation_field()
    none_applies = forms.BooleanField(label="Aucune de ces situations ne me concerne", required=False)

    def clean(self):
        cleaned = super().clean()
        if "situations" in cleaned:
            try:
                cleaned["ballot"] = Ballot(
                    frozenset(cleaned["situations"]), cleaned["none_applies"],
                )
            except ValueError as error:
                raise forms.ValidationError(str(error)) from error
        return cleaned


class CreateSurveyForm(forms.Form):
    name = forms.CharField(
        label="Nom de code (facultatif)", help_text="Ce nom sera visible par tes collègues. Exemple : Équipe framboise.",
        max_length=200, required=False,
    )
    password = forms.CharField(
        label="Mot de passe (facultatif)", max_length=128, required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    include_situations = forms.BooleanField(
        label="Ajouter mes situations comme première réponse", required=False,
    )


class SurveyPasswordForm(forms.Form):
    survey_password = forms.CharField(
        label="Mot de passe", max_length=128, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class DeleteSurveyForm(forms.Form):
    deletion_key = forms.CharField(
        label="Clé de suppression", max_length=128,
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )
