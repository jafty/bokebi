import re

from surveys.gateways import SecureTokenGateway


def test_deletion_key_has_128_bits_in_readable_groups():
    key = SecureTokenGateway().deletion_key()

    assert re.fullmatch(r"[0-9A-F]{4}(?:-[0-9A-F]{4}){7}", key)
    assert SecureTokenGateway.DELETION_KEY_BYTES == 16
