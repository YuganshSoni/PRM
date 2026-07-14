from client.exceptions import InvalidInputError


class ClientPasswordPolicy:
    MIN_LENGTH = 8

    def validate(self, password: str) -> None:
        if len(password) < self.MIN_LENGTH:
            raise InvalidInputError(
                f"Password must be at least {self.MIN_LENGTH} characters"
            )
        if not any(char.isupper() for char in password):
            raise InvalidInputError(
                "Password must contain at least one uppercase letter"
            )
        if not any(char.isdigit() for char in password):
            raise InvalidInputError("Password must contain at least one number")
