import csv
import json
import os
import time

import requests


INPUT_FILE = os.path.join(
    "research",
    "data",
    "family_model_a_dataset.csv",
)

OUTPUT_FILE = os.path.join(
    "research",
    "data",
    "family_identifier_capacity.csv",
)

CACHE_FILE = os.path.join(
    "research",
    "cache",
    "family_identifier_capacity_2024.json",
)

START_DATE = "2024-01-01"
END_DATE = "2024-12-31"

REQUEST_DELAY = 1.25


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def save_cache(cache):
    os.makedirs(
        os.path.dirname(CACHE_FILE),
        exist_ok=True,
    )

    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            cache,
            handle,
            indent=2,
            sort_keys=True,
        )


def api_get(
    url,
    params,
    max_attempts=8,
):
    for attempt in range(
        1,
        max_attempts + 1,
    ):
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
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"    Network error "
                f"({type(exc).__name__}). "
                f"Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        if response.status_code == 429:
            if attempt == max_attempts:
                response.raise_for_status()

            retry_after = (
                response.headers.get(
                    "Retry-After"
                )
            )

            try:
                wait_seconds = float(
                    retry_after
                )
            except (
                TypeError,
                ValueError,
            ):
                wait_seconds = min(
                    60,
                    5 * (2 ** (attempt - 1)),
                )

            print(
                f"    Rate limited. "
                f"Retrying in "
                f"{wait_seconds:.0f} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        response.raise_for_status()

        data = response.json()

        time.sleep(REQUEST_DELAY)

        return data

    raise RuntimeError(
        "API request failed after retries"
    )


def get_identification_count(
    taxon_id,
):
    data = api_get(
        "https://api.inaturalist.org/v1/identifications",
        {
            "taxon_id": taxon_id,
            "d1": START_DATE,
            "d2": END_DATE,
            "current": "any",
            "per_page": 1,
            "page": 1,
        },
    )

    return int(
        data["total_results"]
    )


def get_observation_count(
    taxon_id,
):
    data = api_get(
        "https://api.inaturalist.org/v1/observations",
        {
            "taxon_id": taxon_id,
            "created_d1": START_DATE,
            "created_d2": END_DATE,
            "per_page": 1,
            "page": 1,
        },
    )

    return int(
        data["total_results"]
    )


def load_families():
    rows = []

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            rows.append(
                {
                    "family": row["family"],
                    "taxon_id": int(
                        row["taxon_id"]
                    ),
                }
            )

    return rows


def main():
    families = load_families()
    cache = load_cache()

    results = []

    print()
    print(
        "PRE-2025 IDENTIFIER CAPACITY"
    )
    print(
        "============================"
    )
    print()
    print(
        f"Period: {START_DATE} "
        f"to {END_DATE}"
    )
    print(
        f"Families: {len(families)}"
    )
    print()

    for index, row in enumerate(
        families,
        start=1,
    ):
        family = row["family"]
        taxon_id = row["taxon_id"]

        key = str(taxon_id)

        if key in cache:
            identification_count = int(
                cache[key][
                    "identification_count"
                ]
            )

            observation_count = int(
                cache[key][
                    "observation_count"
                ]
            )

            source = "cache"

        else:
            print(
                f"{index:2}/{len(families)} "
                f"{family}: "
                "fetching identifications..."
            )

            identification_count = (
                get_identification_count(
                    taxon_id
                )
            )

            print(
                f"   identifications: "
                f"{identification_count:,}"
            )

            print(
                f"   fetching observations..."
            )

            observation_count = (
                get_observation_count(
                    taxon_id
                )
            )

            print(
                f"   observations: "
                f"{observation_count:,}"
            )

            cache[key] = {
                "family": family,
                "taxon_id": taxon_id,
                "start_date": START_DATE,
                "end_date": END_DATE,
                "identification_count":
                    identification_count,
                "observation_count":
                    observation_count,
            }

            save_cache(cache)

            source = "API"

        if observation_count:
            ids_per_observation = (
                identification_count
                / observation_count
            )
        else:
            ids_per_observation = None

        results.append(
            {
                "family": family,
                "taxon_id": taxon_id,
                "identifications_2024":
                    identification_count,
                "observations_2024":
                    observation_count,
                "ids_per_observation_2024":
                    ids_per_observation,
            }
        )

        ratio_text = (
            f"{ids_per_observation:.3f}"
            if ids_per_observation
            is not None
            else "NA"
        )

        print(
            f"{index:2}/{len(families)} "
            f"{family:16} "
            f"IDs={identification_count:>10,} "
            f"Obs={observation_count:>10,} "
            f"IDs/obs={ratio_text:>7} "
            f"{source}"
        )

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True,
    )

    fields = [
        "family",
        "taxon_id",
        "identifications_2024",
        "observations_2024",
        "ids_per_observation_2024",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        for row in results:
            writer.writerow(row)

    print()
    print(
        "IDENTIFIER CAPACITY SUMMARY"
    )
    print(
        "==========================="
    )
    print()

    header = (
        f"{'Family':17}"
        f"{'2024 IDs':>12}"
        f"{'2024 Obs':>12}"
        f"{'IDs/Obs':>10}"
    )

    print(header)
    print("-" * len(header))

    for row in results:
        print(
            f"{row['family']:17}"
            f"{row['identifications_2024']:12,d}"
            f"{row['observations_2024']:12,d}"
            f"{row['ids_per_observation_2024']:10.3f}"
        )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print(
        f"Cache: {CACHE_FILE}"
    )


if __name__ == "__main__":
    main()