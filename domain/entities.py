from dataclasses import dataclass
from datetime import datetime
from typing import NewType

SurveyId = NewType("SurveyId", str)

STANDARD_QUESTIONS = (
    "Mes heures de travail réelles correspondent exactement à mes heures rémunérées (pas d'heures supplémentaires non payées).",
    "Mon emploi du temps est respecté et communiqué suffisamment à l'avance.",
    "Je me sens respecté(e) et écouté(e) par ma hiérarchie dans l'exercice de mes fonctions.",
    "Mes conditions de travail me permettent de préserver ma santé physique et mentale.",
    "J'estime que ma rémunération est juste par rapport à la charge de travail demandée.",
)

@dataclass(frozen=True)
class Survey:
    id: SurveyId
    team_name: str
    deletion_key_hash: str
    password_hash: str | None
    created_at: datetime

@dataclass(frozen=True)
class Participation:
    survey_id: SurveyId
    answers: tuple[int, ...]

@dataclass(frozen=True)
class ContactRequest:
    email: str
    wants_colleagues: bool
    wants_organization: bool

    def __post_init__(self) -> None:
        if not self.email.strip() or "@" not in self.email:
            raise ValueError("A valid email is required")
        if not (self.wants_colleagues or self.wants_organization):
            raise ValueError("At least one contact option is required")
