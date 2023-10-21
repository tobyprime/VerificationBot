import argparse
import asyncio
import logging
import sys

from aiogram import Dispatcher, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from handlers import get_handlers_router


def run(
        telegram_token: str,
        webapp_url: str,
        test_time: int = 60,
        recaptcha_token: str | None = None,
        turnstile_token: str | None = None,
        proxy: str | None = None,
        shutup: bool = True,
        groups=None,
):
    """
    启动 bot
    :param telegram_token: Telegram Bot Token
    :param webapp_url: reCAPTCHA 的 webapp URL
    :param test_time: 验证的最大时间限制
    :param proxy: 代理服务器
    :param shutup: 是否在通过验证之前禁言用户，如果开启，由于需要重新设置权限，会导致被管理员手动禁言的用户退出重进后也恢复群组的默认权限
    :param groups: 启用 bot 的群组列表
    :param recaptcha_token: Google reCAPTCHA 服务端 Token
    :param turnstile_token: Cloudflare turnstile 服务端 Token, 与recaptcha二选一
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
        turnstile_token,
        shutup,
        test_time,
        proxy,
        groups)
    dp.include_router(router)

    loop.run_until_complete(dp.start_polling(bot))
    loop.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Telegram Verification Bot with reCaptcha')
    parser.add_argument('--telegram-token', type=str, help='telegram bot token', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--recaptcha-token', type=str, help='google reCaptcha token')
    group.add_argument('--turnstile-token', type=str, help='cloudflare turnstile token')
    parser.add_argument('--webapp-url', type=str, help='reCaptcha Web App URL', required=True)
    parser.add_argument('--shutup', type=bool, help='disable speech until the user is authenticated', default=False)
    parser.add_argument('--test-time', type=bool, help='validation time limit', default=100)
    parser.add_argument('--proxy', type=str, help='proxy server', default=None)
    parser.add_argument('--groups', type=str, nargs='+', help='enable bot group list', default=None)
    args = parser.parse_args()

    run(**vars(args))
