import os
import struct
import heapq
import time

from header import build_header
from constants import HEADER_SIZE

CHUNK_DIR = "chunks"
OUTPUT_FILE = "inatlookup.bin"

RECORD_SIZE = 24

start = time.time()


class ChunkReader:
    def __init__(self, filename):
        self.filename = filename
        self.f = open(filename, "rb")
        self.photo_id = None
        self.uuid = None
        self.read()

    def read(self):
        data = self.f.read(RECORD_SIZE)

        if not data:
            self.photo_id = None
            self.uuid = None
            return

        self.photo_id = struct.unpack(">Q", data[:8])[0]
        self.uuid = data[8:]

    def close(self):
        self.f.close()


files = sorted(
    os.path.join(CHUNK_DIR, f)
    for f in os.listdir(CHUNK_DIR)
    if f.endswith(".bin")
)

readers = [ChunkReader(f) for f in files]

heap = []

for i, r in enumerate(readers):
    if r.photo_id is not None:
        heapq.heappush(heap, (r.photo_id, i))

count = 0

with open(OUTPUT_FILE, "wb") as out:

    # Write one 128-byte placeholder header
    out.write(b"\0" * HEADER_SIZE)

    while heap:

        photo_id, idx = heapq.heappop(heap)

        r = readers[idx]

        out.write(struct.pack(">Q", photo_id))
        out.write(r.uuid)

        count += 1

        r.read()

        if r.photo_id is not None:
            heapq.heappush(heap, (r.photo_id, idx))

        if count % 10_000_000 == 0:
            elapsed = time.time() - start
            rate = count / elapsed
            print(
                f"{count:,} records   "
                f"{rate:,.0f} records/sec"
            )

for r in readers:
    r.close()
    
with open(OUTPUT_FILE, "r+b") as out:
    out.seek(0)
    out.write(build_header(count))

elapsed = time.time() - start

print()
print(f"Finished")
print(f"Records: {count:,}")
print(f"Minutes: {elapsed/60:.1f}")