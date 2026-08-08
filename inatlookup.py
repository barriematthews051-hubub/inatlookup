import os
import re
import argparse
import csv
import requests
from dataclasses import dataclass

from lookup import InatLookup
from version import VERSION


DEFAULT_INDEX = os.path.join(
    os.path.dirname(__file__),
    "data",
    "inatlookup.bin"
)

DEFAULT_OUTPUT = "inatlookup_results.csv"


@dataclass
class BatchResult:
    total: int
    valid: int
    invalid: int
    unique_photos: int
    found: int
    not_found: int
    unique_observations: int
    rows: list


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


def batch_lookup(lookup, input_file):
    """
    Look up photo IDs from a text file.

    Returns a BatchResult containing statistics and output rows.
    """

    total = 0
    valid = 0
    invalid = 0
    found = 0
    not_found = 0

    unique_photo_ids = set()
    observations = set()

    rows = []

    with open(
        input_file,
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            text = line.strip()

            if not text:
                continue

            total += 1

            photo_id = extract_photo_id(text)

            if photo_id is None:

                invalid += 1

                rows.append(
                    {
                        "input": text,
                        "photo_id": "",
                        "observation_uuid": "",
                        "status": "invalid input"
                    }
                )

                continue

            valid += 1
            unique_photo_ids.add(photo_id)

            obs_uuid = lookup.find(photo_id)

            if obs_uuid is None:

                not_found += 1

                rows.append(
                    {
                        "input": text,
                        "photo_id": photo_id,
                        "observation_uuid": "",
                        "status": "not found"
                    }
                )

                continue

            found += 1
            observations.add(obs_uuid)

            rows.append(
                {
                    "input": text,
                    "photo_id": photo_id,
                    "observation_uuid": obs_uuid,
                    "status": "found"
                }
            )

    return BatchResult(
        total=total,
        valid=valid,
        invalid=invalid,
        unique_photos=len(unique_photo_ids),
        found=found,
        not_found=not_found,
        unique_observations=len(observations),
        rows=rows
    )


def write_batch_csv(result, output_file):
    """
    Write a BatchResult to a CSV file.
    """

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "input",
                "photo_id",
                "observation_uuid",
                "status"
            ]
        )

        writer.writeheader()
        writer.writerows(result.rows)


def print_batch_summary(result, output_file):
    """
    Display a BatchResult summary.
    """

    print()
    print("Batch lookup complete")
    print()
    print(f"Input records      : {result.total:,}")
    print(f"Valid inputs       : {result.valid:,}")
    print(f"Invalid input      : {result.invalid:,}")
    print(f"Unique photos      : {result.unique_photos:,}")
    print(f"Found in index     : {result.found:,}")
    print(f"Not found          : {result.not_found:,}")
    print(f"Unique observations: {result.unique_observations:,}")
    print()
    print("Results written to:")
    print(output_file)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Find iNaturalist observations from "
            "photo IDs or photo URLs."
        )
    )

    parser.add_argument(
        "photo",
        nargs="?",
        help=(
            "iNaturalist photo ID, photo URL, "
            "or input text file"
        )
    )

    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX,
        help="Path to inatlookup index file"
    )

    parser.add_argument(
        "--output",
        "-o",
        default=DEFAULT_OUTPUT,
        help="Output CSV filename for batch mode"
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

    # No argument: interactive mode
    if not args.photo:

        while True:

            text = input(
                "Photo URL or Photo ID (blank to quit): "
            ).strip()

            if not text:
                break

            lookup_photo(lookup, text)

            print()

        lookup.close()
        return

    # File argument: batch mode
    if os.path.isfile(args.photo):

        result = batch_lookup(
            lookup,
            args.photo
        )

        write_batch_csv(
            result,
            args.output
        )

        print_batch_summary(
            result,
            args.output
        )

        lookup.close()
        return

    # Otherwise: single-photo mode
    lookup_photo(lookup, args.photo)

    lookup.close()


if __name__ == "__main__":
    main()