class TokenMissing(Exception):
    """Отсутствуют одна или несколько переменных окружения."""

    pass


class APIPracticumNotAvaliable(Exception):
    """API Yandex Practicum не доступен."""

    pass


class HomeworkListEmpty(Exception):
    """Нет домашних работ"""