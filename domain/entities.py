from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import NewType

SurveyId = NewType("SurveyId", str)
MINIMUM_PARTICIPATIONS = 3
RESPONSE_DELAY = timedelta(hours=24)
CLOSED_RETENTION = timedelta(days=30)


class Situation(StrEnum):
    OVERTIME = "overtime"
    SCHEDULE = "schedule"
    PRESSURE = "pressure"
    HEALTH = "health"
    PAY = "pay"


def validate_situations(situations: frozenset[Situation]) -> None:
    if not situations.issubset(Situation):
        raise ValueError("Situation inconnue.")


class HelpStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


NEXT_STATUSES = {
    HelpStatus.NEW: (HelpStatus.CONTACTED, HelpStatus.CLOSED),
    HelpStatus.CONTACTED: (HelpStatus.IN_PROGRESS, HelpStatus.CLOSED),
    HelpStatus.IN_PROGRESS: (HelpStatus.CLOSED,),
    HelpStatus.CLOSED: (),
}


@dataclass(frozen=True)
class HelpRequest:
    id: str
    email: str
    situations: frozenset[Situation]
    survey_id: SurveyId
    from_survey: bool
    created_at: datetime
    status: HelpStatus = HelpStatus.NEW
    contacted_at: datetime | None = None
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        validate_situations(self.situations)

    @property
    def deadline(self) -> datetime:
        return self.created_at + RESPONSE_DELAY

    def transition(self, status: HelpStatus, now: datetime) -> "HelpRequest":
        if status == self.status:
            return self
        if status not in NEXT_STATUSES[self.status]:
            raise ValueError("Transition de statut impossible.")
        return replace(
            self,
            status=status,
            contacted_at=now if status == HelpStatus.CONTACTED else self.contacted_at,
            closed_at=now if status == HelpStatus.CLOSED else None,
        )


@dataclass(frozen=True)
class Ballot:
    situations: frozenset[Situation]
    none_applies: bool = False

    def __post_init__(self) -> None:
        validate_situations(self.situations)
        if bool(self.situations) == self.none_applies:
            raise ValueError("Choisis les situations qui te concernent ou indique qu’aucune ne s’applique.")


@dataclass(frozen=True)
class Survey:
    id: SurveyId
    name: str
    deletion_key_hash: str
    password_hash: str | None
    created_at: datetime
    response_count: int = 0
    counts: tuple[int, ...] = (0,) * len(Situation)

    def count(self, ballot: Ballot) -> "Survey":
        return replace(
            self,
            response_count=self.response_count + 1,
            counts=tuple(
                count + (situation in ballot.situations)
                for situation, count in zip(Situation, self.counts, strict=True)
            ),
        )

    @property
    def results(self) -> tuple[int, ...] | None:
        if self.response_count < MINIMUM_PARTICIPATIONS:
            return None
        return self.counts
