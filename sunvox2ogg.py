import asyncio
from logging import getLogger, basicConfig
import sys
from pathlib import Path

from soundfile import SoundFile
from sunvox.api import Slot
from sunvox.buffered import BufferedProcess

log = getLogger(__name__)


async def sunvox2ogg(
    process: BufferedProcess,
    slot: Slot,
    ogg_path: Path,
    freq: int,
    channels: int,
    max_file_size=8000000,
):
    ogg_path = Path(ogg_path)
    try:
        length = slot.get_song_length_frames()
        log.info("Sunvox reports song length is %d frames", length)
        slot.play_from_beginning()
        position = 0
        with SoundFile(str(ogg_path), "w", freq, channels) as ogg_f:
            while position < length:
                log.info("%r, %r", position, length)
                buffer = process.fill_buffer()
                one_second = position + freq
                end_pos = min(one_second, length)
                copy_size = end_pos - position
                if copy_size < one_second:
                    buffer = buffer[:copy_size]
                ogg_f.buffer_write(buffer, dtype="float32")
                with ogg_path.open("rb") as written_ogg_f:
                    written_ogg_f.seek(0, 2)
                    file_size = written_ogg_f.tell()
                    if file_size > max_file_size:
                        log.warning(
                            "Stopped writing at %r bytes (exceeded %r)",
                            file_size,
                            max_file_size,
                        )
                        break
                position = end_pos
                await asyncio.sleep(0)
    finally:
        process.kill()


def main():
    basicConfig(level="DEBUG")
    sunvox_path, ogg_path = sys.argv[1:]
    future = sunvox2ogg(sunvox_path, ogg_path)
    asyncio.get_event_loop().run_until_complete(future)


if __name__ == "__main__":
    main()
