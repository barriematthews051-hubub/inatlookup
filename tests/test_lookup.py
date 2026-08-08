import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from lookup import InatLookup
from inatlookup import extract_photo_id


BIN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "inatlookup.bin"
)


KNOWN_PHOTO_ID = 455606536
KNOWN_UUID = "9bcb94d0-cf6f-4ab0-9c5b-7301685acdb9"


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


if __name__ == "__main__":

    test_known_photo()
    test_missing_photo()
    test_photo_id_input()
    test_photo_url_input()
    test_invalid_input()

    print("All tests passed")