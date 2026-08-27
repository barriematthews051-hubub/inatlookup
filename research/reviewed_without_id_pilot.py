import csv
import json
import os
import time

import requests


DATA_DIR = os.path.join(
    "research",
    "data",
)

CACHE_DIR = os.path.join(
    "research",
    "cache",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "reviewed_without_id_pilot.csv",
)

CACHE_FILE = os.path.join(
    CACHE_DIR,
    "reviewed_without_id_pilot.json",
)

START_DATE = "2024-01-01"
END_DATE = "2024-12-31T23:59:59.999"

REQUEST_DELAY = 1.25

TOP_N = 5

FAMILIES = [
    {
        "family": "Asteriidae",
        "common_name": "common sea stars",
        "taxon_id": 47671,
    },
    {
        "family": "Salticidae",
        "common_name": "jumping spiders",
        "taxon_id": 48139,
    },
    {
        "family": "Russulaceae",
        "common_name": "russulas and milkcaps",
        "taxon_id": 48340,
    },
    {
        "family": "Anatidae",
        "common_name": "ducks, geese and swans",
        "taxon_id": 6912,
    },
]


def slugify(text):
    return (
        text.lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


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
        CACHE_DIR,
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


def load_sample_observations(
    family,
):
    filename = os.path.join(
        DATA_DIR,
        f"{slugify(family)}"
        "_pilot_500_analysis.csv",
    )

    observations = {}

    with open(
        filename,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            observation_id = int(
                row["observation_id"]
            )

            observations[
                observation_id
            ] = row

    if len(observations) != 500:
        raise ValueError(
            f"{family}: expected 500 "
            f"observations, found "
            f"{len(observations)}"
        )

    return observations


def get_top_identifiers(
    taxon_id,
):
    data = api_get(
        (
            "https://api.inaturalist.org/v1/"
            "identifications/identifiers"
        ),
        {
            "taxon_id": taxon_id,
            "d1": START_DATE,
            "d2": END_DATE,
            "current": "any",
            "own_observation": "false",
            "per_page": TOP_N,
            "page": 1,
        },
    )

    identifiers = []

    for result in data["results"][:TOP_N]:
        user = result["user"]

        identifiers.append(
            {
                "user_id": int(
                    user["id"]
                ),
                "login": user["login"],
                "identification_count":
                    int(result["count"]),
            }
        )

    return identifiers


def batch_items(items, size=100):
    items = list(items)

    for start in range(
        0,
        len(items),
        size,
    ):
        yield items[
            start:start + size
        ]


def reviewed_without_id_for_sample(
    sample_ids,
    user_id,
    login,
):
    matched = set()

    for batch in batch_items(
        sample_ids,
        size=100,
    ):
        data = api_get(
            (
                "https://api.inaturalist.org/"
                "v1/observations"
            ),
            {
                "id": ",".join(
                    str(value)
                    for value in batch
                ),
                "reviewed": "true",
                "viewer_id": user_id,
                "without_ident_user_id":
                    login,
                "per_page": 100,
                "page": 1,
            },
        )

        for result in data["results"]:
            matched.add(
                int(result["id"])
            )

    return matched


def active_ids_by_user(
    sample_ids,
    user_id,
):
    matched = set()

    for batch in batch_items(
        sample_ids,
        size=100,
    ):
        data = api_get(
            (
                "https://api.inaturalist.org/"
                "v1/identifications"
            ),
            {
                "observation_id": ",".join(
                    str(value)
                    for value in batch
                ),
                "user_id": user_id,
                "current": "true",
                "per_page": 200,
                "page": 1,
            },
        )

        for result in data["results"]:
            observation = result.get(
                "observation"
            )

            if observation:
                matched.add(
                    int(
                        observation["id"]
                    )
                )

    return matched


def main():
    cache = load_cache()

    output_rows = []

    print()
    print(
        "REVIEWED-WITHOUT-ID PILOT"
    )
    print(
        "========================="
    )
    print()
    print(
        "Current reviewed state on "
        "the frozen 2025 samples"
    )
    print(
        "Top identifiers selected "
        "from 2024 activity"
    )
    print()

    for family_row in FAMILIES:
        family = family_row["family"]
        common_name = (
            family_row["common_name"]
        )
        taxon_id = (
            family_row["taxon_id"]
        )

        print()
        print(
            f"{family} "
            f"({common_name})"
        )
        print(
            "-" * (
                len(family)
                + len(common_name)
                + 3
            )
        )

        observations = (
            load_sample_observations(
                family
            )
        )

        sample_ids = set(
            observations.keys()
        )

        identifier_key = (
            f"{taxon_id}:identifiers"
        )

        if identifier_key in cache:
            identifiers = (
                cache[identifier_key]
            )
        else:
            identifiers = (
                get_top_identifiers(
                    taxon_id
                )
            )

            cache[
                identifier_key
            ] = identifiers

            save_cache(cache)

        family_reviewed_union = set()
        family_identified_union = set()

        for rank, identifier in enumerate(
            identifiers,
            start=1,
        ):
            user_id = int(
                identifier["user_id"]
            )

            login = identifier["login"]

            activity_count = int(
                identifier[
                    "identification_count"
                ]
            )

            result_key = (
                f"{taxon_id}:"
                f"{user_id}:sample"
            )

            if result_key in cache:
                result = cache[result_key]

                reviewed_without_id = set(
                    result[
                        "reviewed_without_id"
                    ]
                )

                identified = set(
                    result["identified"]
                )

                source = "cache"

            else:
                print(
                    f"  {rank}. {login}: "
                    "checking..."
                )

                reviewed_without_id = (
                    reviewed_without_id_for_sample(
                        sample_ids,
                        user_id,
                        login,
                    )
                )

                identified = (
                    active_ids_by_user(
                        sample_ids,
                        user_id,
                    )
                )

                result = {
                    "family": family,
                    "user_id": user_id,
                    "login": login,
                    "reviewed_without_id":
                        sorted(
                            reviewed_without_id
                        ),
                    "identified":
                        sorted(
                            identified
                        ),
                }

                cache[result_key] = result
                save_cache(cache)

                source = "API"

            exposed = (
                reviewed_without_id
                | identified
            )

            family_reviewed_union.update(
                reviewed_without_id
            )

            family_identified_union.update(
                identified
            )

            output_rows.append(
                {
                    "family": family,
                    "common_name":
                        common_name,
                    "identifier_rank":
                        rank,
                    "user_id": user_id,
                    "login": login,
                    "identifications_2024":
                        activity_count,
                    "sample_identified":
                        len(identified),
                    "sample_reviewed_without_id":
                        len(
                            reviewed_without_id
                        ),
                    "sample_detectable_exposure":
                        len(exposed),
                    "silent_review_share_of_exposure":
                        (
                            len(
                                reviewed_without_id
                            )
                            / len(exposed)
                            * 100
                            if exposed
                            else 0.0
                        ),
                }
            )

            print(
                f"     {login:22} "
                f"ID={len(identified):3} "
                f"review-no-ID="
                f"{len(reviewed_without_id):3} "
                f"exposure={len(exposed):3} "
                f"{source}"
            )

        family_exposure = (
            family_reviewed_union
            | family_identified_union
        )

        print()
        print(
            "  TOP-5 UNION"
        )
        print(
            f"    identified: "
            f"{len(family_identified_union)}"
            f"/500"
        )
        print(
            f"    reviewed without ID: "
            f"{len(family_reviewed_union)}"
            f"/500"
        )
        print(
            f"    detectable exposure: "
            f"{len(family_exposure)}"
            f"/500"
        )

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    fields = [
        "family",
        "common_name",
        "identifier_rank",
        "user_id",
        "login",
        "identifications_2024",
        "sample_identified",
        "sample_reviewed_without_id",
        "sample_detectable_exposure",
        "silent_review_share_of_exposure",
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

        for row in output_rows:
            writer.writerow(row)

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print(
        f"Cache: {CACHE_FILE}"
    )


if __name__ == "__main__":
    main()