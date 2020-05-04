import asyncio
from logging import getLogger, basicConfig
import sys

import soundfile as sf
from sunvox.api import Slot
from sunvox.buffered import BufferedProcess, float32

log = getLogger(__name__)


async def sunvox2ogg(sunvox_path: str, ogg_path: str, max_file_size=8000000):
    freq = 44100
    channels = 2
    p = BufferedProcess(freq=freq, size=freq, channels=channels, data_type=float32)
    try:
        slot = Slot(sunvox_path, process=p)
        length = slot.get_song_length_frames()
        slot.play_from_beginning()
        position = 0
        with sf.SoundFile(ogg_path, "w", freq, channels) as ogg_f:
            while position < length:
                log.info("%r, %r", position, length)
                buffer = p.fill_buffer()
                one_second = position + freq
                end_pos = min(one_second, length)
                copy_size = end_pos - position
                if copy_size < one_second:
                    buffer = buffer[:copy_size]
                ogg_f.buffer_write(buffer, dtype="float32")
                with open(ogg_path, "rb") as written_ogg_f:
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
        p.kill()


def main():
    basicConfig(level="DEBUG")
    sunvox_path, ogg_path = sys.argv[1:]
    future = sunvox2ogg(sunvox_path, ogg_path)
    asyncio.get_event_loop().run_until_complete(future)


if __name__ == "__main__":
    main()
