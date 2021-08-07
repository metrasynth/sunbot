import asyncio
import os
from logging import getLogger
from pathlib import Path
from textwrap import dedent

import discord
from sunvox.api import Slot
from sunvox.buffered import BufferedProcess, float32

log = getLogger(__name__)

FILES_PATH = Path(__file__).parent / "files"


class ProjectRendererClientMixin:
    async def __on_message__(self, message: discord.Message):
        channel: discord.TextChannel = message.channel
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
                try:
                    freq = 44100
                    channels = 2
                    process = BufferedProcess(
                        freq=freq,
                        size=freq,
                        channels=channels,
                        data_type=float32,
                    )
                    slot = Slot(sunvox_path, process=process)
                    project_name = slot.get_song_name()
                    process.kill()
                    await channel.send(
                        f"I found a SunVox Project, called {project_name!r}. "
                        "I'll render a preview of it now and upload it here."
                    )
                    project_info = dedent(
                        f"""
                        {project_name}
                        Uploaded by: {message.author}
                        to the "{message.channel}" channel
                        on the "{message.guild.name}" Discord server
                        at {message.created_at.isoformat()}
                        """
                    ).strip()
                    txt_path = sunvox_path.with_suffix(".txt")
                    txt_path.write_text(project_info)
                    mp4_path = sunvox_path.with_suffix(".mp4")
                    process = await asyncio.create_subprocess_exec(
                        "/home/bots/.virtualenvs/sunvid/bin/python",  # [TODO] get from env
                        "-m",
                        "sunvid",
                        "render",
                        "--font",
                        "/home/bots/proj/sunvid/SunDogMedium.ttf",  # [TODO] get from env
                        "--output-path-template",
                        str(mp4_path),
                        "--song-name-template",
                        f"@{txt_path}",
                        str(sunvox_path),
                    )
                    await process.wait()
                    log.info("Rendering %r finished.", sunvox_path)
                    with mp4_path.open("rb") as f:
                        upload_file = discord.File(f, filename=mp4_path.name)
                        content = f"Here is a preview of {project_name!r}:"
                        await channel.send(content=content, file=upload_file)
                        log.info("MP4 Sent to %r", channel)
                except Exception:
                    await channel.send(
                        f"I found a file called {sunvox_path.name!r} but it "
                        "could not be loaded and rendered to an "
                        "audio file."
                    )
                    raise
