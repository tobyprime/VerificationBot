import argparse
import asyncio
import logging
import sys

from aiogram import Dispatcher, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from handlers import get_handlers_router

# Webserver settings
# bind localhost only to prevent any external access
WEB_SERVER_HOST = "127.0.0.1"
# Port for incoming request from reverse proxy. Should be any available port
WEB_SERVER_PORT = 8080

# Path to webhook route, on which Telegram will send requests
WEBHOOK_PATH = "/webhook"
# Secret key to validate requests from Telegram (optional)
# WEBHOOK_SECRET = "my-secret"
# Base URL for webhook will be used to generate webhook URL for Telegram,
# in this example it is used public DNS with HTTPS support
BASE_WEBHOOK_URL = "https://TobyLinas.pythonanywhere.com/"


def run(
        telegram_token: str,
        recaptcha_token: str,
        webapp_url: str,
        test_time: int = 60,
        proxy: str | None = None,
        shutup_before_verification: bool = True
):
    dp = Dispatcher()

    bot = Bot(
        token=telegram_token,
        session=AiohttpSession({proxy}) if proxy else None,
        parse_mode=ParseMode.HTML
    )

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    router = get_handlers_router(asyncio.run(bot.get_me()).username,
                                 webapp_url,
                                 recaptcha_token,
                                 shutup_before_verification,
                                 test_time,
                                 proxy)
    dp.include_router(router)
    app = web.Application()

    # Create an instance of request handler,
    # aiogram has few implementations for different cases of usage
    # In this example we use SimpleRequestHandler which is designed to handle simple cases
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        # secret_token=WEBHOOK_SECRET,
    )
    # Register webhook handler on application
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Mount dispatcher startup and shutdown hooks to aiohttp application
    setup_application(app, dp, bot=bot)

    # And finally start webserver
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Telegram Verification Bot with reCaptcha')
    parser.add_argument('--telegram-token', type=str, help='Telegram Bot Token', required=True)
    parser.add_argument('--recaptcha-token', type=str, help='reCaptcha Bot Token', required=True)
    parser.add_argument('--webapp-url', type=str, help='reCaptcha Web App URL', required=True)
    parser.add_argument('--shutup', type=bool, help='disable speech until the user is authenticated', default=False)
    parser.add_argument('--test-time', type=bool, help='validation time limit', default=False)
    parser.add_argument('--proxy', type=str, help='proxy server', default=None)
    args = parser.parse_args()

    run(
        telegram_token=args.telegram_token,
        recaptcha_token=args.recaptcha_token,
        webapp_url=args.webapp_url,
        test_time=args.test_time,
        proxy=args.proxy,
        shutup_before_verification=args.shutup
    )
