from asyncio import sleep
from functools import partial

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.markdown import hbold, markdown_decoration,html_decoration

from filters import IsEnableGroup, IsWebAppData, IsNewMember
from verification import verify_recaptcha, verify_turnstile, verification, user_states, STATE_PASS


async def command_start_handler(message: Message, command: CommandObject, webapp_url: str):
    """
    处理用户与 Bot 开始对话命令事件
    """
    if command.args is None or command.args != 'verify':
        return
    user_id = message.from_user.id
    if user_id not in user_states:
        return await message.answer(f"你没有待通过的入群验证")

    webapp = WebAppInfo(url=webapp_url)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="点击验证", web_app=webapp)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    msg = await message.answer("请点击下方按钮进行验证", reply_markup=keyboard)
    user_states[user_id].private_tip_msg = msg


async def web_callback_handler(message: Message, token: str, reset_permissions: bool, proxy: str | None,
                               validator: callable):
    """
       处理用户在 WebApp 完成验证得到 reCaptcha Response 事件
    """
    user_id = message.from_user.id
    if user_id not in user_states:
        return

    if not validator(message.web_app_data.data, token, proxy):
        return await message.answer("验证失败")

    chat_id = user_states[user_id].chat_id
    user_states[user_id].state = STATE_PASS
    group_tip_id = user_states[user_id].group_tip_id

    if reset_permissions:
        chat = await message.bot.get_chat(chat_id)
        await message.bot.restrict_chat_member(chat_id, user_id, chat.permissions)
    await message.answer("验证通过", reply_markup=ReplyKeyboardRemove())

    msg = await message.bot.send_message(chat_id, f"{hbold(message.from_user.full_name)} 通过了验证")
    await sleep(5)
    await message.bot.delete_message(chat_id, group_tip_id)
    await message.bot.delete_message(chat_id, msg.message_id)


async def new_member_handler(event: ChatMemberUpdated, bot_name: str, test_time: int, reset_permissions: bool):
    """
    处理新进群事件
    """
    print(event.chat.username)
    keyboard = [[InlineKeyboardButton(text="点击验证", url=f"https://t.me/{bot_name}?start=verify")]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    user_name = event.from_user.full_name
    msg = await event.answer(
        text=f"{event.from_user.mention_html(name=user_name[0] + '███' + user_name[-1])if len(user_name)>=3 else user_name} 加入了, 请在 {test_time} 秒内私聊通过验证 !",
        reply_markup=markup
    )

    await verification(
        chat=msg.chat,
        message_id=msg.message_id,
        user=event.new_chat_member.user,
        bot=event.bot,
        shutup_before_verification=reset_permissions,
        test_time=test_time
    )


async def new_member_tip_handler(message: Message):
    await message.delete()


def get_handlers_router(bot_name: str,
                        webapp_url: str,
                        recaptcha_token: str | None,
                        turnstile_token: str | None,
                        reset_permissions: bool,
                        test_time: int,
                        proxy: str | None,
                        groups: str | list[str] | None):
    router = Router()
    router.message(CommandStart())(
        partial(command_start_handler, webapp_url=webapp_url))
    if recaptcha_token:
        router.message(IsWebAppData())(
            partial(web_callback_handler,
                    token=recaptcha_token,
                    reset_permissions=reset_permissions,
                    proxy=proxy,
                    validator=verify_recaptcha))
    elif turnstile_token:
        router.message(IsWebAppData())(
            partial(web_callback_handler,
                    token=turnstile_token,
                    reset_permissions=reset_permissions,
                    proxy=proxy,
                    validator=verify_turnstile))
    router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), IsEnableGroup(groups))(
        partial(new_member_handler,
                bot_name=bot_name,
                test_time=test_time,
                reset_permissions=reset_permissions))

    router.message(IsNewMember())(new_member_tip_handler)
    return router
