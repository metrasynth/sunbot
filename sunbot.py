import logging
import os
from typing import List

import discord
from dotenv import load_dotenv

from autoreactor import AutoReactorClientMixin
from projectrenderer import ProjectRendererClientMixin

log = logging.getLogger(__name__)


class SunBotClient(discord.Client, AutoReactorClientMixin, ProjectRendererClientMixin):
    def __init__(self, guild_names: List[str]):
        super(SunBotClient, self).__init__()
        self.guild_names = guild_names
        for cls in self.__class__.__bases__:
            if callable(getattr(cls, "__post_init__", None)):
                cls.__post_init__(self)

    async def on_ready(self):
        for cls in self.__class__.__bases__:
            if callable(getattr(cls, "__on_ready__", None)):
                await cls.__on_ready__(self)

    async def on_message(self, message: discord.Message):
        guild: discord.Guild = message.guild
        if message.author == self.user or guild.name not in self.guild_names:
            return
        for cls in self.__class__.__bases__:
            if callable(getattr(cls, "__on_message__", None)):
                await cls.__on_message__(self, message)


def main():
    load_dotenv("local.env")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=log_level)
    bot_token = os.environ["BOT_TOKEN"]
    guild_names = os.environ["GUILD_NAMES"].split(";")
    client = SunBotClient(guild_names=guild_names)
    client.run(bot_token)


if __name__ == "__main__":
    main()
