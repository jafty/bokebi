import secrets
from datetime import datetime, timezone
from django.contrib.auth.hashers import check_password, make_password
from domain.entities import SurveyId
from domain.ports import Clock, SecretGateway, TokenGateway

class SecureTokenGateway(TokenGateway):
    # The deletion key is the only proof of ownership on this accountless
    # service.  Sixteen random bytes provide 128 bits of entropy; grouping the
    # hexadecimal representation keeps it reasonably easy to copy or type.
    DELETION_KEY_BYTES = 16

    def survey_id(self): return SurveyId(secrets.token_urlsafe(9))
    def deletion_key(self):
        key = secrets.token_hex(self.DELETION_KEY_BYTES).upper()
        return "-".join(key[index:index + 4] for index in range(0, len(key), 4))
class DjangoSecretGateway(SecretGateway):
    def encode(self, secret): return make_password(secret)
    def matches(self, secret, encoded): return check_password(secret, encoded)
class SystemClock(Clock):
    def now(self): return datetime.now(timezone.utc)
