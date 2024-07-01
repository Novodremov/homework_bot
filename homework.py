import logging
import os
import requests
import sys
import time
from dotenv import load_dotenv
from http import HTTPStatus
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


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
logger.addHandler(handler)


def check_tokens():
    """Функция проверки наличия необходимых данных в окружении."""
    if not all((PRACTICUM_TOKEN,
                TELEGRAM_TOKEN,
                TELEGRAM_CHAT_ID)):
        raise exceptions.MissingCorrectTokens(
            'Некорректно определены переменные окружения'
        )


def send_message(bot, message):
    """Функция отправки сообщения пользователю."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise Exception(
            f'Не удалось отправить сообщение пользователю: {error}')
    logger.debug('''Пользователю отправлено сообщение об изменении'''
                 ''' статуса домашней работы''')


''' Этот комментарий уберу на следующей итерации.
Пытался реализовать функцию get_api_answer с разделением случаев ошибки
во время выполенения requests.get() запроса и возврата статуса ответа,
отличного от 200. В таком виде не проходятся тесты, причину так и не понял:

def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params={'from_date': timestamp}
                                         )
    except requests.RequestException:
        raise requests.RequestException('Ошибка во время запроса к API')
    status_code = homework_statuses.status_code
    if status_code == HTTPStatus.OK:
        return homework_statuses.json()
    raise Exception(
        f'Эндпоинт {ENDPOINT} недоступен. Код ответа API: {status_code}')
'''


# Тесты прошла следующая реализация:
def get_api_answer(timestamp):
    """Функция запроса к эндпоинту API-сервиса."""
    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params={'from_date': timestamp}
                                         )
        status_code = homework_statuses.status_code
        if status_code == HTTPStatus.OK:
            return homework_statuses.json()
        raise Exception('Статус ответа отличен от 200')
    except Exception as error:
        logger.error(f'Не удалось получить корректный ответ от API: {error}')
        raise Exception('Статус ответа отличен от 200')


def check_response(response):
    """Функция проверки корректности ответ API-сервиса."""
    if not isinstance(response, dict):

        raise TypeError('В качестве ответа API должен быть получен словарь')
    if 'homeworks' not in response:
        logger.error('В ответе API отсутствует ключ "homeworks"')
        raise KeyError('В ответе API отсутствует ключ "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Значением ключа "homeworks" должен быть список')
    return response['homeworks']


def parse_status(homework):
    """Функция проверки изменения статуса домашней работы."""
    if homework:
        if 'homework_name' in homework:
            homework_name = homework['homework_name']
        else:
            raise KeyError('В ответе API домашки нет ключа "homework_name"')
        if 'status' in homework and homework['status'] in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS[homework['status']]
        else:
            raise KeyError(
                'Статус домашней работы недокументирован/отсутствует')
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    logger.debug('Статус домашней работы не изменился')


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except exceptions.MissingCorrectTokens as error:
        logger.critical(error)
        sys.exit(error)

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            homework_statuses = get_api_answer(timestamp)
            print(homework_statuses)
            homeworks = check_response(homework_statuses)
            homework = homeworks[0] if homeworks else None
            message = parse_status(homework)
            if message:
                send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            # Пытаемся отправить сообщение об ошибке пользователю.
            try:
                send_message(bot, message)
            except Exception as error:
                message = f'Сбой при отправке сообщения об ошибке: {error}'
                logger.error(message)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
