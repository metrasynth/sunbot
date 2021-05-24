import asyncio
import os
from logging import getLogger, basicConfig
import sys
from pathlib import Path
from typing import List

import discord
import librosa
import librosa.display
import matplotlib.pyplot as plot
import numpy
from scipy.io import wavfile

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
                    wav_path = sunvox_path.with_suffix(".wav")
                    await sunvox2audio(
                        process=process,
                        slot=slot,
                        audio_paths=[ogg_path, wav_path],
                        freq=freq,
                        channels=channels,
                    )
                    log.info("Rendered to %r", ogg_path)
                    with ogg_path.open("rb") as f:
                        upload_file = discord.File(f, filename=ogg_path.name)
                        content = f"Here is the audio file for {project_name!r}:"
                        await channel.send(content=content, file=upload_file)
                        log.info("OGG Sent to %r", channel)
                except Exception:
                    await channel.send(
                        f"I found a file called {sunvox_path.name!r} but it "
                        "could not be loaded and rendered to an "
                        "audio file."
                    )
                    raise
                # try:
                #     # [TODO] do all this in a thread
                #     png_path = sunvox_path.with_suffix(".png")
                #     with wav_path.open("rb") as f:
                #         freq, data = wavfile.read(f)
                #     wav_path.unlink()
                #     y = data.transpose()
                #     plot.figure(figsize=(14, 9))
                #     plot.suptitle(project_name, color="white", weight="bold", size=14)
                #     plot.subplot(211)
                #     plot.title(None)
                #     mono_y = (y[0] + y[1]) / 2
                #     CQT = librosa.amplitude_to_db(
                #         numpy.abs(librosa.cqt(mono_y, sr=freq)),
                #         ref=numpy.max,
                #     )
                #     librosa.display.specshow(
                #         CQT, x_axis="time", y_axis="cqt_note", sr=freq
                #     )
                #     # ax.set_xlabel(None)
                #     plot.subplot(212)
                #     plot.title(None)
                #     librosa.display.waveplot(mono_y, sr=freq, alpha=0.5, color="black")
                #     librosa.display.waveplot(y[0], sr=freq, alpha=0.5, color="blue")
                #     librosa.display.waveplot(y[1], sr=freq, alpha=0.5, color="red")
                #     plot.tight_layout()
                #     plot.savefig(png_path)
                #     with png_path.open("rb") as f:
                #         upload_file = discord.File(f, filename=png_path.name)
                #         await channel.send(file=upload_file)
                #         log.info("PNG Sent to %r", channel)
                # except Exception:
                #     await channel.send(
                #         f"I could not render the spectrogram and waveform for {project_name!r}"
                #     )
                #     raise


async def sunvox2audio(
    process: BufferedProcess,
    slot: Slot,
    audio_paths: List[Path],
    freq: int,
    channels: int,
    max_file_size=8000000,
):
    audio_paths = [Path(p) for p in audio_paths]
    try:
        length = slot.get_song_length_frames()
        log.info("Sunvox reports song length is %d frames", length)
        slot.play_from_beginning()
        position = 0
        audio_files = [
            SoundFile(
                str(p),
                "w",
                freq,
                channels,
                "FLOAT" if str(p).endswith(".wav") else None,
            )
            for p in audio_paths
        ]
        try:
            while position < length:
                percentage = position * 100.0 / length
                buffer = process.fill_buffer()
                one_second = position + freq
                end_pos = min(one_second, length)
                copy_size = end_pos - position
                if copy_size < one_second:
                    buffer = buffer[:copy_size]
                for f in audio_files:
                    f.buffer_write(buffer, dtype="float32")
                with audio_paths[0].open("rb") as primary_f:
                    primary_f.seek(0, 2)
                    file_size = primary_f.tell()
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
            for f in audio_files:
                f.close()
    finally:
        process.kill()


def main():
    basicConfig(level="DEBUG")
    sunvox_path, ogg_path = sys.argv[1:]
    future = sunvox2audio(sunvox_path, ogg_path)
    asyncio.get_event_loop().run_until_complete(future)


if __name__ == "__main__":
    main()
