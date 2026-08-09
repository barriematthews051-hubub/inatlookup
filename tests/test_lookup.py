import os
import sys
import tempfile
import csv

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from lookup import InatLookup
from inatlookup import (
    extract_photo_id,
    batch_lookup,
    write_batch_csv
)


BIN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "inatlookup.bin"
)


KNOWN_PHOTO_ID = 455606536
KNOWN_UUID = "9bcb94d0-cf6f-4ab0-9c5b-7301685acdb9"


class CountingLookup:
    def __init__(self):
        self.calls = 0

    def find(self, photo_id):
        self.calls += 1

        if photo_id == KNOWN_PHOTO_ID:
            return KNOWN_UUID

        return None


def test_known_photo():

    lookup = InatLookup(BIN_FILE)

    result = lookup.find(KNOWN_PHOTO_ID)

    assert result == KNOWN_UUID

    lookup.close()

    print("PASS: known photo lookup")


def test_missing_photo():

    lookup = InatLookup(BIN_FILE)

    result = lookup.find(999999999999)

    assert result is None

    lookup.close()

    print("PASS: missing photo lookup")


def test_photo_id_input():

    result = extract_photo_id("455606536")

    assert result == 455606536

    print("PASS: photo ID input")


def test_photo_url_input():

    url = (
        "https://static.inaturalist.org/"
        "photos/455606536/original.jpeg"
    )

    result = extract_photo_id(url)

    assert result == 455606536

    print("PASS: photo URL input")


def test_invalid_input():

    result = extract_photo_id("banana")

    assert result is None

    print("PASS: invalid input")


def test_batch_lookup():

    input_text = (
        "455606536\n"
        "\n"
        "999999999999\n"
        "banana\n"
        "455606536\n"
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        input_file = os.path.join(
            temp_dir,
            "photos.txt"
        )

        output_file = os.path.join(
            temp_dir,
            "results.csv"
        )

        with open(
            input_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(input_text)

        lookup = InatLookup(BIN_FILE)

        result = batch_lookup(
            lookup,
            input_file
        )

        lookup.close()

        assert result.total == 4
        assert result.valid == 3
        assert result.invalid == 1
        assert result.unique_photos == 2
        assert result.index_lookups == 2
        assert result.found == 2
        assert result.not_found == 1
        assert result.unique_observations == 1

        assert len(result.rows) == 4

        assert result.rows[0]["input"] == "455606536"
        assert result.rows[0]["photo_id"] == 455606536
        assert result.rows[0]["observation_uuid"] == KNOWN_UUID
        assert result.rows[0]["status"] == "found"

        assert result.rows[1]["input"] == "999999999999"
        assert result.rows[1]["photo_id"] == 999999999999
        assert result.rows[1]["observation_uuid"] == ""
        assert result.rows[1]["status"] == "not found"

        assert result.rows[2]["input"] == "banana"
        assert result.rows[2]["photo_id"] == ""
        assert result.rows[2]["observation_uuid"] == ""
        assert result.rows[2]["status"] == "invalid input"

        assert result.rows[3]["input"] == "455606536"
        assert result.rows[3]["photo_id"] == 455606536
        assert result.rows[3]["observation_uuid"] == KNOWN_UUID
        assert result.rows[3]["status"] == "found"

        write_batch_csv(
            result,
            output_file
        )

        with open(
            output_file,
            "r",
            encoding="utf-8",
            newline=""
        ) as f:

            rows = list(csv.DictReader(f))

        assert len(rows) == 4

        assert rows[0]["input"] == "455606536"
        assert rows[0]["photo_id"] == "455606536"
        assert rows[0]["observation_uuid"] == KNOWN_UUID
        assert rows[0]["status"] == "found"

        assert rows[1]["input"] == "999999999999"
        assert rows[1]["photo_id"] == "999999999999"
        assert rows[1]["observation_uuid"] == ""
        assert rows[1]["status"] == "not found"

        assert rows[2]["input"] == "banana"
        assert rows[2]["photo_id"] == ""
        assert rows[2]["observation_uuid"] == ""
        assert rows[2]["status"] == "invalid input"

        assert rows[3]["input"] == "455606536"
        assert rows[3]["photo_id"] == "455606536"
        assert rows[3]["observation_uuid"] == KNOWN_UUID
        assert rows[3]["status"] == "found"

    print("PASS: batch result object and cache")


def test_duplicate_cache():

    input_text = (
        "455606536\n"
        "455606536\n"
        "455606536\n"
        "999999999999\n"
        "999999999999\n"
    )

    with tempfile.TemporaryDirectory() as temp_dir:

        input_file = os.path.join(
            temp_dir,
            "photos.txt"
        )

        with open(
            input_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(input_text)

        lookup = CountingLookup()

        result = batch_lookup(
            lookup,
            input_file
        )

        assert result.total == 5
        assert result.valid == 5
        assert result.invalid == 0
        assert result.unique_photos == 2
        assert result.index_lookups == 2
        assert result.found == 3
        assert result.not_found == 2
        assert result.unique_observations == 1

        assert lookup.calls == 2

        print("PASS: duplicate lookup cache")


def test_lookup_context_manager():

    with InatLookup(BIN_FILE) as lookup:

        result = lookup.find(KNOWN_PHOTO_ID)

        assert result == KNOWN_UUID
        assert not lookup.f.closed

    assert lookup.f.closed

    print("PASS: lookup context manager")


if __name__ == "__main__":

    test_known_photo()
    test_missing_photo()
    test_photo_id_input()
    test_photo_url_input()
    test_invalid_input()
    test_batch_lookup()
    test_duplicate_cache()
    test_lookup_context_manager()

    print("All tests passed")