from asyncio import sleep
from functools import partial

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject, ChatMemberUpdatedFilter, JOIN_TRANSITION
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, ChatMemberUpdated, \
    InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, CallbackQuery, User

from filters import IsEnableGroup, IsWebAppData, IsNewMember
from verification import verification, user_states, STATE_PASS


async def command_start_handler(message: Message, command: CommandObject, webapp_url: str):
    """
    处理用户与 Bot 开始对话命令事件
    点击验证按钮在 webapp 中完成验证返回 responses 后由 :func:`web_callback_handler` 处理
    :param message: Command Start 的信息
    :param command: 命令对象，包含命令参数
    :param webapp_url: 用于验证的 web app 页面地址

    """
    if command.args is None or command.args != 'verify':
        return

    user_id = message.from_user.id

    if user_id not in user_states:
        return await message.answer(f"你没有待通过的入群验证")

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="点击验证", web_app=WebAppInfo(url=webapp_url))]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    msg = await message.answer("请点击下方按钮进行验证（如果未找到按钮请在底部选项内查找）", reply_markup=keyboard)
    user_states[user_id].private_tip_msg = msg


def get_at(user: User, mask: bool = True):
    """
    @群成员
    :param user: @的用户
    :param mask: 是否遮挡用户名
    :return:
    """
    name = user.full_name
    masked_name = (name[0] + '███' + name[-1]) if len(name) >= 3 and mask else name
    return user.mention_html(masked_name)


async def web_callback_handler(message: Message, token: str, reset_permissions: bool, proxy: str | None,
                               validator: callable):
    """
    处理用户在 WebApp 完成验证得到 Response 事件
    :param message: 携带 response 的消息
    :param token: recaptcha 或 turnstile 后端验证的 secret token
    :param reset_permissions: 是否需要将用户的权限重设为默认权限（在启用进群禁言时需要同时启用）
    :param proxy: 后端验证时使用的代理服务器
    :param validator: 后端验证器为 :func:`verify_recaptcha` 或 :func:`verify_turnstile`
    """
    user_id = message.from_user.id
    if user_id not in user_states:
        return

    if not validator(message.web_app_data.data, token, proxy):
        return await message.answer("验证失败，请重试")

    bot = message.bot
    chat_id = user_states[user_id].chat_id
    user_states[user_id].state = STATE_PASS

    if reset_permissions:
        chat = await bot.get_chat(chat_id)
        await bot.restrict_chat_member(chat_id, user_id, chat.permissions)

    await message.answer("验证通过", reply_markup=ReplyKeyboardRemove())
    await bot.send_message(chat_id, f"{get_at(message.from_user, mask=False)} 通过了验证")

    await sleep(5)
    await bot.delete_message(chat_id, user_states[user_id].group_tip_msg.message_id)


async def new_member_handler(event: ChatMemberUpdated, test_time: int, shutup: bool, ban: bool,
                             ban_time: int | None):
    """
    处理新进群事件，提示进行验证，点击验证后的事件由 :func:`click_button_handler` 处理
    :param event: 事件，包含入群人的信息
    :param test_time: 进行测试的最大时长
    :param shutup: 是否在通过验证前禁言用户
    :param ban: 验证失败后是否封禁
    :param ban_time: 封禁时间，空为永久
    """
    keyboard = [[InlineKeyboardButton(text="点击验证", callback_data="go_to_verify")]]
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    msg = await event.answer(
        text=f"{get_at(event.from_user)} 加入了, 请在 {test_time} 秒内私聊通过验证 !",
        reply_markup=markup
    )

    await verification(
        chat=msg.chat,
        group_tip_message=msg,
        user=event.new_chat_member.user,
        bot=event.bot,
        shutup_before_verification=shutup,
        test_time=test_time,
        ban=ban,
        ban_time=ban_time
    )


async def click_button_handler(callback: CallbackQuery):
    """
    群聊内用户点击验证事件，判断是否需要进行验证
    :param callback: 按钮的回调
    """
    if callback.data != "go_to_verify":
        return
    if callback.from_user.id not in user_states:
        return await callback.answer(text="你没有待验证的进群请求", show_alert=True)
    await callback.answer(url=f"https://t.me/{(await callback.bot.get_me()).username}?start=verify")


async def new_member_tip_handler(message: Message):
    """
    自动删除进群消息
    """
    await message.delete()


def get_handlers_router(webapp_url: str,
                        secret_token: str,
                        validator: callable,
                        shutup: bool,
                        test_time: int,
                        proxy: str | None,
                        groups: str | list[str] | None,
                        ban: bool,
                        ban_time: int | None):
    """
    获取注册了所有 handler 的路由
    :param webapp_url: 用于验证的 web app 页面地址
    :param secret_token: recaptcha 或 turnstile 后端验证的 secret token
    :param validator: 后端验证器为 :func:`verify_recaptcha` 或 :func:`verify_turnstile`
    :param shutup: 是否在通过验证前禁言用户
    :param test_time: 进行测试的最大时长
    :param proxy: 后端验证时使用的代理服务器
    :param groups: 启用验证的群组列表
    :param ban: 验证失败后是否封禁
    :param ban_time: 封禁时间，空为永久
    :return: 路由
    """
    router = Router()

    router.message(CommandStart())(
        partial(command_start_handler, webapp_url=webapp_url))

    router.message(IsWebAppData())(
        partial(web_callback_handler,
                token=secret_token,
                reset_permissions=shutup,
                proxy=proxy,
                validator=validator, ))

    router.chat_member(ChatMemberUpdatedFilter(JOIN_TRANSITION), IsEnableGroup(groups))(
        partial(new_member_handler,
                test_time=test_time,
                shutup=shutup,
                ban=ban,
                ban_time=ban_time
                ))

    router.callback_query()(click_button_handler)

    router.message(IsNewMember(), IsEnableGroup(groups))(new_member_tip_handler)
    return router
