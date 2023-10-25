import logging
import sys

from aiogram import Dispatcher, Bot
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from config import Config
from handlers import get_handlers_router
from verification import verify_recaptcha, verify_turnstile


def run(config: Config):
    dp = Dispatcher()

    bot = Bot(
        token=config.telegram_token,
        session=AiohttpSession({config.proxy}) if config.proxy else None,
        parse_mode=ParseMode.HTML
    )

    router = get_handlers_router(
        config.webapp_url,
        config.recaptcha_token if config.recaptcha_token is not None else config.turnstile_token,
        verify_recaptcha if config.recaptcha_token is not None else verify_turnstile,
        config.shutup,
        config.test_time,
        config.proxy,
        config.groups,
        config.ban,
        config.ban_time)

    dp.include_router(router)

    if not config.web_hook:
        import asyncio
        logging.log(logging.INFO, "正在以轮询模式启动 Bot")
        asyncio.run(dp.start_polling(bot))
        return

    from aiohttp import web
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
    app = web.Application()
    logging.log(logging.INFO, "正在以 Web Hook 模式启动 Bot")
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=config.webhook_path)

    setup_application(app, dp, bot=bot)
    web.run_app(app, host=config.server_host, port=config.server_port)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.NOTSET)
    run(Config.from_arg())
