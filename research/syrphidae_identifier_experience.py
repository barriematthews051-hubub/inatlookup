import csv
import json
import os
import time
from collections import defaultdict

import requests


OBSERVATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_enriched.csv"
)

IDENTIFICATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_identifications_all.csv"
)

CACHE_FILE = (
    "research/"
    "syrphidae_identifier_experience_cache.json"
)

OUTPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_identifier_experience.csv"
)

TAXON_ID = 49995

API_URL = (
    "https://api.inaturalist.org/"
    "v1/identifications"
)

REQUEST_DELAY = 1.0


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_cache(cache):
    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            cache,
            f,
            indent=2,
            sort_keys=True
        )


def cache_key(user_id, created_at):
    return (
        f"{user_id}|{created_at}"
    )


def fetch_prior_experience(
    user_id,
    created_at,
    cache
):
    key = cache_key(
        user_id,
        created_at
    )

    if key in cache:
        return cache[key], True

    params = {
        "user_id": user_id,
        "taxon_id": TAXON_ID,
        "current": "any",
        "d2": created_at,
        "per_page": 1,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    total_at_time = (
        data["total_results"]
    )

    prior_count = max(
        0,
        total_at_time - 1
    )

    cache[key] = prior_count

    save_cache(cache)

    time.sleep(
        REQUEST_DELAY
    )

    return prior_count, False


def main():
    observations = load_csv(
        OBSERVATIONS_FILE
    )

    identifications = load_csv(
        IDENTIFICATIONS_FILE
    )

    cache = load_cache()

    print(
        "Observations:",
        len(observations)
    )

    external_ids = [
        x
        for x in identifications
        if x["own_observation"] != "True"
    ]

    print(
        "Historical external IDs:",
        len(external_ids)
    )

    unique_queries = {
        cache_key(
            x["identifier_user_id"],
            x["created_at"]
        )
        for x in external_ids
        if x["identifier_user_id"]
        and x["created_at"]
    }

    print(
        "Unique experience queries:",
        len(unique_queries)
    )

    print(
        "Already cached:",
        sum(
            key in cache
            for key in unique_queries
        )
    )

    experience_by_identification = {}

    total = len(external_ids)

    for number, identification in enumerate(
        external_ids,
        start=1
    ):

        user_id = (
            identification[
                "identifier_user_id"
            ]
        )

        created_at = (
            identification[
                "created_at"
            ]
        )

        if not user_id or not created_at:
            continue

        prior_count, cached = (
            fetch_prior_experience(
                user_id,
                created_at,
                cache
            )
        )

        identification_id = (
            identification[
                "identification_id"
            ]
        )

        experience_by_identification[
            identification_id
        ] = prior_count

        source = (
            "cache"
            if cached
            else "API"
        )

        print(
            f"{number:4d}/"
            f"{total}  "
            f"{identification['identifier_login']:<25} "
            f"{prior_count:8,d}  "
            f"{source}"
        )

    by_observation = defaultdict(list)

    for identification in external_ids:

        identification_id = (
            identification[
                "identification_id"
            ]
        )

        if (
            identification_id
            not in experience_by_identification
        ):
            continue

        item = {
            **identification,
            "prior_syrphidae_ids":
                experience_by_identification[
                    identification_id
                ],
        }

        by_observation[
            identification[
                "observation_id"
            ]
        ].append(item)

    output_rows = []

    for observation in observations:

        observation_id = (
            observation[
                "observation_id"
            ]
        )

        ids = sorted(
            by_observation[
                observation_id
            ],
            key=lambda x:
                x["created_at"]
        )

        if ids:

            first_external = ids[0]

            most_experienced = max(
                ids,
                key=lambda x:
                    x[
                        "prior_syrphidae_ids"
                    ]
            )

            first_experience = (
                first_external[
                    "prior_syrphidae_ids"
                ]
            )

            max_experience = (
                most_experienced[
                    "prior_syrphidae_ids"
                ]
            )

            zero_experience_count = sum(
                x[
                    "prior_syrphidae_ids"
                ] == 0
                for x in ids
            )

        else:

            first_external = None
            most_experienced = None

            first_experience = ""
            max_experience = ""
            zero_experience_count = 0

        output_rows.append(
            {
                "observation_id":
                    observation_id,

                "community_taxon_rank":
                    observation[
                        "community_taxon_rank"
                    ],

                "photo_count":
                    observation[
                        "photo_count"
                    ],

                "project_count":
                    observation[
                        "project_count"
                    ],

                "external_history_count":
                    len(ids),

                "first_external_user_id":
                    (
                        first_external[
                            "identifier_user_id"
                        ]
                        if first_external
                        else ""
                    ),

                "first_external_login":
                    (
                        first_external[
                            "identifier_login"
                        ]
                        if first_external
                        else ""
                    ),

                "first_external_rank":
                    (
                        first_external[
                            "taxon_rank"
                        ]
                        if first_external
                        else ""
                    ),

                "first_external_prior_syrphidae_ids":
                    first_experience,

                "most_experienced_user_id":
                    (
                        most_experienced[
                            "identifier_user_id"
                        ]
                        if most_experienced
                        else ""
                    ),

                "most_experienced_login":
                    (
                        most_experienced[
                            "identifier_login"
                        ]
                        if most_experienced
                        else ""
                    ),

                "most_experienced_rank":
                    (
                        most_experienced[
                            "taxon_rank"
                        ]
                        if most_experienced
                        else ""
                    ),

                "max_prior_syrphidae_ids":
                    max_experience,

                "zero_experience_external_ids":
                    zero_experience_count,
            }
        )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                output_rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )

    print()
    print(
        "Experience enrichment complete"
    )

    print(
        "Output rows:",
        len(output_rows)
    )

    print(
        "Cache entries:",
        len(cache)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()