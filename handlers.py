from asyncio import sleep
from functools import partial

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.markdown import hbold, markdown_decoration, html_decoration

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
    user_states[user_id].private_chat_id = message.chat.id
    webapp = WebAppInfo(url=webapp_url)
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="点击验证", web_app=webapp)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    msg = await message.answer("请点击下方按钮进行验证（如果未找到按钮请在底部选项内查找）", reply_markup=keyboard)
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

    await message.bot.send_message(chat_id, f"{hbold(message.from_user.full_name)} 通过了验证")
    await sleep(5)
    await message.bot.delete_message(chat_id, group_tip_id)


async def new_member_handler(event: ChatMemberUpdated, test_time: int, reset_permissions: bool, ban: bool,
                             ban_time: int | None):
    """
    处理新进群事件
    """
    keyboard = [
        [InlineKeyboardButton(text="点击验证", url=f"https://t.me/{(await event.bot.get_me()).username}?start=verify")]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    user_name = event.from_user.full_name
    msg = await event.answer(
        text=f"{event.from_user.mention_html(name=user_name[0] + '███' + user_name[-1]) if len(user_name) >= 3 else user_name} 加入了, 请在 {test_time} 秒内私聊通过验证 !",
        reply_markup=markup
    )

    await verification(
        chat=msg.chat,
        group_tip_message=msg,
        user=event.new_chat_member.user,
        bot=event.bot,
        shutup_before_verification=reset_permissions,
        test_time=test_time,
        ban=ban,
        ban_time=ban_time
    )


async def new_member_tip_handler(message: Message):
    await message.delete()


def get_handlers_router(webapp_url: str,
                        secret_key: str,
                        validator: callable,
                        reset_permissions: bool,
                        test_time: int,
                        proxy: str | None,
                        groups: str | list[str] | None,
                        ban: bool,
                        ban_time: int | None):
    router = Router()
    router.message(CommandStart())(
        partial(command_start_handler, webapp_url=webapp_url))
    router.message(IsWebAppData())(
        partial(web_callback_handler,
                token=secret_key,
                reset_permissions=reset_permissions,
                proxy=proxy,
                validator=validator,))
    router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), IsEnableGroup(groups))(
        partial(new_member_handler,
                test_time=test_time,
                reset_permissions=reset_permissions,
                ban=ban,
                ban_time=ban_time
                ))

    router.message(IsNewMember(), IsEnableGroup(groups))(new_member_tip_handler)
    return router
