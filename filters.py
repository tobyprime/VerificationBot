import aiogram
import functools
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, ChatMember, ChatMemberAdministrator


class IsAdmin(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, query_or_message: Message | CallbackQuery) -> bool:
        member = await query_or_message.chat.get_member(query_or_message.bot.id)
        return isinstance(member, ChatMemberAdministrator) and query_or_message.chat.type == 'supergroup'


class IsWebAppData(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        return message.web_app_data is not None and message.chat.type == 'private'
