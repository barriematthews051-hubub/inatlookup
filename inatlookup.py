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


def main():

    parser = argparse.ArgumentParser(
        description="Find iNaturalist observations from photo IDs or URLs."
    )

    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX,
        help="Path to inatlookup index file"
    )

    args = parser.parse_args()

    if not os.path.exists(args.index):
        print("Index file not found:")
        print(args.index)
        return

    lookup = InatLookup(args.index)

    print(f"inatlookup - Fast Reverse Lookup v{VERSION}")
    print(f"Index format v{lookup.version}")
    print(f"Records : {lookup.records:,}")
    print()

    while True:

        text = input(
            "Photo URL or Photo ID (blank to quit): "
        ).strip()

        if not text:
            break

        if text.isdigit():

            photo_id = int(text)

        else:

            m = re.search(
                r"/photos/(\d+)",
                text
            )

            if not m:
                print("Couldn't find a photo ID.")
                continue

            photo_id = int(m.group(1))

        print("Photo ID:", photo_id)

        obs_uuid = lookup.find(photo_id)

        if obs_uuid is None:
            print("Photo not found in index.")
            continue

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
                    "UUID found, but observation not returned."
                )

        except Exception as e:

            print("API lookup failed.")
            print(e)

    lookup.close()


if __name__ == "__main__":
    main()