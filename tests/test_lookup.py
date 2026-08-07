import sys
import os

sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from lookup import InatLookup


#BIN_FILE = "inatlookup.bin"
BIN_FILE = r"C:\Users\Barrie\inatlookup\data\inatlookup.bin"


def test_known_photo():

    lookup = InatLookup(BIN_FILE)

    photo_id = 455606536

    expected = (
        "9bcb94d0-cf6f-4ab0-9c5b-7301685acdb9"
    )

    result = lookup.find(photo_id)

    assert result == expected, (
        f"Expected {expected}, got {result}"
    )

    lookup.close()

    print("PASS: known photo lookup")


def test_missing_photo():

    lookup = InatLookup(BIN_FILE)

    result = lookup.find(999999999999)

    assert result is None

    lookup.close()

    print("PASS: missing photo lookup")


if __name__ == "__main__":

    test_known_photo()
    test_missing_photo()

    print("All tests passed")