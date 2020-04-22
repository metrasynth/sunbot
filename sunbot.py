import os
from typing import List, Optional

import discord
from dotenv import load_dotenv

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
    "filterpro": {},
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
    "vocalfilter": {},
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
        await self._on_message_autoreactor(message)

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
        guild: discord.Guild = message.guild
        if message.author == self.user or guild.name not in self.guild_names:
            return
        e = self.guild_emoji[message.guild.id]
        searchtext = message.content.lower().replace(" ", "")
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
            print(f"Reacting to f{message.content!r} with {reactions}")
        for ename in reactions:
            await message.add_reaction(e[ename])


def main():
    load_dotenv("local.env")
    bot_token = os.environ["BOT_TOKEN"]
    guild_names = os.environ["GUILD_NAMES"].split(";")
    client = SunBotClient(guild_names=guild_names)
    client.run(bot_token)


if __name__ == "__main__":
    main()
