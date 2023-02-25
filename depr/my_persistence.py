from typing import (
    Dict,
    Optional,
)

from telegram.ext import (
    BasePersistence,
)
from telegram.ext._utils.types import (
    BD,
    CD,
    UD,
    CDCData,
    ConversationDict,
    ConversationKey,
)


class MyPersistence(BasePersistence):
    async def get_user_data(self) -> Dict[int, UD]:
        pass

    async def get_chat_data(self) -> Dict[int, CD]:
        pass

    async def get_bot_data(self) -> BD:
        pass

    async def get_callback_data(self) -> Optional[CDCData]:
        pass

    async def get_conversations(self, name: str) -> ConversationDict:
        pass

    async def update_conversation(self, name: str, key: ConversationKey, new_state: Optional[object]) -> None:
        pass

    async def update_user_data(self, user_id: int, data: UD) -> None:
        pass

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        pass

    async def update_bot_data(self, data: BD) -> None:
        pass

    async def update_callback_data(self, data: CDCData) -> None:
        pass

    async def drop_chat_data(self, chat_id: int) -> None:
        pass

    async def drop_user_data(self, user_id: int) -> None:
        pass

    async def refresh_user_data(self, user_id: int, user_data: UD) -> None:
        pass

    async def refresh_chat_data(self, chat_id: int, chat_data: CD) -> None:
        pass

    async def refresh_bot_data(self, bot_data: BD) -> None:
        pass

    async def flush(self) -> None:
        pass
