from copilot.redact import redact


def test_redacts_common_secrets():
    text = ("db password=hunter2 key AKIAABCDEFGHIJKLMNOP "
            "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnop")
    clean, kinds = redact(text)
    assert "hunter2" not in clean and "AKIAABCDEFGHIJKLMNOP" not in clean and "eyJhbGci" not in clean
    assert {"password", "aws_access_key", "jwt"} <= set(kinds)


def test_keeps_normal_logs():
    line = "ERROR KeyError: 'PAYMENTS_DB_URL' environment variable is not set"
    assert redact(line) == (line, [])
