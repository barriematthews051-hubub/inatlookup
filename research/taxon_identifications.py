import argparse
import csv
import math
import os
import re
import time

import requests


API_URL = (
    "https://api.inaturalist.org/"
    "v1/identifications"
)

DATA_DIR = "research/data"

OBSERVATIONS_PER_BATCH = 100
PER_PAGE = 200
REQUEST_DELAY = 1.0


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Download complete historical "
            "identification records for a "
            "taxon pilot sample."
        )
    )

    parser.add_argument(
        "--taxon-id",
        type=int,
        required=True,
        help="iNaturalist taxon ID.",
    )

    parser.add_argument(
        "--taxon-name",
        required=True,
        help="Taxon name, e.g. Syrphidae.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=500,
        help="Pilot sample size. Default: 500.",
    )

    return parser.parse_args()


def slugify(text):
    text = text.strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    )

    return text.strip("_")


def load_observation_ids(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        return [
            int(row["observation_id"])
            for row in reader
        ]


def api_get(params):
    response = requests.get(
        API_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    time.sleep(
        REQUEST_DELAY
    )

    return data


def extract_row(identification):
    user = (
        identification.get("user")
        or {}
    )

    taxon = (
        identification.get("taxon")
        or {}
    )

    observation = (
        identification.get(
            "observation"
        )
        or {}
    )

    return {
        "observation_id":
            observation.get(
                "id",
                ""
            ),

        "identification_id":
            identification.get(
                "id",
                ""
            ),

        "identification_uuid":
            identification.get(
                "uuid",
                ""
            ),

        "identifier_user_id":
            user.get(
                "id",
                ""
            ),

        "identifier_login":
            user.get(
                "login",
                ""
            ),

        "created_at":
            identification.get(
                "created_at",
                ""
            ),

        "taxon_id":
            identification.get(
                "taxon_id",
                ""
            ),

        "taxon_rank":
            taxon.get(
                "rank",
                ""
            ),

        "category":
            identification.get(
                "category",
                ""
            ),

        "current":
            identification.get(
                "current",
                ""
            ),

        "own_observation":
            identification.get(
                "own_observation",
                ""
            ),

        "vision":
            identification.get(
                "vision",
                ""
            ),

        "disagreement":
            identification.get(
                "disagreement",
                ""
            ),

        "previous_observation_taxon_id":
            identification.get(
                "previous_observation_taxon_id",
                ""
            ),

        "current_taxon":
            identification.get(
                "current_taxon",
                ""
            ),

        "hidden":
            identification.get(
                "hidden",
                ""
            ),
    }


def fetch_batch(observation_ids):
    ids_text = ",".join(
        str(x)
        for x in observation_ids
    )

    first_page = api_get(
        {
            "observation_id":
                ids_text,

            "current":
                "any",

            "per_page":
                PER_PAGE,

            "page":
                1,
        }
    )

    total = (
        first_page["total_results"]
    )

    rows = [
        extract_row(x)
        for x in first_page[
            "results"
        ]
    ]

    pages = math.ceil(
        total / PER_PAGE
    )

    print(
        "  Identifications:",
        total
    )

    print(
        "  Pages:",
        pages
    )

    for page in range(
        2,
        pages + 1
    ):

        print(
            f"  Fetching page "
            f"{page}/{pages}"
        )

        data = api_get(
            {
                "observation_id":
                    ids_text,

                "current":
                    "any",

                "per_page":
                    PER_PAGE,

                "page":
                    page,
            }
        )

        rows.extend(
            extract_row(x)
            for x in data[
                "results"
            ]
        )

    return rows


def main():
    args = parse_args()

    slug = slugify(
        args.taxon_name
    )

    input_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}.csv"
    )

    output_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"identifications_all.csv"
    )

    if not os.path.exists(
        input_file
    ):
        raise RuntimeError(
            f"Pilot file not found: "
            f"{input_file}"
        )

    observation_ids = (
        load_observation_ids(
            input_file
        )
    )

    print(
        "Taxon:",
        args.taxon_name
    )

    print(
        "Taxon ID:",
        args.taxon_id
    )

    print(
        "Observations:",
        len(observation_ids)
    )

    batches = [
        observation_ids[
            i:
            i + OBSERVATIONS_PER_BATCH
        ]
        for i in range(
            0,
            len(observation_ids),
            OBSERVATIONS_PER_BATCH
        )
    ]

    print(
        "Batches:",
        len(batches)
    )

    all_rows = []

    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        print()
        print(
            f"Batch "
            f"{batch_number}/"
            f"{len(batches)}"
        )

        rows = fetch_batch(
            batch
        )

        all_rows.extend(
            rows
        )

    fieldnames = [
        "observation_id",
        "identification_id",
        "identification_uuid",
        "identifier_user_id",
        "identifier_login",
        "created_at",
        "taxon_id",
        "taxon_rank",
        "category",
        "current",
        "own_observation",
        "vision",
        "disagreement",
        "previous_observation_taxon_id",
        "current_taxon",
        "hidden",
    ]

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(
            all_rows
        )

    current_count = sum(
        row["current"] is True
        for row in all_rows
    )

    non_current_count = sum(
        row["current"] is False
        for row in all_rows
    )

    represented = {
        str(
            row["observation_id"]
        )
        for row in all_rows
        if row["observation_id"]
        != ""
    }

    print()
    print(
        "Identification extraction complete"
    )

    print(
        "Identification rows:",
        len(all_rows)
    )

    print(
        "Current IDs:",
        current_count
    )

    print(
        "Non-current IDs:",
        non_current_count
    )

    print(
        "Observations represented:",
        len(represented)
    )

    print(
        "Output:",
        output_file
    )


if __name__ == "__main__":
    main()