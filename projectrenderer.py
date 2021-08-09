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
                    process = BufferedProcess()
                    slot = Slot(sunvox_path, process=process)
                    project_name = slot.get_song_name()
                    process.kill()

                    thread = await message.start_thread(
                        name=project_name,
                        auto_archive_duration=60,
                    )
                    initial = await thread.send(
                        f"I found a SunVox Project, called {project_name!r}. "
                        "I'll render a preview of it now and upload it here."
                    )
                    project_info = dedent(
                        f"""
                        {project_name}
                        Uploaded by: {message.author.display_name}
                        to #{message.channel}
                        ({message.guild.name} Discord server)
                        at {message.created_at.replace(microsecond=0).isoformat()}
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

                    ogg_path = sunvox_path.with_suffix(".ogg")
                    process = await asyncio.create_subprocess_exec(
                        "/home/bots/.virtualenvs/sunvid/bin/python",  # [TODO] get from env
                        "-m",
                        "sunvid",
                        "render",
                        "--audio-codec",
                        "libvorbis",
                        "--video-codec",
                        "none",
                        "--font",
                        "/home/bots/proj/sunvid/SunDogMedium.ttf",  # [TODO] get from env
                        "--output-path-template",
                        str(ogg_path),
                        str(sunvox_path),
                    )
                    await process.wait()

                    log.info("Rendering %r finished.", sunvox_path)
                    with mp4_path.open("rb") as f:
                        upload_file = discord.File(f, filename=mp4_path.name)
                        content = f"Here is a preview of {project_name!r}:"
                        await thread.send(content=content, file=upload_file)
                        log.info("MP4 Sent to %r", thread)
                    with ogg_path.open("rb") as f:
                        upload_file = discord.File(f, filename=ogg_path.name)
                        await thread.send(file=upload_file)
                        log.info("OGG Sent to %r", thread)
                    await initial.delete()
                except Exception as e:
                    await channel.send(
                        f"I found a file called {sunvox_path.name!r} but it "
                        "could not be loaded and rendered to an "
                        f"audio file due to an error: {e}."
                    )
                    raise
