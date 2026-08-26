import argparse
import csv
import json
import os
import re
import time
from collections import defaultdict

import requests

DATA_DIR = "research/data"
CACHE_DIR = "research/cache"

API_URL = (
    "https://api.inaturalist.org/"
    "v1/identifications"
)

REQUEST_DELAY = 1.0



def api_get(url, params, max_attempts=8):
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=90,
                headers={
                    "User-Agent":
                        "inatlookup-research-pilot"
                },
            )
        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            if attempt == max_attempts:
                raise

            wait_seconds = min(
                60,
                5 * (2 ** (attempt - 1))
            )

            print(
                f"    Network error "
                f"({type(exc).__name__}). "
                f"Retrying in {wait_seconds} "
                "seconds..."
            )

            time.sleep(wait_seconds)
            continue

        if response.status_code == 429:
            retry_after = response.headers.get(
                "Retry-After"
            )

            wait_seconds = 0

            if retry_after:
                try:
                    wait_seconds = float(
                        retry_after
                    )
                except ValueError:
                    pass

            if wait_seconds <= 0:
                wait_seconds = min(
                    60,
                    5 * attempt
                )

            print(
                f"    API throttled (429). "
                f"Waiting {wait_seconds:.0f} "
                "seconds before retry..."
            )

            time.sleep(wait_seconds)
            continue

        response.raise_for_status()

        data = response.json()

        # Deliberately conservative because this
        # script can issue hundreds of requests.
        time.sleep(1.5)

        return data

    raise RuntimeError(
        "API request failed after "
        f"{max_attempts} attempts: "
        f"{url} {params}"
    )




def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Calculate historical taxon-specific "
            "identifier experience for a pilot sample."
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


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(
            csv.DictReader(f)
        )


def load_cache(filename):
    if not os.path.exists(filename):
        return {}

    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def save_cache(
    filename,
    cache
):
    with open(
        filename,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cache,
            f,
            indent=2,
            sort_keys=True
        )


def cache_key(
    user_id,
    created_at
):
    return (
        f"{user_id}|"
        f"{created_at}"
    )


def fetch_prior_experience(
    user_id,
    created_at,
    taxon_id,
    cache,
    cache_file
):
    key = cache_key(
        user_id,
        created_at
    )

    if key in cache:
        return (
            cache[key],
            True
        )

    params = {
        "user_id":
            user_id,

        "taxon_id":
            taxon_id,

        "current":
            "any",

        "d2":
            created_at,

        "per_page":
            1,
    }

    data = api_get(
    	"https://api.inaturalist.org/v1/identifications",
    	params,
    )

    total_at_time = (
        data["total_results"]
    )

    prior_count = max(
        0,
        total_at_time - 1
    )

    cache[key] = prior_count

    save_cache(
        cache_file,
        cache
    )

    time.sleep(
        REQUEST_DELAY
    )

    return (
        prior_count,
        False
    )


def main():
    args = parse_args()

    slug = slugify(
        args.taxon_name
    )

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    os.makedirs(
        CACHE_DIR,
        exist_ok=True
    )

    observations_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"enriched.csv"
    )

    identifications_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"identifications_all.csv"
    )

    cache_file = os.path.join(
        CACHE_DIR,
        f"{args.taxon_id}_"
        f"identifier_experience.json"
    )

    output_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"identifier_experience.csv"
    )

    if not os.path.exists(
        observations_file
    ):
        raise RuntimeError(
            "Enriched observation file "
            f"not found: {observations_file}"
        )

    if not os.path.exists(
        identifications_file
    ):
        raise RuntimeError(
            "Identification file "
            f"not found: "
            f"{identifications_file}"
        )

    observations = load_csv(
        observations_file
    )

    identifications = load_csv(
        identifications_file
    )

    cache = load_cache(
        cache_file
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
        len(observations)
    )

    external_ids = [
        row
        for row in identifications
        if row[
            "own_observation"
        ] != "True"
    ]

    print(
        "Historical external IDs:",
        len(external_ids)
    )

    unique_queries = {
        cache_key(
            row[
                "identifier_user_id"
            ],
            row[
                "created_at"
            ]
        )
        for row in external_ids
        if (
            row[
                "identifier_user_id"
            ]
            and row[
                "created_at"
            ]
        )
    }

    already_cached = sum(
        key in cache
        for key in unique_queries
    )

    print(
        "Unique experience queries:",
        len(unique_queries)
    )

    print(
        "Already cached:",
        already_cached
    )

    experience_by_identification = {}

    total = len(
        external_ids
    )

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
                args.taxon_id,
                cache,
                cache_file
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

    by_observation = defaultdict(
        list
    )

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

        enriched = {
            **identification,

            "prior_taxon_ids":
                experience_by_identification[
                    identification_id
                ],
        }

        by_observation[
            identification[
                "observation_id"
            ]
        ].append(
            enriched
        )

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
            key=lambda row:
                row["created_at"]
        )

        if ids:

            first_external = (
                ids[0]
            )

            most_experienced = max(
                ids,
                key=lambda row:
                    row[
                        "prior_taxon_ids"
                    ]
            )

            first_experience = (
                first_external[
                    "prior_taxon_ids"
                ]
            )

            max_experience = (
                most_experienced[
                    "prior_taxon_ids"
                ]
            )

            zero_experience_count = sum(
                row[
                    "prior_taxon_ids"
                ] == 0
                for row in ids
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

                "first_external_prior_taxon_ids":
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

                "max_prior_taxon_ids":
                    max_experience,

                "zero_experience_external_ids":
                    zero_experience_count,
            }
        )

    with open(
        output_file,
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
        output_file
    )


if __name__ == "__main__":
    main()