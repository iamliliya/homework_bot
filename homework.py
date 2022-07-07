import logging
import os
import requests
import time


from dotenv import load_dotenv
from http import HTTPStatus
from telegram import Bot, TelegramError

from exceptions import (
    APIPracticumNotAvaliable,
    HomeworkListEmpty,
    TokenMissing)

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
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.info(f'Бот успешно отправил сообщение "{message}"')


def get_api_answer(current_timestamp):
    """Функция делает запрос к API и возвращает ответ API."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        raise APIPracticumNotAvaliable(
            f'API {ENDPOINT} не доступен, код ответа: {response.status_code}'
        )


def check_response(response):
    """Функция проверяет ответ API на корректность.
    Функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Тип ответа API не словарь')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Тип "homeworks" не список')
    else:
        return response.get('homeworks')


def parse_status(homework):
    """Функция извлекает статус конкретной домашней работы.
    Возвращает строку-вердикт из словаря HOMEWORK_STATUSES.
    """
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise KeyError(f'Ключ {homework_name} не найден в {homework}')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict:
        raise KeyError(
            f'{homework_status} не найден в {HOMEWORK_STATUSES}'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Функция проверят доступность переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    previous_message = ''
    while check_tokens() is True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                raise HomeworkListEmpty('В списке нет домашних работ')
            else:
                if len(homeworks) > 0:
                    homework = homeworks[0]
                    message = parse_status(homework)
        except APIPracticumNotAvaliable as error:
            logging.error(error, exc_info=True)
        except TypeError as error:
            logging.error(error, exc_info=True)
            message = 'Тип данных в ответе API не соответствует ожидаемому'
        except HomeworkListEmpty as error:
            logging.error(error, exc_info=True)
            message = 'В списке нет домашних работ за указанный период'
        except KeyError as error:
            logging.error(error, exc_info=True)
            message = 'Ожидаемые ключи в ответе API отсутствуют'
        except TelegramError as error:
            message = f'Сбой в работе программы {error}'
            logging.error(message, exc_info=True)
        if previous_message != message:
            send_message(bot, message)
            previous_message = message
        else:
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
    else:
        logging.critical(exc_info=True)
        raise TokenMissing(
            'Одна или несколько переменных окружения не найдены',
        )


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(lineno)d - %(message)s'
    )
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    main()
