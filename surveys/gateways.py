import secrets
from datetime import datetime, timezone
from django.contrib.auth.hashers import check_password, make_password
from domain.entities import SurveyId
from domain.ports import Clock, SecretGateway, TokenGateway

class SecureTokenGateway(TokenGateway):
    def survey_id(self): return SurveyId(secrets.token_urlsafe(9))
    def deletion_key(self): return secrets.token_urlsafe(24)
class DjangoSecretGateway(SecretGateway):
    def encode(self, secret): return make_password(secret)
    def matches(self, secret, encoded): return check_password(secret, encoded)
class SystemClock(Clock):
    def now(self): return datetime.now(timezone.utc)
