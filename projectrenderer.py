import asyncio
import os
from logging import getLogger, basicConfig
import sys
from pathlib import Path

import discord
from soundfile import SoundFile
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
                        freq=freq, size=freq, channels=channels, data_type=float32
                    )
                    slot = Slot(sunvox_path, process=process)
                    project_name = slot.get_song_name()
                    await channel.send(
                        f"I found a SunVox Project, called {project_name!r}. "
                        "I'll render it to an audio file now and upload it here."
                    )
                    ogg_path = sunvox_path.with_suffix(".ogg")
                    await sunvox2audio(
                        process=process,
                        slot=slot,
                        audio_path=ogg_path,
                        freq=freq,
                        channels=channels,
                    )
                    log.info("Rendered to %r", ogg_path)
                    with ogg_path.open("rb") as f:
                        upload_file = discord.File(f, filename=ogg_path.name)
                        content = f"Here is the audio file for {project_name!r}:"
                        await channel.send(content=content, file=upload_file)
                        log.info("Sent to %r", channel)
                except Exception:
                    await channel.send(
                        f"I found a file called {sunvox_path.name!r} but it "
                        "could not be loaded and rendered to an "
                        "audio file."
                    )
                    raise


async def sunvox2audio(
    process: BufferedProcess,
    slot: Slot,
    audio_path: Path,
    freq: int,
    channels: int,
    max_file_size=8000000,
):
    audio_path = Path(audio_path)
    try:
        length = slot.get_song_length_frames()
        log.info("Sunvox reports song length is %d frames", length)
        slot.play_from_beginning()
        position = 0
        with SoundFile(str(audio_path), "w", freq, channels) as audio_f:
            while position < length:
                percentage = position * 100.0 / length
                buffer = process.fill_buffer()
                one_second = position + freq
                end_pos = min(one_second, length)
                copy_size = end_pos - position
                if copy_size < one_second:
                    buffer = buffer[:copy_size]
                audio_f.buffer_write(buffer, dtype="float32")
                with audio_path.open("rb") as written_ogg_f:
                    written_ogg_f.seek(0, 2)
                    file_size = written_ogg_f.tell()
                    if file_size > max_file_size:
                        log.warning(
                            "Stopped writing at %r bytes (exceeded %r)",
                            file_size,
                            max_file_size,
                        )
                        break
                log.info(
                    "Rendered %r of %r (%.2f%%), %r bytes written",
                    position,
                    length,
                    percentage,
                    file_size,
                )
                position = end_pos
                await asyncio.sleep(0)
    finally:
        process.kill()


def main():
    basicConfig(level="DEBUG")
    sunvox_path, ogg_path = sys.argv[1:]
    future = sunvox2audio(sunvox_path, ogg_path)
    asyncio.get_event_loop().run_until_complete(future)


if __name__ == "__main__":
    main()
