import os
import sys
import tempfile
import csv
import struct
import requests
from unittest.mock import patch

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from lookup import InatLookup
from header import build_header

from inatlookup import (
    extract_photo_id,
    batch_lookup,
    write_batch_csv,
    lookup_observation_api
)


BIN_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "test_index.bin"
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


def test_api_lookup_success():

    fake_response = {
        "results": [
            {
                "id": 254368720,
                "uri": "https://www.inaturalist.org/observations/254368720"
            }
        ]
    }

    with patch(
        "inatlookup.requests.get"
    ) as mock_get:

        mock_get.return_value.json.return_value = fake_response
        mock_get.return_value.raise_for_status.return_value = None

        result = lookup_observation_api(
            KNOWN_UUID
        )

    assert result["observation_id"] == 254368720

    assert result["observation_url"] == (
        "https://www.inaturalist.org/observations/254368720"
    )

    mock_get.assert_called_once()

    print("PASS: API lookup success")

def test_api_lookup_failure():

    with patch(
        "inatlookup.requests.get"
    ) as mock_get:

        mock_get.side_effect = requests.RequestException(
            "Test API failure"
        )

        result = lookup_observation_api(
            KNOWN_UUID
        )

    assert result is None

    mock_get.assert_called_once()

    print("PASS: API lookup failure")

def test_batch_api_enrichment():

    input_text = (
        "455606536\n"
        "455606536\n"
        "999999999999\n"
    )

    fake_api_result = {
        "observation_id": 254368720,
        "observation_url":
            "https://www.inaturalist.org/observations/254368720"
    }

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

        with patch(
            "inatlookup.lookup_observation_api"
        ) as mock_api:

            mock_api.return_value = fake_api_result

            result = batch_lookup(
                lookup,
                input_file,
                use_api=True
            )

        assert result.total == 3
        assert result.valid == 3
        assert result.invalid == 0
        assert result.unique_photos == 2
        assert result.index_lookups == 2
        assert result.found == 2
        assert result.not_found == 1
        assert result.unique_observations == 1

        assert result.api_lookups == 1
        assert result.api_successes == 1
        assert result.api_failures == 0

        assert lookup.calls == 2

        assert mock_api.call_count == 1

        assert result.rows[0]["observation_id"] == 254368720
        assert result.rows[0]["observation_url"] == (
            "https://www.inaturalist.org/observations/254368720"
        )

        assert result.rows[1]["observation_id"] == 254368720
        assert result.rows[1]["observation_url"] == (
            "https://www.inaturalist.org/observations/254368720"
        )

        assert result.rows[2]["observation_id"] == ""
        assert result.rows[2]["observation_url"] == ""

    print("PASS: batch API enrichment")


def test_api_csv_output():

    result = type(
        "TestResult",
        (),
        {
            "rows": [
                {
                    "input": "455606536",
                    "photo_id": 455606536,
                    "observation_uuid": KNOWN_UUID,
                    "status": "found",
                    "observation_id": 254368720,
                    "observation_url":
                        "https://www.inaturalist.org/observations/254368720"
                }
            ]
        }
    )()

    with tempfile.TemporaryDirectory() as temp_dir:

        output_file = os.path.join(
            temp_dir,
            "results.csv"
        )

        write_batch_csv(
            result,
            output_file,
            include_api=True
        )

        with open(
            output_file,
            "r",
            encoding="utf-8",
            newline=""
        ) as f:

            rows = list(csv.DictReader(f))

        assert len(rows) == 1

        assert rows[0]["input"] == "455606536"
        assert rows[0]["photo_id"] == "455606536"
        assert rows[0]["observation_uuid"] == KNOWN_UUID
        assert rows[0]["status"] == "found"
        assert rows[0]["observation_id"] == "254368720"
        assert rows[0]["observation_url"] == (
            "https://www.inaturalist.org/observations/254368720"
        )

    print("PASS: API CSV output")


def test_lookup_context_manager():

    with InatLookup(BIN_FILE) as lookup:

        result = lookup.find(KNOWN_PHOTO_ID)

        assert result == KNOWN_UUID
        assert not lookup.f.closed

    assert lookup.f.closed

    print("PASS: lookup context manager")


def test_valid_index_exact_length():

    expected_size = 128 + (5 * 24)

    assert os.path.getsize(BIN_FILE) == expected_size

    with InatLookup(BIN_FILE) as lookup:
        assert lookup.records == 5

    print("PASS: valid index exact length")


