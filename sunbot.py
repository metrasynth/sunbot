import logging
import os
from typing import List

import discord
from dotenv import load_dotenv
from normality import ascii_text

log = logging.getLogger(__name__)


EMOJI_REACTIONS = {
    "amplifier": {},
    "analoggenerator": {},
    "compressor": {},
    "dcblocker": {},
    "delay": {},
    "distortion": {},
    "drumsynth": {},
    "echo": {},
    "eq": {},
    "feedback": {},
    "filter": {"nobefore": [":vocal", "vocal"], "noafter": ["pro", "pro:"]},
    "filterpro": {"nobefore": ["vocal"]},
    "flanger": {},
    "fm": {},
    "generator": {"nobefore": [":analog", "analog"]},
    "glide": {},
    "gpio": {},
    "input": {},
    "kicker": {},
    "lfo": {},
    "loop": {},
    "metamodule": {},
    "modulator": {},
    "multictl": {},
    "multisynth": {},
    "output": {},
    "pitch2ctl": {},
    "pitchshifter": {},
    "reverb": {},
    "sampler": {},
    "sound2ctl": {},
    "spectravoice": {},
    "velocity2ctl": {},
    "vibrato": {},
    "vocalfilter": {"noafter": ["pro"]},
    "vorbisplayer": {},
    "waveshaper": {},
}


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
        e = self.guild_emoji[message.guild.id]
        searchtext = message.content
        # extract salt 😎
        searchtext = searchtext.replace("ꜞ", "i").replace("\u2006", " ")
        # 6-bit distortion 🎸
        searchtext = ascii_text(searchtext)
        # waveshaper ∿
        searchtext = searchtext.replace(" ", "").lower()
        log.debug("searchtext transformed %r -> %r", message.content, searchtext)
        reactions_by_index = {}
        for ename in set(e).intersection(set(EMOJI_REACTIONS)):
            start = 0
            while True:
                try:
                    idx = searchtext.index(ename, start)
                except ValueError:
                    break
                start = idx + len(ename)
                overrides = EMOJI_REACTIONS.get(ename)
                override_found = False
                if overrides:
                    nobefore = overrides.get("nobefore", [])
                    noafter = overrides.get("noafter", [])
                    for override in nobefore:
                        first = idx - len(override)
                        if first >= 0:
                            searchbefore = searchtext[first:idx]
                            if searchbefore == override:
                                override_found = True
                                break
                    if not override_found:
                        for override in noafter:
                            last = start + len(override)
                            if last <= len(searchtext):
                                searchafter = searchtext[start:last]
                                if searchafter == override:
                                    override_found = True
                                    break
                if (
                    idx > 0
                    and searchtext[idx - 1] == ":"
                    and start < len(searchtext)
                    and searchtext[start] == ":"
                ):
                    override_found = True
                if not override_found:
                    reactions_by_index[idx] = ename
        reactions = [ename for idx, ename in sorted(reactions_by_index.items())]
        if reactions:
            log.info("Reacting to %r with %r", message.content, reactions)
        for ename in reactions:
            await message.add_reaction(e[ename])

    async def _on_message_projectrenderer(self, message: discord.Message):
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(".sunvox"):
                log.info("Found SunVox attachment of %d bytes", attachment.size)


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
