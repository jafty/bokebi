from datetime import datetime, timezone

from django.contrib.auth.hashers import check_password, make_password


class DjangoSecretGateway:
    def encode(self, secret: str) -> str:
        return make_password(secret)

    def matches(self, secret: str, encoded: str) -> bool:
        return check_password(secret, encoded)


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
