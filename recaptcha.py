from asyncio import sleep

import requests
from aiogram import Bot
from aiogram.types import ChatPermissions, Chat, User, ChatMember

STATE_PASS = 'pass'
STATE_NOT_PERFORMED = 'not performed'
STATE_FAIL = 'fail'

users_state: dict[int, list] = {}  # [user_id, [group_id, state]]


async def verification(chat: Chat,
                       message_id: int,
                       user: User,
                       bot: Bot,
                       shutup_before_verification: bool,
                       test_time: int):
    """
     缓存数据，发送提示信息，等待私聊验证，超市则踢出用户
     :param chat_id: 群组 id
     :param message_id: 提示信息 id，验证后删除
     :param user_id: 被验证用户 id
     :param bot: Bot
     :param shutup_before_verification: 在通过验证前是否禁言
     :param test_time: 超过这个时间将被封禁
     :return:
     """
    users_state[user.id] = [chat.id, STATE_NOT_PERFORMED, message_id]  # 缓存正在用户的信息

    if shutup_before_verification:
        await bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(),
        )

    await sleep(test_time)

    if users_state[user.id][1] != STATE_PASS:
        await bot.ban_chat_member(chat.id, user.id)
        await bot.delete_message(chat.id, message_id)
        msg = await bot.send_message(chat.id, f"{user.full_name} 验证超时，已被踢出")
        await sleep(10)
        await bot.delete_message(chat.id, msg.message_id)
    users_state.pop(user.id)


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

    return result['success']
