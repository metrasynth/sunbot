import os

import discord
from dotenv import load_dotenv


FILTER_OVERRIDES = {
    "filter": {"before": [":vocal", "vocal"], "after": ["pro", "pro:"]},
    "generator": {"before": [":analog", "analog"]},
}


class SunBotClient(discord.Client):
    def __init__(self):
        super(SunBotClient, self).__init__()
        self.guild_emoji = {}

    async def on_ready(self):
        guild: discord.Guild
        emoji: discord.Emoji
        for guild in self.guilds:
            e = self.guild_emoji[guild.id] = {}
            for emoji in guild.emojis:
                ename = emoji.name.lower()
                print(f"{guild.name} / {emoji.name} ({ename})")
                e[ename] = emoji

    async def on_message(self, message: discord.Message):
        if message.author == client.user:
            return
        e = self.guild_emoji[message.guild.id]
        searchtext = message.content.lower().replace(" ", "")
        reactions_by_index = {}
        for ename in e:
            start = 0
            while True:
                try:
                    idx = searchtext.index(ename, start)
                except ValueError:
                    break
                start = idx + len(ename)
                overrides = FILTER_OVERRIDES.get(ename)
                override_found = False
                if overrides:
                    before = overrides.get("before", [])
                    after = overrides.get("after", [])
                    for override in before:
                        if (first := idx - len(override)) >= 0:
                            searchbefore = searchtext[first:idx]
                            if searchbefore == override:
                                override_found = True
                                break
                    if not override_found:
                        for override in after:
                            if (last := start + len(override)) <= len(searchtext):
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


if __name__ == "__main__":
    load_dotenv("local.env")
    TOKEN = os.getenv("BOT_TOKEN")
    client = SunBotClient()

    client.run(TOKEN)
