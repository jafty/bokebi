from abc import ABC, abstractmethod
from .entities import ContactRequest, Participation, Survey, SurveyId

class SurveyRepository(ABC):
    @abstractmethod
    def add(self, survey: Survey) -> None: ...
    @abstractmethod
    def get(self, survey_id: SurveyId) -> Survey | None: ...
    @abstractmethod
    def delete(self, survey_id: SurveyId) -> None: ...

class ParticipationRepository(ABC):
    @abstractmethod
    def add(self, participation: Participation) -> bool:
        """Store a participation, returning false when its token was already used."""
        ...
    @abstractmethod
    def for_survey(self, survey_id: SurveyId) -> list[Participation]: ...

class ContactRepository(ABC):
    @abstractmethod
    def add(self, request: ContactRequest) -> None: ...

class TokenGateway(ABC):
    @abstractmethod
    def survey_id(self) -> SurveyId: ...
    @abstractmethod
    def deletion_key(self) -> str: ...

class SecretGateway(ABC):
    @abstractmethod
    def encode(self, secret: str) -> str: ...
    @abstractmethod
    def matches(self, secret: str, encoded: str) -> bool: ...

class Clock(ABC):
    @abstractmethod
    def now(self): ...
