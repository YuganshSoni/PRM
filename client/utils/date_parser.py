from datetime import date, datetime

from client.exceptions import InvalidInputError


class DateInputParser:
    _FORMAT = "%d-%m-%Y"

    @classmethod
    def parse(cls, value: str) -> date:
        text = value.strip()
        try:
            return datetime.strptime(text, cls._FORMAT).date()
        except ValueError as exc:
            raise InvalidInputError(
                "Invalid date. Use DD-MM-YYYY format."
            ) from exc

    @classmethod
    def format(cls, value: date) -> str:
        return value.strftime(cls._FORMAT)
