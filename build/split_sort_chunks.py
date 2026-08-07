import gzip
import csv
import struct
import heapq
import os
import time

CSV_FILE = "photos.csv.gz"
CHUNK_DIR = "chunks"

ROWS_PER_CHUNK = 2_000_000

os.makedirs(CHUNK_DIR, exist_ok=True)

def uuid_to_bytes(u):
    return bytes.fromhex(u.replace("-", ""))

start = time.time()

chunk = []
chunk_num = 0
total = 0

with gzip.open(CSV_FILE, "rt", encoding="utf-8") as f:

    reader = csv.DictReader(f, delimiter="\t")

    for row in reader:

        photo_id = int(row["photo_id"])
        obs_uuid = uuid_to_bytes(row["observation_uuid"])

        chunk.append((photo_id, obs_uuid))
        total += 1

        if len(chunk) >= ROWS_PER_CHUNK:

            chunk_num += 1

            print(f"Sorting chunk {chunk_num}...")

            chunk.sort(key=lambda x: x[0])

            outfile = os.path.join(
                CHUNK_DIR,
                f"chunk_{chunk_num:03d}.bin"
            )

            with open(outfile, "wb") as out:

                for pid, uuid in chunk:
                    out.write(struct.pack(">Q", pid))
                    out.write(uuid)

            print(
                f"Saved {outfile} "
                f"({len(chunk):,} records)"
            )

            chunk.clear()

if chunk:

    chunk_num += 1

    print(f"Sorting final chunk {chunk_num}...")

    chunk.sort(key=lambda x: x[0])

    outfile = os.path.join(
        CHUNK_DIR,
        f"chunk_{chunk_num:03d}.bin"
    )

    with open(outfile, "wb") as out:

        for pid, uuid in chunk:
            out.write(struct.pack(">Q", pid))
            out.write(uuid)

elapsed = time.time() - start

print()
print(f"Chunks created : {chunk_num}")
print(f"Rows processed : {total:,}")
print(f"Elapsed minutes: {elapsed/60:.1f}")