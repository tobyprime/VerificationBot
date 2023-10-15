from aiogram import Router
from aiogram.filters import CommandStart, CommandObject, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.markdown import hbold

from recaptcha import verify_recaptcha, deferred_verification, users_state, STATE_PASS


def reg_command_start_handler(router: Router, webapp_url: str):
    @router.message(CommandStart())
    async def handler(message: Message, command: CommandObject):
        """
        处理用户与 Bot 开始对话
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
    @router.message()
    async def handler(message: Message):
        """
           处理用户在 WebApp 完成验证后的 reCaptcha Response
           """
        if not message.web_app_data:
            return
        user_id = message.from_user.id
        if user_id not in users_state:
            return
        if not verify_recaptcha(message.web_app_data.data, token, proxy):
            await message.answer("验证失败")
            return

        chat_id = users_state[user_id][0]
        users_state[user_id][1] = STATE_PASS

        if reset_permissions:
            chat = await message.bot.get_chat(chat_id)
            await message.bot.restrict_chat_member(chat_id, user_id, chat.permissions)

        await message.answer("验证通过")


def reg_new_member_handler(router: Router, test_time: int, bot_name: str, reset_permissions: bool):
    @router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION))
    async def handler(event: ChatMemberUpdated):
        keyboard = [[InlineKeyboardButton(text="点击验证", url=f"https://t.me/{bot_name}?start=verify")]]
        markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        msg = await event.answer(
            text=f"{hbold(event.new_chat_member.user.full_name)} 加入了, 请在 {test_time} 秒内私聊通过验证 !",
            reply_markup=markup
        )

        await deferred_verification(
            chat_id=msg.chat.id,
            message_id=msg.message_id,
            user_id=event.new_chat_member.user.id,
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
