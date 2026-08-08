import os
import re
import argparse
import requests

from lookup import InatLookup
from version import VERSION


DEFAULT_INDEX = os.path.join(
    os.path.dirname(__file__),
    "data",
    "inatlookup.bin"
)


def extract_photo_id(text):
    """
    Extract a numeric iNaturalist photo ID from either
    a plain photo ID or an iNaturalist photo URL.
    """

    text = text.strip()

    if text.isdigit():
        return int(text)

    match = re.search(r"/photos/(\d+)", text)

    if match:
        return int(match.group(1))

    return None


def lookup_photo(lookup, text):
    """
    Look up one photo and display the result.
    """

    photo_id = extract_photo_id(text)

    if photo_id is None:
        print("Couldn't find a valid iNaturalist photo ID.")
        return

    print("Photo ID:", photo_id)

    obs_uuid = lookup.find(photo_id)

    if obs_uuid is None:
        print("Photo not found in index.")
        return

    print("Observation UUID:", obs_uuid)

    try:

        r = requests.get(
            "https://api.inaturalist.org/v1/observations",
            params={
                "uuid": obs_uuid,
                "per_page": 1
            },
            timeout=30
        )

        r.raise_for_status()

        results = r.json()["results"]

        if results:

            obs = results[0]

            print()
            print("Observation ID :", obs["id"])
            print("Observation URL:", obs["uri"])

        else:

            print(
                "UUID found, but observation was not returned by the API."
            )

    except requests.RequestException as e:

        print("API lookup failed.")
        print(e)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Find an iNaturalist observation from a "
            "photo ID or photo URL."
        )
    )

    parser.add_argument(
        "photo",
        nargs="?",
        help="iNaturalist photo ID or photo URL"
    )

    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX,
        help="Path to inatlookup index file"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"iNatLookup {VERSION}"
    )

    parser.add_argument(
        "--info",
        action="store_true",
        help="Display index information and exit"
    )

    args = parser.parse_args()

    if not os.path.exists(args.index):

        print("Index file not found:")
        print(args.index)
        return

    lookup = InatLookup(args.index)

    if args.info:

        print(f"iNatLookup {VERSION}")
        print(f"Index format v{lookup.version}")
        print(f"Records : {lookup.records:,}")

        lookup.close()
        return

    print(f"iNatLookup program v{VERSION}")
    print(f"Index format v{lookup.version}")
    print(f"Records : {lookup.records:,}")
    print()

    # Direct command-line lookup
    if args.photo:

        lookup_photo(lookup, args.photo)
        lookup.close()
        return

    # Interactive mode
    while True:

        text = input(
            "Photo URL or Photo ID (blank to quit): "
        ).strip()

        if not text:
            break

        lookup_photo(lookup, text)

        print()

    lookup.close()


if __name__ == "__main__":
    main()