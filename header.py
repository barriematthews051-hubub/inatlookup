import struct
import time

from constants import *


def build_header(record_count):

    header = bytearray(HEADER_SIZE)

    # Magic signature
    header[0:8] = MAGIC

    # Format version
    struct.pack_into(
        "<I",
        header,
        8,
        FORMAT_VERSION
    )

    # Reserved (bytes 12-15)

    # Number of records
    struct.pack_into(
        "<Q",
        header,
        16,
        record_count
    )

    # Record size
    struct.pack_into(
        "<I",
        header,
        24,
        RECORD_SIZE
    )

    # Header size
    struct.pack_into(
        "<I",
        header,
        28,
        HEADER_SIZE
    )

    # Build time (Unix timestamp)
    struct.pack_into(
        "<Q",
        header,
        32,
        int(time.time())
    )

    return bytes(header)


def read_header(f):

    header = f.read(HEADER_SIZE)

    if len(header) != HEADER_SIZE:
        raise RuntimeError("Header is incomplete.")

    magic = header[0:8]

    if magic != MAGIC:
        raise RuntimeError("Not a valid inatlookup index.")

    version = struct.unpack_from("<I", header, 8)[0]

    if version != FORMAT_VERSION:
        raise RuntimeError(
            f"Unsupported index format version: {version}"
        )

    record_count = struct.unpack_from("<Q", header, 16)[0]

    record_size = struct.unpack_from("<I", header, 24)[0]

    if record_size != RECORD_SIZE:
        raise RuntimeError(
            f"Unsupported record size: {record_size}"
        )

    header_size = struct.unpack_from("<I", header, 28)[0]

    if header_size != HEADER_SIZE:
        raise RuntimeError(
            f"Unsupported header size: {header_size}"
        )

    build_time = struct.unpack_from("<Q", header, 32)[0]

    return {
        "magic": magic,
        "version": version,
        "record_count": record_count,
        "record_size": record_size,
        "header_size": header_size,
        "build_time": build_time,
    }