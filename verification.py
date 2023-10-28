import logging
from asyncio import sleep
from datetime import datetime, timedelta
from typing import Optional

import requests
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import ChatPermissions, Chat, User, Message

STATE_PASS = 'pass'
STATE_NOT_PERFORMED = 'not performed'


# STATE_FAIL = 'fail'


class UserState:
    def __init__(self, chat_id: int, group_tim_msg: Message, state: str = STATE_NOT_PERFORMED,
                 private_tip_msg: Optional[Message] = None):
        self.chat_id = chat_id
        self.group_tip_msg = group_tim_msg
        self.state = state
        self.private_tip_msg = private_tip_msg  # 私聊中的提示信息，完成后删除


user_states: dict[int, UserState] = {}


async def verification(chat: Chat,
                       group_tip_message: Message,
                       user: User,
                       bot: Bot,
                       shutup_before_verification: bool,
                       test_time: int,
                       ban: bool,
                       ban_time: int | None):
    """
     缓存数据，发送提示信息，等待私聊验证，超市则踢出用户
     :param chat: 群组
     :param group_tip_message: 提示信息，验证后删除
     :param user: 被验证用户
     :param bot: Bot
     :param shutup_before_verification: 在通过验证前是否禁言
     :param test_time: 超过这个时间将被封禁
     :param ban: 验证失败后是否封禁
     :param ban_time: 封禁时间，空为永久
     """
    user_states[user.id] = UserState(chat.id, group_tip_message)  # 缓存正在用户的信息

    if shutup_before_verification:
        await bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(),
        )

    await sleep(test_time)

    if user_states[user.id].state == STATE_PASS:
        """
        通过验证后消息的删除，与通过的提醒在 handlers.web_callback_handler 中处理了
        """
        user_states.pop(user.id)
        return

    msg = await bot.send_message(chat.id, f"{user.full_name[0] + '███' + user.full_name[-1]} 验证超时，已被踢出")
    await bot.ban_chat_member(
        chat_id=chat.id,
        user_id=user.id,
        until_date=datetime.now() + timedelta(seconds=ban_time) if ban_time is not None else None)

    if not ban:
        await bot.unban_chat_member(chat.id, user.id)
    elif ban_time is not None:
        try:
            await bot.send_message(user.id, f"未通过验证，已被踢出，请在 {test_time} 秒后重试")
        except TelegramForbiddenError:
            logging.info(f"{user.full_name} 未私聊，无法发送消息")
    else:
        try:
            await bot.send_message(user.id, f"未通过验证，已被永久封禁，请联系管理员")
        except TelegramForbiddenError:
            logging.info(f"{user.full_name} 未私聊，无法发送消息")
    user_states.pop(user.id)
    await sleep(10)

    await bot.delete_message(chat.id, msg.message_id)
    await bot.delete_message(chat.id, group_tip_message.message_id)


# 验证客户端传回来的 recaptcha response
def verify_recaptcha(user_data: str, token: str, proxy: str = None):
    data = {
        "secret": token,
        "response": user_data
    }
    result = requests.post(
        url="https://www.google.com/recaptcha/api/siteverify",
        data=data,
        proxies={"https": proxy} if proxy else None
    ).json()
    if "score" in result:  # for v3
        return result['success'] and result['score'] > 0.5
    return result['success']  # for v2


def verify_turnstile(user_data: str, token: str, proxy: str = None):
    data = {
        "secret": token,
        "response": user_data
    }
    result = requests.post(
        url="https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=data,
        proxies={"https": proxy} if proxy else None
    ).json()
    return result['success']
