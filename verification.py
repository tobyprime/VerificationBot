from asyncio import sleep
from datetime import datetime, timedelta

import requests
from aiogram import Bot
from aiogram.types import ChatPermissions, Chat, User, Message

STATE_PASS = 'pass'
STATE_NOT_PERFORMED = 'not performed'


# STATE_FAIL = 'fail'


class UserState:
    def __init__(self, chat_id: int, group_tip_id: int, state=STATE_NOT_PERFORMED, private_tip_msg=None,
                 private_chat_id=None):
        self.chat_id = chat_id
        self.group_tip_id = group_tip_id
        self.private_tip_msg = private_tip_msg
        self.state = state
        self.private_chat_id = private_chat_id


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
     :param ban:
     :param ban_time:
     :param chat: 群组
     :param group_tip_message: 提示信息，验证后删除
     :param user: 被验证用户
     :param bot: Bot
     :param shutup_before_verification: 在通过验证前是否禁言
     :param test_time: 超过这个时间将被封禁
     :return:
     """
    user_states[user.id] = UserState(chat.id, group_tip_message.message_id)  # 缓存正在用户的信息

    if shutup_before_verification:
        await bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(),
        )

    await sleep(test_time)

    if user_states[user.id].state != STATE_PASS:
        msg = await bot.send_message(chat.id, f"{user.full_name[0] + '███' + user.full_name[-1]} 验证超时，已被踢出")
        if ban:
            if ban_time is None:
                await bot.ban_chat_member(chat.id, user.id)
            else:
                await bot.ban_chat_member(chat.id, user.id, until_date=datetime.now() + timedelta(seconds=ban_time))
                try:
                    await bot.send_message(user.id, f"未通过验证，已被踢出，请在 {test_time} 秒后重试")
                except:
                    pass
        else:
            await bot.ban_chat_member(chat.id, user.id)
            await bot.unban_chat_member(chat.id, user.id)

        await sleep(10)

        await bot.delete_message(chat.id, msg.message_id)
        await bot.delete_message(chat.id, group_tip_message.message_id)
    user_states.pop(user.id)


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
