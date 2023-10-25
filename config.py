import argparse
import logging
from os import getenv
from typing import Optional


class Config:
    # 使用轮询或者 webhook
    web_hook: bool = False

    def __init__(self,
                 telegram_token: str,
                 webapp_url: str,
                 recaptcha_token: Optional[str] = None,
                 turnstile_token: Optional[str] = None,
                 ban: bool = False,
                 ban_time: Optional[int] = None,
                 shutup: bool = False,
                 test_time: int = 60,
                 proxy: Optional[str] = None,
                 groups: Optional[list[str]] = None,
                 server_host: Optional[str] = None,  # for webhook
                 server_port: Optional[int] = None,  # for webhook
                 webhook_path: Optional[str] = None,  # for webhook
                 ):
        """

        :param telegram_token: Bot 的 token 通过 https://t.me/BotFather 获取
        :param webapp_url: 用于客户端进行验证的网页地址（必须 https 协议通信），完成前端验证时将 response 通过 tg 的 url 返回给客户端，见 https://core.telegram.org/bots/webapps#initializing-mini-apps
        :param recaptcha_token: 与 ``turnstile_token`` 二选一，google recaptcha 的 secret key
        :param turnstile_token: cloudflare turnstile 的 secret key
        :param shutup: 是否在用户通过验证前禁言
        :param test_time: 用户验证的最大容忍时间
        :param proxy: 代理服务器，同时会为 tg 通信与 response 验证服务器通信都启用
        :param groups: 启用验证的群组列表
        :param server_host: 绑定到 localhost 则只允许内部访问，一般绑定到 0.0.0.0
        :param server_port: 任何有效的端口
        :param webhook_path: path to webhook route, on which Telegram will send requests
        """
        self.telegram_token = telegram_token

        if ((recaptcha_token is not None and turnstile_token is not None) or
                (recaptcha_token is None and turnstile_token is None)):
            raise ValueError("recaptcha_token 和 turnstile_token 必须二选一填入")

        self.recaptcha_token = recaptcha_token
        self.turnstile_token = turnstile_token
        self.ban = ban
        self.ban_time = ban_time
        if ban_time is not None and ban_time < 30:
            logging.warning("封禁时间必须 > 30 秒且 < 366 天 否则会视为永久封禁")

        self.webapp_url = webapp_url
        self.shutup = shutup
        self.test_time = test_time
        self.proxy = proxy
        self.groups = groups

        if server_port is not None and server_host is not None:
            self.web_hook = True
        self.server_port = server_port
        self.server_host = server_host
        self.webhook_path = webhook_path

    @staticmethod
    def from_arg():
        parser = argparse.ArgumentParser(description='Telegram Verification Bot with reCaptcha')
        parser.add_argument('--telegram-token', type=str, help='telegram bot token', required=True)

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--recaptcha-token', type=str, help='google reCaptcha token')
        group.add_argument('--turnstile-token', type=str, help='cloudflare turnstile token')

        parser.add_argument('--ban', type=bool, default=False, help='验证超时后屏蔽')
        parser.add_argument('--ban-time', type=int, help='验证超时后屏蔽的时间')

        parser.add_argument('--webapp-url', type=str, help='path to web app page', required=True)

        parser.add_argument('--shutup', type=bool, help='disable speech until the user is authenticated',
                            default=True)
        parser.add_argument('--test-time', type=int, help='validation time limit', default=60)
        parser.add_argument('--proxy', type=str, help='proxy server', default=None)
        parser.add_argument('--groups', type=str, nargs='+', help='enable bot group list', default=None)

        parser.add_argument('--server-host',
                            type=str,
                            help='bind localhost only to prevent any external access', )
        parser.add_argument('--server-port',
                            type=int,
                            help='port for incoming request from reverse proxy. should be any available port',
                            default=getenv("PORT"))
        parser.add_argument('--webhook-path', type=str,
                            help='path to webhook route, on which Telegram will send requests', default="/webhook")
        return Config(**vars(parser.parse_args()))
