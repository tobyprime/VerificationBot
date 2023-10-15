from asyncio import sleep

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold

from filters import IsAdmin, IsWebAppData
from recaptcha import verify_recaptcha, verification, users_state, STATE_PASS


def reg_command_start_handler(router: Router, webapp_url: str):
    @router.message(CommandStart())
    async def handler(message: Message, command: CommandObject):
        """
        处理用户与 Bot 开始对话命令事件
        """
        if command.args is None or command.args != 'verify':
            return
        user_id = message.from_user.id
        if user_id not in users_state:
            await message.answer(f"你没有待通过的入群验证")
            return
        webapp = WebAppInfo(url=webapp_url)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="点我验证", web_app=webapp)]],
            resize_keyboard=True
        )
        await message.answer("请点击下方按钮进行验证", reply_markup=keyboard)


def reg_callback_handler(router: Router, reset_permissions: bool, token: str, proxy=None):
    @router.message(IsWebAppData())
    async def handler(message: Message):
        """
           处理用户在 WebApp 完成验证得到 reCaptcha Response 事件
           """
        user_id = message.from_user.id
        if user_id not in users_state:
            return
        if not verify_recaptcha(message.web_app_data.data, token, proxy):
            await message.answer("验证失败")
            return

        chat_id = users_state[user_id][0]
        users_state[user_id][1] = STATE_PASS
        message_id = users_state[user_id][2]
        if reset_permissions:
            chat = await message.bot.get_chat(chat_id)
            await message.bot.restrict_chat_member(chat_id, user_id, chat.permissions)
        await message.answer("验证通过")
        msg = await message.bot.send_message(chat_id, f"{hbold(message.from_user.full_name)}验证通过")
        await sleep(5)
        await message.bot.delete_message(chat_id, message_id)
        await message.bot.delete_message(chat_id, msg.message_id)


def reg_new_member_handler(router: Router, test_time: int, bot_name: str, reset_permissions: bool):
    """
    处理新用户入群事件
    :param router:
    :param test_time:
    :param bot_name:
    :param reset_permissions:
    :return:
    """

    @router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), IsAdmin())
    async def handler(event: ChatMemberUpdated):
        keyboard = [[InlineKeyboardButton(text="点击验证", url=f"https://t.me/{bot_name}?start=verify")]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        msg = await event.answer(
            text=f"{hbold(event.new_chat_member.user.full_name)} 加入了, 请在 {test_time} 秒内私聊通过验证 !",
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


def get_handlers_router(bot_name: str,
                        webapp_url: str,
                        recaptcha_token: str,
                        reset_permissions: bool,
                        test_time: int,
                        proxy: str):
    router = Router()
    reg_command_start_handler(router, webapp_url)
    reg_callback_handler(router, reset_permissions, recaptcha_token, proxy)
    reg_new_member_handler(router, test_time, bot_name, reset_permissions)
    return router
