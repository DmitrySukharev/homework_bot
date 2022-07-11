class APINotAvailableError(Exception):
    """Для ошибок соединения с API (ConnectionError,  Timeout, и т.д.)."""

    pass


class InvalidHTTPResponseError(Exception):
    """Для ответов API со статусом, отличным от успешного (200)."""

    pass


class CustomJSONDecodeError(Exception):
    """Для ошибки при преобразовании ответа API в словарь."""

    pass


class WrongResponseKeysError(Exception):
    """Для отсутствующих ключей в ответе API, напр. 'homeworks'."""

    pass


class WrongHomeworkStatusError(Exception):
    """Для недокументированных статусов домашней работы."""

    pass
