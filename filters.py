import aiogram
import functools
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, ChatMember, ChatMemberAdministrator


class IsEnableGroup(BaseFilter):
    def __init__(self, groups: list[str] | str | None) -> None:
        self.groups = groups
        pass

    async def __call__(self, query_or_message: Message | CallbackQuery) -> bool:
        if not query_or_message.chat.type == 'supergroup':
            return False
        member = await query_or_message.chat.get_member(query_or_message.bot.id)
        if not isinstance(member, ChatMemberAdministrator):
            return False
        if not query_or_message.chat.type == 'supergroup':
            return False
        group_id = query_or_message.chat.username
        if not self.groups:
            return True
        if self.groups == group_id or group_id in self.groups:
            return True
        return False


class IsWebAppData(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        return message.web_app_data is not None and message.chat.type == 'private'


class IsNewMember(BaseFilter):
    def __init__(self) -> None:
        pass

    async def __call__(self, message: Message) -> bool:
        return message.new_chat_members is not None
