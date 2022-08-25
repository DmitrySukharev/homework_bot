import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions as exc
from settings import ENDPOINT, HOMEWORK_STATUSES, RETRY_TIME

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_TG_ID')
# TEAM22_TG_ID = os.getenv('TEAM22_TG_ID')
PRACTICUM_TOKEN = os.getenv('HW_TOKEN')
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в чат, определяемый в переменных окружения."""
    try:
        logger.debug('Отправляем сообщение в Телеграм...')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as err:
        logger.error(f'Не могу отправить сообщение в Телеграм! Ошибка: {err}')
    else:
        logger.info(f'Бот отправил сообщение "{message}"')


def send_message_to_team22(bot, message):
    """Отправка сообщения в чат группы, определяемый в переменных окружения."""
    try:
        logger.debug('Отправляем сообщение в ТГ Группу 22...')
        # bot.send_message(TEAM22_TG_ID, message)
    except telegram.error.TelegramError as err:
        logger.error(f'Не могу отправить сообщение в Группу 22! Ошибка: {err}')
    else:
        logger.info(f'Бот отправил сообщение в ТГ Группу 22"{message}"')


def get_api_answer(current_timestamp):
    """Получение ответа API и проверка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.debug('Запрашиваем Yandex Homework API...')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        error_msg = (f'Эндпоинт {ENDPOINT} недоступен. Ошибка: {error}')
        raise exc.APINotAvailableError(error_msg)
    if response.status_code != HTTPStatus.OK:
        error_msg = (f'Эндпоинт {ENDPOINT} недоступен. '
                     f'Код ответа API: {response.status_code}')
        raise exc.InvalidHTTPResponseError(error_msg)
    try:
        response = response.json()
    except json.JSONDecodeError:
        error_msg = ('JSON Decode Error - невозможно привести ответ API '
                     'к типам данных Python')
        raise exc.CustomJSONDecodeError(error_msg)
    return response


def check_response(response):
    """Проверка ответа API на корректность (наличие ключа 'homeworks')."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        error_msg = f'Отсутствие ожидаемых ключей в ответе API ({error})'
        raise exc.WrongResponseKeysError(error_msg)
    if type(homeworks) != list:
        raise Exception('Тип, отличный от списка, под ключом homeworks')
    return homeworks


def parse_status(homework):
    """Парсинг ответа API и проверка наличия нужных ключей и статусов."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        error_msg = f'Отсутствие ожидаемых ключей в ответе API ({error})'
        raise KeyError(error_msg)
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        error_msg = ('Недокументированный статус домашней работы '
                     f'в ответе API: {error}')
        # raise exc.WrongHomeworkStatusError(error_msg)   # Не проходит pytest
        raise KeyError(error_msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота.

    - периодический опрос API сервиса Практикум.Домашка
    - проверка статуса отправленной на ревью домашней работы
    - отправка уведомлений в Telegram при обновлении статуса
    - логирование работы и отправка сообщений об ошибках в Telegram
    """
    if not check_tokens():
        logger.critical(
            'Отсутствует обязательная переменная окружения!\n'
            'Программа принудительно остановлена.'
        )
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    latest_error_type = None

    send_message(bot, 'Привет, я проснулся!')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
                    # end_message_to_team22(bot, message)
            else:
                logger.debug('No news - good news!')
            current_timestamp = response.get('current_date') or time.time()
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if type(error) != latest_error_type:
                send_message(bot, message)
            latest_error_type = type(error)
            time.sleep(RETRY_TIME)
        else:
            latest_error_type = None


if __name__ == '__main__':
    main()
