import discord


class KeepAliveMixin:

    async def __on_ready__(self: discord.Client):
        async def keepalive():
            pass
