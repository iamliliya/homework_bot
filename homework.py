import telegram
import exceptions
import json
import logging
import os
import sys
import requests
import time


from dotenv import load_dotenv
from http import HTTPStatus
from telegram import Bot


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot: Bot, message: str):
    """Функция отправляет сообщение о статусе домашней работы в чат."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.info(f'Бот успешно отправил сообщение "{message}"')
    except telegram.TelegramError as error:
        logging.error(f'Сбой при отправке сообщения, {error}')


def get_api_answer(current_timestamp):
    """Функция делает запрос к API и возвращает ответ API."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        raise requests.exceptions.ConnectionError('Ошибка соединения')
    if response.status_code != HTTPStatus.OK:
        raise exceptions.APIPracticumNotAvaliable(
            f'API {ENDPOINT} не доступен, код: {response.status_code}'
        )
    else:
        try:
            return response.json()
        except Exception:
            raise json.decoder.JSONDecodeError(
                'Запрос не удалось преобразовать'
            )


def check_response(response):
    """Функция проверяет ответ API на корректность.
    Функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Тип ответа API не словарь')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Ключ "homeworks" не список')
    return homeworks


def parse_status(homework):
    """Функция извлекает статус конкретной домашней работы.
    Возвращает строку-вердикт из словаря HOMEWORK_STATUSES.
    """
    if not isinstance(homework, dict):
        raise TypeError('"Homework" не словарь')
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError(f'Ключ {homework_name} не найден в {homework}')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise KeyError(
            f'{homework_status} не найден в {HOMEWORK_STATUSES}'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверят доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    current_timestamp = 0
    bot = Bot(token=TELEGRAM_TOKEN)
    previous_message = ''
    if not check_tokens():
        logging.critical(
            msg='Один или несколько токенов отсутствуют', exc_info=True
        )
        sys.exit
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                message = 'Нет новых домашних работ'
                logging.debug(msg=message, exc_info=True)
            else:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
                previous_message = ''
        except Exception as error:
            message = f'{type(error)}: {error}'
            logging.error(message)
            if previous_message != message:
                send_message(bot, message)
                previous_message = message
        current_timestamp = response.get('current_date')
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(lineno)d - %(message)s'
    )
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    main()
