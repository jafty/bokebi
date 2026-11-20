from uuid import uuid4

from django.core import signing
from django.utils.crypto import salted_hmac

FLOW_LIFETIME = 3600


def browser_key(request):
    if "bokebi_browser" not in request.session:
        request.session["bokebi_browser"] = uuid4().hex
    return request.session["bokebi_browser"]


def start_help(request, survey_id):
    return signing.dumps(
        {"id": uuid4().hex, "survey": survey_id}, salt=f"bokebi.help.form.{browser_key(request)}",
    )


def read_help(request, token):
    try:
        return signing.loads(token, salt=f"bokebi.help.form.{browser_key(request)}", max_age=FLOW_LIFETIME)
    except signing.BadSignature:
        return None


def confirm_help(request, request_id):
    return signing.dumps(request_id, salt=f"bokebi.help.confirm.{browser_key(request)}")


def read_confirmation(request, token):
    try:
        return signing.loads(
            token, salt=f"bokebi.help.confirm.{browser_key(request)}", max_age=FLOW_LIFETIME,
        )
    except signing.BadSignature:
        return None


def private_token(request, purpose, value):
    return salted_hmac(purpose, value, secret=browser_key(request), algorithm="sha256").hexdigest()


def vote_receipt(request, survey_id):
    return private_token(request, "bokebi.vote", survey_id)
