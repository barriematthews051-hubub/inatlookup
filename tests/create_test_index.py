import os
import sys
import struct
import uuid

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from header import build_header
from constants import RECORD_SIZE


TEST_RECORDS = [
    (
        100000001,
        "11111111-1111-1111-1111-111111111111"
    ),
    (
        100000002,
        "22222222-2222-2222-2222-222222222222"
    ),
    (
        455606536,
        "9bcb94d0-cf6f-4ab0-9c5b-7301685acdb9"
    ),
    (
        100000004,
        "44444444-4444-4444-4444-444444444444"
    ),
    (
        100000005,
        "55555555-5555-5555-5555-555555555555"
    ),
]


OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "test_index.bin"
)


def create_test_index():

    records = sorted(
        TEST_RECORDS,
        key=lambda record: record[0]
    )

    header = build_header(len(records))

    with open(
        OUTPUT_FILE,
        "wb"
    ) as f:

        f.write(header)

        for photo_id, observation_uuid in records:

            uuid_bytes = uuid.UUID(
                observation_uuid
            ).bytes

            record = struct.pack(
                ">Q",
                photo_id
            ) + uuid_bytes

            assert len(record) == RECORD_SIZE

            f.write(record)

    print("Created test index:")
    print(OUTPUT_FILE)
    print(f"Records: {len(records)}")


if __name__ == "__main__":
    create_test_index()