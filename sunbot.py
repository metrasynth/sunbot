import logging
import os
from pathlib import Path
from typing import List

import discord
from dotenv import load_dotenv
from sunvox.api import Slot
from sunvox.buffered import BufferedProcess, float32

from autoreact import reactions_for_message_content
from reactions import REACTION_OPTIONS
from sunvox2ogg import sunvox2ogg

log = logging.getLogger(__name__)

FILES_PATH = Path(__file__).parent / "files"


class SunBotClient(discord.Client):
    def __init__(self, guild_names: List[str]):
        super(SunBotClient, self).__init__()
        self.guild_names = guild_names
        self.guild_emoji = {}

    async def on_ready(self):
        await self._on_ready_autoreactor()

    async def on_message(self, message: discord.Message):
        guild: discord.Guild = message.guild
        if message.author == self.user or guild.name not in self.guild_names:
            return
        await self._on_message_autoreactor(message)
        await self._on_message_projectrenderer(message)

    async def _on_ready_autoreactor(self):
        guild: discord.Guild
        emoji: discord.Emoji
        for guild in self.guilds:
            if guild.name in self.guild_names:
                e = self.guild_emoji[guild.id] = {}
                for emoji in guild.emojis:
                    ename = emoji.name.lower()
                    print(f"{guild.name} / {emoji.name} ({ename})")
                    e[ename] = emoji

    async def _on_message_autoreactor(self, message: discord.Message):
        emoji_map = self.guild_emoji[message.guild.id]
        reactions = reactions_for_message_content(
            content=message.content,
            emoji_map=emoji_map,
            reaction_options=REACTION_OPTIONS,
        )
        if reactions:
            log.info("Reacting to %r with %r", message.content, reactions)
        for reaction in reactions:
            await message.add_reaction(reaction)

    async def _on_message_projectrenderer(self, message: discord.Message):
        if os.getenv("PROJECTRENDERER") != "1":
            return
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(".sunvox"):
                log.info("Found SunVox attachment of %d bytes", attachment.size)
                sunvox_path = FILES_PATH / str(attachment.id) / attachment.filename
                sunvox_path.parent.mkdir(parents=True, exist_ok=True)
                with sunvox_path.open("wb") as f:
                    await attachment.save(f)
                    log.info("Saved to %r", sunvox_path)
                freq = 44100
                channels = 2
                process = BufferedProcess(
                    freq=freq, size=freq, channels=channels, data_type=float32
                )
                slot = Slot(sunvox_path, process=process)
                project_name = slot.get_song_name()
                channel: discord.TextChannel = message.channel
                await channel.send(
                    f"I found a SunVox Project, called {project_name!r}. "
                    "I'll render it to an OGG file now and upload it here."
                )
                ogg_path = sunvox_path.with_suffix(".ogg")
                await sunvox2ogg(
                    process=process,
                    slot=slot,
                    ogg_path=ogg_path,
                    freq=freq,
                    channels=channels,
                )
                log.info("Rendered to %r", ogg_path)
                with ogg_path.open("rb") as f:
                    upload_file = discord.File(f, filename=ogg_path.name)
                    content = f"Here is the OGG file for {project_name!r}:"
                    await channel.send(content=content, file=upload_file)
                    log.info("Sent to %r", channel)


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
