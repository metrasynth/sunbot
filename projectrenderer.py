import asyncio
import os
from logging import getLogger
from pathlib import Path
from textwrap import dedent

import discord
from discord import Thread
from sunvox.api import Slot
from sunvox.buffered import BufferedProcess

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
                    song_length = slot.get_song_length_frames()
                    process.kill()

                    if song_length == 0:
                        return

                    if isinstance(message.channel, Thread):
                        thread = message.channel
                    else:
                        thread = await message.create_thread(
                            name=project_name,
                            auto_archive_duration=60,
                        )
                    sanitized_project_name = project_name.replace("`", "'")
                    initial1 = await thread.send(
                        f"Found a SunVox project called `{sanitized_project_name}`. "
                        "Rendering MP4 preview..."
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
                        "--output-path-template",
                        str(mp4_path),
                        "--song-name-template",
                        f"@{txt_path}",
                        str(sunvox_path),
                    )
                    await process.wait()

                    with mp4_path.open("rb") as f:
                        upload_file = discord.File(f, filename=mp4_path.name)
                        content = f"Here is a preview of `{sanitized_project_name}`:"
                        await thread.send(content=content, file=upload_file)
                    log.info("MP4 Sent to %r", thread)
                    await initial1.delete()

                    initial2 = await thread.send("Rendering OGG preview...")

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
                        "--output-path-template",
                        str(ogg_path),
                        str(sunvox_path),
                    )
                    await process.wait()

                    with ogg_path.open("rb") as f:
                        upload_file = discord.File(f, filename=ogg_path.name)
                        await thread.send(file=upload_file)
                    log.info("OGG Sent to %r", thread)
                    await initial2.delete()

                    log.info("Rendering %r finished.", sunvox_path)

                except Exception as e:
                    await channel.send(
                        f"""I found a file called `{sunvox_path.name.replace('`', "'")}` but it """
                        "could not be loaded and rendered to an "
                        f"audio file due to an error: {e}."
                    )
                    raise