def test_truncated_final_record():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name
        f.write(build_header(1))
        f.write(b"\0" * 23)

    try:

        try:
            InatLookup(filename)
            assert False, "Expected index size error"

        except RuntimeError as e:
            assert str(e) == (
                "Index file size does not match header: "
                "expected 152 bytes, found 151 bytes."
            )

    finally:

        os.remove(filename)

    print("PASS: truncated final record")


def test_file_shorter_than_declared_record_count():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name
        f.write(build_header(2))
        f.write(b"\0" * 24)

    try:

        try:
            InatLookup(filename)
            assert False, "Expected index size error"

        except RuntimeError as e:
            assert str(e) == (
                "Index file size does not match header: "
                "expected 176 bytes, found 152 bytes."
            )

    finally:

        os.remove(filename)

    print("PASS: file shorter than declared record count")


def test_file_longer_than_declared_record_count():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name
        f.write(build_header(1))
        f.write(b"\0" * 25)

    try:

        try:
            InatLookup(filename)
            assert False, "Expected index size error"

        except RuntimeError as e:
            assert str(e) == (
                "Index file size does not match header: "
                "expected 152 bytes, found 153 bytes."
            )

    finally:

        os.remove(filename)

    print("PASS: file longer than declared record count")


def test_invalid_magic():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name
        f.write(b"NOTVALID" + (b"\0" * 120))

    try:

        try:
            InatLookup(filename)
            assert False, "Expected invalid magic error"

        except RuntimeError as e:
            assert str(e) == "Not a valid inatlookup index."

    finally:

        os.remove(filename)

    print("PASS: invalid magic")


def test_incomplete_header():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name
        f.write(b"INATLOOK")

    try:

        try:
            InatLookup(filename)
            assert False, "Expected incomplete header error"

        except RuntimeError as e:
            assert str(e) == "Header is incomplete."

    finally:

        os.remove(filename)

    print("PASS: incomplete header")


def test_zero_record_index():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name
        f.write(build_header(0))

    try:

        with InatLookup(filename) as lookup:
            assert lookup.records == 0
            assert lookup.find(KNOWN_PHOTO_ID) is None

    finally:

        os.remove(filename)

    print("PASS: zero-record index")


def test_invalid_header_version():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name

        header = bytearray(128)

        header[0:8] = b"INATLOOK"

        struct.pack_into(
            "<I",
            header,
            8,
            999
        )

        f.write(header)

    try:

        try:
            InatLookup(filename)
            assert False, "Expected unsupported version error"

        except RuntimeError as e:
            assert str(e) == (
                "Unsupported index format version: 999"
            )

    finally:

        os.remove(filename)

    print("PASS: invalid header version")


def test_invalid_record_size():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name

        header = bytearray(128)

        header[0:8] = b"INATLOOK"

        struct.pack_into(
            "<I",
            header,
            8,
            1
        )

        struct.pack_into(
            "<I",
            header,
            24,
            999
        )

        f.write(header)

    try:

        try:
            InatLookup(filename)
            assert False, "Expected unsupported record size error"

        except RuntimeError as e:
            assert str(e) == (
                "Unsupported record size: 999"
            )

    finally:

        os.remove(filename)

    print("PASS: invalid record size")


def test_invalid_header_size():

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        delete=False
    ) as f:

        filename = f.name

        header = bytearray(128)

        header[0:8] = b"INATLOOK"

        struct.pack_into(
            "<I",
            header,
            8,
            1
        )

        struct.pack_into(
            "<I",
            header,
            24,
            24
        )

        struct.pack_into(
            "<I",
            header,
            28,
            999
        )

        f.write(header)

    try:

        try:
            InatLookup(filename)
            assert False, "Expected unsupported header size error"

        except RuntimeError as e:
            assert str(e) == (
                "Unsupported header size: 999"
            )

    finally:

        os.remove(filename)

    print("PASS: invalid header size")


if __name__ == "__main__":

    test_known_photo()
    test_missing_photo()
    test_photo_id_input()
    test_photo_url_input()
    test_invalid_input()
    test_batch_lookup()
    test_duplicate_cache()
    test_api_lookup_success()
    test_api_lookup_failure()
    test_batch_api_enrichment()
    test_api_csv_output()
    test_lookup_context_manager()
    test_valid_index_exact_length()
    test_truncated_final_record()
    test_file_shorter_than_declared_record_count()
    test_file_longer_than_declared_record_count()
    test_invalid_magic()
    test_incomplete_header()
    test_zero_record_index()
    test_invalid_header_version()
    test_invalid_record_size()
    test_invalid_header_size()

print("All tests passed")
