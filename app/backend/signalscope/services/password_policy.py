from signalscope.core.errors import AppError

MIN_LENGTH = 10
MAX_LENGTH = 128

# A short list of the most common passwords that still pass the length rule.
_COMMON = {
    "password12",
    "password123",
    "password1234",
    "1234567890",
    "12345678910",
    "qwertyuiop",
    "qwerty12345",
    "iloveyou123",
    "abcdefghij",
    "abc1234567",
    "welcome123",
    "letmein1234",
    "passw0rd123",
    "administrator",
    "0987654321",
    "1q2w3e4r5t",
}


def check_password(password: str, email: str, field: str = "password") -> None:
    """Raise a 422 with a user-facing message if the password is too weak."""

    def fail(message: str) -> AppError:
        return AppError(422, "weak_password", message, field=field)

    if len(password) < MIN_LENGTH:
        raise fail(f"Password must be at least {MIN_LENGTH} characters.")
    if len(password) > MAX_LENGTH:
        raise fail(f"Password must be at most {MAX_LENGTH} characters.")
    if len(set(password)) < 4:
        raise fail("Password is too repetitive.")
    lowered = password.lower()
    if lowered in _COMMON:
        raise fail("That password is too common. Please choose another.")
    local_part = email.split("@", 1)[0].lower()
    if len(local_part) >= 3 and local_part in lowered:
        raise fail("Password must not contain your email address.")
