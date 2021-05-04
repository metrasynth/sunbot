import os

import aiohttp
from logging import getLogger


import discord

log = getLogger(__name__)


class SunvoxAudioUploaderMixin:
    async def __on_message__(self, message: discord.Message):
        for attachment in message.attachments:
            filename = attachment.filename.lower()
            if filename.endswith(".sunvox") or filename.endswith(".sunsynth"):
                log.info("Found SunVox attachment at %r", attachment.url)
                metadata = {"discord": {"uid": str(message.author.id)}}
                secret_key = os.getenv("SVAUDIO_REPO_API_SECRET_KEY")
                request_body = {
                    "url": attachment.url,
                    "metadata": metadata,
                    "key": secret_key,
                }
                headers = {"Content-Type": "application/json"}
                async with aiohttp.ClientSession(headers=headers) as session:
                    url = "https://sunvox.audio/locations/submit/api/"
                    async with session.post(url, json=request_body) as r:
                        json_body = (await r.json()) or {}
                        submitted = json_body.get("submitted", False)
                # [TODO] send someting to the channel about whether it was submitted.
