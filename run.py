# user state code
import asyncio
import logging
import sys

from aiogram import Dispatcher, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from handlers import get_handlers_router

import argparse


def run(
        telegram_token: str,
        recaptcha_token: str,
        webapp_url: str,
        test_time: int = 60,
        proxy: str | None = None,
        shutup: bool = True
):
    """
    启动 bot
    :param telegram_token: Telegram Bot Token
    :param recaptcha_token: Google reCAPTCHA 服务端 Token
    :param webapp_url: reCAPTCHA 的 webapp URL
    :param test_time: 验证的最大时间限制
    :param proxy: 代理服务器
    :param shutup: 是否在通过验证之前禁言用户，如果开启，由于需要重新设置权限，会导致被管理员手动禁言的用户退出重进后也恢复群组的默认权限
    :return:
    """
    dp = Dispatcher()

    bot = Bot(
        token=telegram_token,
        session=AiohttpSession({proxy}) if proxy else None,
        parse_mode=ParseMode.HTML
    )

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    loop = asyncio.get_event_loop()
    me = loop.run_until_complete(bot.get_me())

    router = get_handlers_router(
        me.username,
        webapp_url,
        recaptcha_token,
        shutup,
        test_time,
        proxy)
    dp.include_router(router)

    loop.run_until_complete(dp.start_polling(bot))
    loop.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Telegram Verification Bot with reCaptcha')
    parser.add_argument('--telegram-token', type=str, help='Telegram Bot Token', required=True)
    parser.add_argument('--recaptcha-token', type=str, help='reCaptcha Bot Token', required=True)
    parser.add_argument('--webapp-url', type=str, help='reCaptcha Web App URL', required=True)
    parser.add_argument('--shutup', type=bool, help='disable speech until the user is authenticated', default=False)
    parser.add_argument('--test-time', type=bool, help='validation time limit', default=100)
    parser.add_argument('--proxy', type=str, help='proxy server', default=None)
    args = parser.parse_args()

    run(**vars(args))
