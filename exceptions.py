class MissingCorrectTokens(Exception):
    """Исключение в случае отстутствия необходимых переменных в окружении."""

    pass


class ResponseIsNotCorrect(Exception):
    """Исключение в случае некорректного ответа API."""

    pass
