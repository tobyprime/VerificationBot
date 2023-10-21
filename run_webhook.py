import argparse
import asyncio
import logging
import sys
import urllib.parse

from aiogram import Dispatcher, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from handlers import get_handlers_router


def run(
        telegram_token: str,
        server_url: str,
        server_host: str,
        server_port: int,
        webapp_path: str,
        webhook_path: str,
        recaptcha_token: str | None = None,
        turnstile_token: str | None = None,
        test_time: int = 60,
        proxy: str | None = None,
        shutup: bool = True,
        groups: list[str] | str | None = None
):
    dp = Dispatcher()

    bot = Bot(
        token=telegram_token,
        session=AiohttpSession({proxy}) if proxy else None,
        parse_mode=ParseMode.HTML
    )

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    router = get_handlers_router(asyncio.run(bot.get_me()).username,
                                 urllib.parse.urljoin(server_url, webapp_path),
                                 recaptcha_token,
                                 turnstile_token,
                                 shutup,
                                 test_time,
                                 proxy,
                                 groups)
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
    webhook_requests_handler.register(app, path=webhook_path)

    # Mount dispatcher startup and shutdown hooks to aiohttp application
    setup_application(app, dp, bot=bot)

    # And finally start webserver
    web.run_app(app, host=server_host, port=server_port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Telegram Verification Bot with reCaptcha')
    parser.add_argument('--telegram-token', type=str, help='Telegram Bot Token', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--recaptcha-token', type=str, help='google reCaptcha token')
    group.add_argument('--turnstile-token', type=str, help='cloudflare turnstile token')
    parser.add_argument('--server-url',
                        type=str,
                        help='base URL for webhook will be used to generate webhook URL for Telegram',
                        required=True)
    parser.add_argument('--server-host',
                        type=str,
                        help='bind localhost only to prevent any external access',
                        default="127.0.0.1")
    parser.add_argument('--server-port',
                        type=int,
                        help='Port for incoming request from reverse proxy. Should be any available port',
                        default=8080)
    parser.add_argument('--webhook-path', type=str, help='path to webhook route, on which Telegram will send requests',
                        default='/webhook')
    parser.add_argument('--webapp-path', type=str, help='path to web app page', required=True)

    parser.add_argument('--shutup', type=bool, help='disable speech until the user is authenticated', default=False)
    parser.add_argument('--test-time', type=bool, help='validation time limit', default=False)
    parser.add_argument('--proxy', type=str, help='proxy server', default=None)
    parser.add_argument('--groups', type=str, nargs='+', help='enable bot group list', default=None)

    args = parser.parse_args()

    run(**vars(args))
