"""Password policy: length bounds (in schemas) + a blocklist of very common passwords.

Follows NIST SP 800-63B: no composition rules, reject known-compromised/common values.
"""

COMMON_PASSWORDS = frozenset(
    {
        "1234567890",
        "12345678910",
        "0123456789",
        "1111111111",
        "0000000000",
        "1q2w3e4r5t",
        "1qaz2wsx3edc",
        "qwertyuiop",
        "qwertyuiop1",
        "asdfghjkl1",
        "zxcvbnm123",
        "password12",
        "password123",
        "password1234",
        "passw0rd123",
        "iloveyou12",
        "iloveyou123",
        "letmein123",
        "welcome123",
        "welcome1234",
        "admin12345",
        "administrator",
        "football123",
        "baseball123",
        "sunshine123",
        "princess123",
        "superman123",
        "trustno1234",
        "changeme123",
        "qwerty12345",
        "qwerty123456",
        "abc1234567",
        "abcdefghij",
        "abcd123456",
        "dragon12345",
        "monkey12345",
        "travel1234",
        "travel12345",
        "traveller1",
        "wanderlust",
        "wanderlust1",
    }
)


def validate_password_strength(password: str) -> str:
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS:
        raise ValueError("This password is too common. Choose something harder to guess.")
    if len(set(password)) < 4:
        raise ValueError("This password is too repetitive. Use a longer mix of characters.")
    return password
