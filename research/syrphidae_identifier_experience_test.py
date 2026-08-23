import csv
import time
from collections import defaultdict

import requests


HISTORY_FILE = (
    "research/"
    "syrphidae_pilot_500_history.csv"
)

IDENTIFICATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_identifications_all.csv"
)

TAXON_ID = 49995
SAMPLE_PER_GROUP = 10
REQUEST_DELAY = 1.0

API_URL = (
    "https://api.inaturalist.org/"
    "v1/identifications"
)


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def api_count(user_id, cutoff):
    params = {
        "user_id": user_id,
        "taxon_id": TAXON_ID,
        "current": "any",
        "d2": cutoff,
        "per_page": 1,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    time.sleep(REQUEST_DELAY)

    return data["total_results"]


def main():
    history = load_csv(
        HISTORY_FILE
    )

    identifications = load_csv(
        IDENTIFICATIONS_FILE
    )

    by_observation = defaultdict(list)

    for identification in identifications:
        by_observation[
            identification["observation_id"]
        ].append(identification)

    selected = []

    for outcome in (
        "species",
        "genus",
        "other",
    ):

        candidates = [
            row
            for row in history
            if row["outcome_group"] == outcome
            and row["first_external_rank"]
        ]

        selected.extend(
            candidates[:SAMPLE_PER_GROUP]
        )

    print(
        "Selected observations:",
        len(selected)
    )

    print()

    results = []

    for number, hist in enumerate(
        selected,
        start=1
    ):

        obs_id = hist["observation_id"]

        ids = sorted(
            [
                x
                for x in by_observation[obs_id]
                if x["own_observation"] != "True"
            ],
            key=lambda x: x["created_at"]
        )

        first_external = ids[0]

        user_id = (
            first_external[
                "identifier_user_id"
            ]
        )

        user_login = (
            first_external[
                "identifier_login"
            ]
        )

        created_at = (
            first_external["created_at"]
        )

        print(
            f"{number:2d}/"
            f"{len(selected)}  "
            f"Observation {obs_id}  "
            f"{hist['outcome_group']}  "
            f"{user_login}"
        )

        total_at_time = api_count(
            user_id,
            created_at
        )

        prior_count = max(
            0,
            total_at_time - 1
        )

        results.append(
            {
                "observation_id":
                    obs_id,

                "outcome":
                    hist[
                        "outcome_group"
                    ],

                "identifier_user_id":
                    user_id,

                "identifier_login":
                    user_login,

                "identification_time":
                    created_at,

                "first_external_rank":
                    first_external[
                        "taxon_rank"
                    ],

                "prior_syrphidae_ids":
                    prior_count,
            }
        )

    print()
    print("RESULTS")
    print()

    for row in results:
        print(
            f"{row['outcome']:<7}  "
            f"{row['identifier_login']:<25} "
            f"rank={row['first_external_rank']:<10} "
            f"prior Syrphidae IDs="
            f"{row['prior_syrphidae_ids']:,}"
        )


if __name__ == "__main__":
    main()