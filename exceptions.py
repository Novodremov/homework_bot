class MissingCorrectTokens(Exception):
    """Исключение в случае отсутствия необходимых переменных в окружении."""

    pass


class SendMessageError(Exception):
    """Исключение в случае невозможности отправки сообщения пользователю."""

    pass
