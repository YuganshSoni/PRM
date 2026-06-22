from typing import ClassVar

from server.core.exceptions import WeakPasswordError


class PasswordPolicy:
    MIN_LENGTH: ClassVar[int] = 8

    def validate(self, password: str) -> None:
        if len(password) < self.MIN_LENGTH:
            raise WeakPasswordError(
                f"Password must be at least {self.MIN_LENGTH} characters"
            )
        if not any(char.isupper() for char in password):
            raise WeakPasswordError("Password must contain at least one uppercase letter")
        if not any(char.isdigit() for char in password):
            raise WeakPasswordError("Password must contain at least one number")
