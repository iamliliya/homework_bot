import logging
import os
import requests
import time


from dotenv import load_dotenv
from http import HTTPStatus
from telegram import Bot, TelegramError

from exceptions import EmptyList, TokenMissing

load_dotenv()

# TODO
# [x] отсутствие обязательных переменных окружения во время запуска бота (уровень CRITICAL).
# [х] удачная отправка любого сообщения в Telegram (уровень INFO);
# [x] сбой при отправке сообщения в Telegram (уровень ERROR);
# [?] недоступность эндпоинта https://practicum.yandex.ru/api/user_api/homework_statuses/ (уровень ERROR);
# [?] любые другие сбои при запросе к эндпоинту (уровень ERROR);
# [x] отсутствие ожидаемых ключей в ответе API (уровень ERROR);
# [x] недокументированный статус домашней работы, обнаруженный в ответе API (уровень ERROR);
# [] отсутствие в ответе новых статусов (уровень DEBUG).]


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


def send_message(bot, message):
    """Функция отправляет сообщение о статусе домашней работы в чат."""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    logging.info(f'Бот успешно отправил сообщение "{message}"')


def get_api_answer(current_timestamp):
    """Функция делает запрос к API и возвращает ответ API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        raise ConnectionError(
            f'API {ENDPOINT} не доступен, код ответа: {response.status_code}'
        )


def check_response(response):
    """Функция проверяет ответ API на корректность.
    Функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Тип ответа API не словарь')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError('Тип "Homeworks" не список')
    if not response.get('homeworks') or response.get('homeworks') is None:
        raise KeyError('Ключ "homeworks" отсутствуeт в ответе API')
    else:
        return response.get('homeworks')


def parse_status(homework):
    """Функция извлекает статус конкретной домашней работы.
    Возвращает строку-вердикт из словаря HOMEWORK_STATUSES.
    """
    homework_name = homework.get('homework_name')
    if not homework_name or homework_name is None:
        raise KeyError(f'Ключ {homework_name} не найден в {homework}')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if not verdict or verdict is None:
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
    current_timestamp = int(time.time()) - 30 * 24 * 3600
    # current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    while check_tokens() is True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = int(time.time()) - 30 * 24 * 3600
        except ConnectionError as error:
            logging.error(error, exc_info=True)
        except TypeError as error:
            logging.error(error, exc_info=True)
            message = 'Тип данных в ответе API не соответствует ожидаемому'
            # send_message(bot, message)
        except EmptyList as error:
            logging.error(error, exc_info=True)
            message = 'В списке нет домашних работ за указанный период'
            # send_message(bot, message)
        except IndexError as error:
            logging.error(error, exc_info=True)
            message = 'Нет работы с таким индексом'
        except KeyError as error:
            logging.error(error, exc_info=True)
            message = 'Запрашиваемый ключ не найден'
            # send_message(bot, message)
        except TelegramError as error:
            message = f'Сбой в работе программы {error}'
            logging.error(message, exc_info=True)
        previous_message = message
        if message == previous_message:
            logging.debug(msg='Нет обновлений', exc_info=True)
            time.sleep(RETRY_TIME)
        else:
            send_message(bot, message)
    else:
        logging.critical(exc_info=True)
        raise TokenMissing(
            'Одна или несколько переменных окружения не найдены',
            exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(lineno)d - %(message)s'
    )
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    main()
