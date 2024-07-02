import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

import exceptions


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


def check_tokens():
    """Функция проверки наличия необходимых данных в окружении."""
    if not all((PRACTICUM_TOKEN,
                TELEGRAM_TOKEN,
                TELEGRAM_CHAT_ID)):
        token_names = ['PRACTICUM_TOKEN',
                       'TELEGRAM_TOKEN',
                       'TELEGRAM_CHAT_ID']
        missing_tokens = ', '.join(
            [token for token in token_names if not globals()[token]])
        error = f'Не определены переменные окружения: {missing_tokens}'
        logger.critical(error)
        sys.exit(error)


def send_message(bot, message):
    """Функция отправки сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise exceptions.SendMessageError(
            f'Не удалось отправить сообщение пользователю: {error}')
    logger.debug('Пользователю отправлено сообщение об изменении '
                 'статуса домашней работы')


def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API-сервиса."""
    request_params = {'url': ENDPOINT,
                      'headers': HEADERS,
                      'params': {'from_date': timestamp}}
    try:
        responce = requests.get(**request_params)
    except requests.RequestException as error:
        raise ConnectionError(f'Ошибка во время запроса к API: {error}, '
                              f'параметры запроса: {request_params}')
    status_code = responce.status_code
    if status_code == HTTPStatus.OK:
        return responce.json()
    raise ConnectionError(
        f'Эндпоинт {ENDPOINT} недоступен. Код ответа API: {status_code}')


def check_response(response):
    """Функция проверки корректности ответ API-сервиса."""
    if not isinstance(response, dict):
        raise TypeError(
            f'В качестве ответа API вместо словаря получен {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError(f'Значением ключа "homeworks" является не список, '
                        f'а {type(response['homeworks'])}')
    return response['homeworks']


def parse_status(homework):
    """Функция проверки изменения статуса домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API домашки нет ключа "homework_name"')
    homework_name = homework['homework_name']
    if ('status' not in homework
            and homework['status'] in HOMEWORK_VERDICTS):
        raise KeyError('Статус домашней работы отсутствует')
    if homework['status'] not in HOMEWORK_VERDICTS:
        raise KeyError('Статус домашней работы недокументирован')
    verdict = HOMEWORK_VERDICTS[homework['status']]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    last_error_message = ''

    while True:
        try:
            homework_statuses = get_api_answer(timestamp)
            homeworks = check_response(homework_statuses)
            homework = homeworks[0] if homeworks else None
            message = parse_status(homework) if homework else None
            if not message:
                logger.debug('Статус домашней работы не изменился')
            elif message != last_message:
                send_message(bot, message)
            timestamp = homework_statuses.get('current_date', int(time.time()))
        except exceptions.SendMessageError as error:
            logger.error(error)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != last_error_message:
                try:
                    send_message(bot, message)
                    last_error_message = message
                except exceptions.SendMessageError as error:
                    message = f'Сбой при отправке сообщения об ошибке: {error}'
                    logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
    )
    main()
