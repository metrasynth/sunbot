import asyncio
import os
from logging import getLogger
from pathlib import Path
from textwrap import dedent
from zipfile import ZipFile

import discord
from discord import Thread
from sunvox.api import Slot
from sunvox.buffered import BufferedProcess

log = getLogger(__name__)

FILES_PATH = Path(__file__).parent / "files"
MAX_UNZIPPED_FILE_SIZE = 64 * 1024 * 1024  # 64 MB


class ProjectRendererClientMixin:
    async def __on_message__(self, message: discord.Message):
        channel: discord.TextChannel = message.channel
        if os.getenv("PROJECTRENDERER") != "1":
            return
        for attachment in message.attachments:
            await self.__render_attachment(attachment, channel, message)

    async def __render_attachment(self, attachment, channel, message):
        filename_lower = attachment.filename.lower()
        parts = filename_lower.rsplit(".", 1)
        if len(parts) != 2:
            return
        filename, ext = parts

        if ext == "zip":
            log.info("Found ZIP attachment of %d bytes", attachment.size)
            zip_path = FILES_PATH / str(attachment.id) / attachment.filename
            zip_path.parent.mkdir(parents=True, exist_ok=True)
            with zip_path.open("wb") as f:
                await attachment.save(f)
                log.info("Saved to %r", zip_path)
            zip_file = ZipFile(zip_path)
            for zip_info in zip_file.infolist():
                zipped_filename = zip_info.filename
                if not zipped_filename.lower().endswith(".sunvox"):
                    continue
                if zip_info.file_size > MAX_UNZIPPED_FILE_SIZE:
                    continue
                if "/" in zipped_filename or "\\" in zipped_filename:
                    continue
                sunvox_path = FILES_PATH / str(attachment.id) / zipped_filename
                sunvox_path.parent.mkdir(parents=True, exist_ok=True)
                log.info("Extracting %r to %r", zip_info, sunvox_path)
                with zip_file.open(zip_info, "r") as r, sunvox_path.open("wb") as w:
                    w.write(r.read())
                break
            else:
                # No SunVox files found in ZIP file.
                return
        elif ext == "sunvox":
            log.info("Found SunVox attachment of %d bytes", attachment.size)
            sunvox_path = FILES_PATH / str(attachment.id) / attachment.filename
            sunvox_path.parent.mkdir(parents=True, exist_ok=True)
            with sunvox_path.open("wb") as f:
                await attachment.save(f)
                log.info("Saved to %r", sunvox_path)
        else:
            # Not a ZIP or SunVox file.
            return

        try:
            process = BufferedProcess()
            slot = Slot(sunvox_path, process=process)
            project_name = slot.get_song_name() or "(Untitled)"
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

            rendering_ogg_preview_message = await thread.send(
                "Rendering OGG preview..."
            )

            ogg_path = sunvox_path.with_suffix(".ogg")
            sunvid_python = Path("~/.virtualenvs/sunvid/bin/python").expanduser()
            args = (
                str(sunvid_python),  # [TODO] get from env
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
            log.info(args)
            process = await asyncio.create_subprocess_exec(*args)
            await process.wait()

            with ogg_path.open("rb") as f:
                upload_file = discord.File(f, filename=ogg_path.name)
                await thread.send(file=upload_file)
            log.info("OGG Sent to %r", thread)
            await rendering_ogg_preview_message.delete()

            rendering_mp4_preview_message = await thread.send(
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
            args = (
                str(sunvid_python),  # [TODO] get from env
                "-m",
                "sunvid",
                "render",
                "--output-path-template",
                str(mp4_path),
                "--song-name-template",
                f"@{txt_path}",
                str(sunvox_path),
            )
            log.info(args)
            process = await asyncio.create_subprocess_exec(*args)
            await process.wait()

            with mp4_path.open("rb") as f:
                upload_file = discord.File(f, filename=mp4_path.name)
                content = f"Here is a preview of `{sanitized_project_name}`:"
                await thread.send(content=content, file=upload_file)
            log.info("MP4 Sent to %r", thread)
            await rendering_mp4_preview_message.delete()

            log.info("Rendering %r finished.", sunvox_path)

        except Exception as e:
            await channel.send(
                f"""I found a file called `{sunvox_path.name.replace('`', "'")}` """
                "but it could not be loaded and rendered to an audio file "
                "due to a SunBot error. "
                "On behalf of my maintainer, <@250124746618961920>, we apologize!"
            )
            raise
