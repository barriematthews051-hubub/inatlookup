import csv
import math
import time

import requests


INPUT_FILE = "research/syrphidae_pilot_500.csv"

OUTPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_identifications_all.csv"
)

API_URL = (
    "https://api.inaturalist.org/"
    "v1/identifications"
)

OBSERVATIONS_PER_BATCH = 100
PER_PAGE = 200
REQUEST_DELAY = 1.0


def load_observation_ids():
    with open(
        INPUT_FILE,
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

    time.sleep(REQUEST_DELAY)

    return data


def extract_row(identification):
    user = identification.get("user") or {}
    taxon = identification.get("taxon") or {}
    observation = (
        identification.get("observation")
        or {}
    )

    return {
        "observation_id": observation.get(
            "id",
            ""
        ),
        "identification_id": identification.get(
            "id",
            ""
        ),
        "identification_uuid": identification.get(
            "uuid",
            ""
        ),
        "identifier_user_id": user.get(
            "id",
            ""
        ),
        "identifier_login": user.get(
            "login",
            ""
        ),
        "created_at": identification.get(
            "created_at",
            ""
        ),
        "taxon_id": identification.get(
            "taxon_id",
            ""
        ),
        "taxon_rank": taxon.get(
            "rank",
            ""
        ),
        "category": identification.get(
            "category",
            ""
        ),
        "current": identification.get(
            "current",
            ""
        ),
        "own_observation": identification.get(
            "own_observation",
            ""
        ),
        "vision": identification.get(
            "vision",
            ""
        ),
        "disagreement": identification.get(
            "disagreement",
            ""
        ),
        "previous_observation_taxon_id":
            identification.get(
                "previous_observation_taxon_id",
                ""
            ),
        "current_taxon": identification.get(
            "current_taxon",
            ""
        ),
        "hidden": identification.get(
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
            "observation_id": ids_text,
	    "current": "any",
            "per_page": PER_PAGE,
            "page": 1,
        }
    )

    total = first_page["total_results"]

    rows = [
        extract_row(x)
        for x in first_page["results"]
    ]

    pages = math.ceil(
        total / PER_PAGE
    )

    print(
        f"  Identifications: {total}"
    )
    print(
        f"  Pages: {pages}"
    )

    for page in range(2, pages + 1):

        print(
            f"  Fetching page "
            f"{page}/{pages}"
        )

        data = api_get(
            {
                "observation_id": ids_text,
		"current": "any",
                "per_page": PER_PAGE,
                "page": page,
            }
        )

        rows.extend(
            extract_row(x)
            for x in data["results"]
        )

    return rows


def main():
    observation_ids = (
        load_observation_ids()
    )

    print(
        "Observations:",
        len(observation_ids)
    )

    all_rows = []

    batches = [
        observation_ids[i:i + OBSERVATIONS_PER_BATCH]
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

    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        print()
        print(
            f"Batch {batch_number}/"
            f"{len(batches)}"
        )

        rows = fetch_batch(batch)

        all_rows.extend(rows)

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
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(all_rows)

    print()
    print(
        "Identification extraction complete"
    )
    print(
        "Observations:",
        len(observation_ids)
    )
    print(
        "Identification rows:",
        len(all_rows)
    )
    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()