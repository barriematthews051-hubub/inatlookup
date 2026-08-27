import csv
import json
import os
import statistics
import time

from datetime import datetime, timedelta

import requests


DATA_DIR = os.path.join(
    "research",
    "data",
)

CACHE_DIR = os.path.join(
    "research",
    "cache",
)

AUDIT_FILE = os.path.join(
    DATA_DIR,
    "public_interaction_audit.csv",
)

OBSERVATION_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "public_interaction_audit.json",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "reviewer_experience_audit.csv",
)

EXPERIENCE_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "reviewer_experience_audit.json",
)

REQUEST_DELAY = 1.25


TAXON_IDS = {
    "Asteriidae": 47671,
    "Salticidae": 48139,
    "Russulaceae": 48340,
    "Anatidae": 6912,
}


COMMON_NAMES = {
    "Asteriidae": "common sea stars",
    "Salticidae": "jumping spiders",
    "Russulaceae": "russulas and milkcaps",
    "Anatidae": "ducks, geese and swans",
}


def load_json(
    filename,
    default=None,
):
    if not os.path.exists(filename):
        if default is None:
            raise FileNotFoundError(
                filename
            )

        return default

    with open(
        filename,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def save_experience_cache(cache):
    os.makedirs(
        CACHE_DIR,
        exist_ok=True,
    )

    with open(
        EXPERIENCE_CACHE_FILE,
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

        if response.status_code in {
            500,
            502,
            503,
            504,
        }:
            if attempt == max_attempts:
                response.raise_for_status()

            wait_seconds = min(
                60,
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"    Server error "
                f"{response.status_code}. "
                f"Retrying in "
                f"{wait_seconds} seconds..."
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


def load_audit_rows():
    rows = {}

    with open(
        AUDIT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            observation_id = int(
                row["observation_id"]
            )

            rows[observation_id] = {
                "family": row["family"],
                "common_name":
                    row["common_name"],
                "external_id_count":
                    int(
                        row[
                            "external_id_count"
                        ]
                    ),
            }

    return rows


def user_id_from_identification(
    identification,
):
    user_id = identification.get(
        "user_id"
    )

    if user_id is not None:
        try:
            return int(user_id)
        except (
            TypeError,
            ValueError,
        ):
            pass

    user = identification.get(
        "user"
    )

    if isinstance(user, dict):
        user_id = user.get("id")

        if user_id is not None:
            try:
                return int(user_id)
            except (
                TypeError,
                ValueError,
            ):
                pass

    return None


def reviewer_no_id_users(
    observation,
):
    owner = observation.get(
        "user",
        {},
    )

    owner_id = owner.get("id")

    if owner_id is not None:
        owner_id = int(owner_id)

    identifiers = set()

    for identification in (
        observation.get(
            "identifications",
            [],
        )
        or []
    ):
        user_id = (
            user_id_from_identification(
                identification
            )
        )

        if user_id is not None:
            identifiers.add(user_id)

    reviewers = set()

    for value in (
        observation.get(
            "reviewed_by",
            [],
        )
        or []
    ):
        try:
            reviewers.add(
                int(value)
            )
        except (
            TypeError,
            ValueError,
        ):
            pass

    if owner_id is not None:
        reviewers.discard(owner_id)

    return (
        reviewers
        - identifiers
    )


def timestamp_before(
    created_at,
):
    text = str(created_at)

    if text.endswith("Z"):
        text = (
            text[:-1]
            + "+00:00"
        )

    value = datetime.fromisoformat(
        text
    )

    value = (
        value
        - timedelta(seconds=1)
    )

    return value.isoformat()


def prior_identification_count(
    user_id,
    taxon_id,
    d2,
    own_observation=None,
):
    params = {
        "user_id": user_id,
        "taxon_id": taxon_id,
        "current": "any",
        "d2": d2,
        "per_page": 0,
    }

    if own_observation is not None:
        params[
            "own_observation"
        ] = (
            "true"
            if own_observation
            else "false"
        )

    data = api_get(
        (
            "https://api.inaturalist.org/"
            "v1/identifications"
        ),
        params,
    )

    return int(
        data["total_results"]
    )


def experience_band(count):
    if count == 0:
        return "0"

    if count < 10:
        return "1-9"

    if count < 100:
        return "10-99"

    if count < 1000:
        return "100-999"

    if count < 10000:
        return "1,000-9,999"

    return "10,000+"


def median_text(values):
    if not values:
        return "NA"

    return (
        f"{statistics.median(values):,.1f}"
    )


def percent(
    numerator,
    denominator,
):
    if not denominator:
        return 0.0

    return (
        numerator
        / denominator
        * 100
    )


def print_group_summary(
    title,
    rows,
):
    print()
    print(title)
    print("-" * len(title))

    if not rows:
        print("  Pairs: 0")
        return

    all_counts = [
        row["prior_family_ids"]
        for row in rows
    ]

    external_counts = [
        row[
            "prior_external_family_ids"
        ]
        for row in rows
    ]

    unique_reviewers = {
        row["reviewer_user_id"]
        for row in rows
    }

    print(
        f"  Reviewer-observation pairs: "
        f"{len(rows)}"
    )

    print(
        f"  Unique reviewers: "
        f"{len(unique_reviewers)}"
    )

    print(
        f"  Median prior family IDs: "
        f"{median_text(all_counts)}"
    )

    print(
        f"  Median prior external "
        f"family IDs: "
        f"{median_text(external_counts)}"
    )

    for threshold in [
        10,
        100,
        1000,
        10000,
    ]:
        count = sum(
            value >= threshold
            for value in external_counts
        )

        print(
            f"  Prior external IDs "
            f">={threshold:,}: "
            f"{count}/{len(rows)} "
            f"({percent(count, len(rows)):.1f}%)"
        )


def main():
    audit_rows = load_audit_rows()

    observation_cache = load_json(
        OBSERVATION_CACHE_FILE
    )

    experience_cache = load_json(
        EXPERIENCE_CACHE_FILE,
        default={},
    )

    output_rows = []

    print()
    print(
        "REVIEWER EXPERIENCE AUDIT"
    )
    print(
        "========================="
    )
    print()
    print(
        "Reviewer-without-ID pairs "
        "from the 100-observation "
        "public interaction audit."
    )
    print()
    print(
        "Experience is counted before "
        "the sampled observation was "
        "created."
    )

    pair_number = 0

    for observation_id in sorted(
        audit_rows
    ):
        audit = audit_rows[
            observation_id
        ]

        family = audit["family"]

        taxon_id = TAXON_IDS[
            family
        ]

        common_name = COMMON_NAMES[
            family
        ]

        observation = (
            observation_cache[
                str(observation_id)
            ]
        )

        created_at = observation.get(
            "created_at"
        )

        if not created_at:
            raise ValueError(
                f"Observation "
                f"{observation_id} "
                "has no created_at"
            )

        d2 = timestamp_before(
            created_at
        )

        reviewers = sorted(
            reviewer_no_id_users(
                observation
            )
        )

        for reviewer_user_id in reviewers:
            pair_number += 1

            cache_key = (
                f"{taxon_id}:"
                f"{reviewer_user_id}:"
                f"{d2}"
            )

            if cache_key in experience_cache:
                cached = (
                    experience_cache[
                        cache_key
                    ]
                )

                prior_family_ids = int(
                    cached[
                        "prior_family_ids"
                    ]
                )

                prior_external_family_ids = int(
                    cached[
                        "prior_external_family_ids"
                    ]
                )

                source = "cache"

            else:
                print(
                    f"{pair_number:3} "
                    f"{family} "
                    f"({common_name}) "
                    f"obs={observation_id} "
                    f"user={reviewer_user_id}"
                )

                prior_family_ids = (
                    prior_identification_count(
                        reviewer_user_id,
                        taxon_id,
                        d2,
                    )
                )

                prior_external_family_ids = (
                    prior_identification_count(
                        reviewer_user_id,
                        taxon_id,
                        d2,
                        own_observation=False,
                    )
                )

                experience_cache[
                    cache_key
                ] = {
                    "family": family,
                    "common_name":
                        common_name,
                    "taxon_id": taxon_id,
                    "observation_id":
                        observation_id,
                    "reviewer_user_id":
                        reviewer_user_id,
                    "observation_created_at":
                        created_at,
                    "experience_cutoff":
                        d2,
                    "prior_family_ids":
                        prior_family_ids,
                    "prior_external_family_ids":
                        prior_external_family_ids,
                }

                save_experience_cache(
                    experience_cache
                )

                source = "API"

            output_rows.append(
                {
                    "family": family,
                    "common_name":
                        common_name,
                    "taxon_id": taxon_id,
                    "observation_id":
                        observation_id,
                    "observation_created_at":
                        created_at,
                    "external_id_present":
                        (
                            audit[
                                "external_id_count"
                            ]
                            > 0
                        ),
                    "reviewer_user_id":
                        reviewer_user_id,
                    "prior_family_ids":
                        prior_family_ids,
                    "prior_external_family_ids":
                        prior_external_family_ids,
                    "experience_band":
                        experience_band(
                            prior_external_family_ids
                        ),
                }
            )

            print(
                f"     prior IDs="
                f"{prior_family_ids:,} "
                f"external="
                f"{prior_external_family_ids:,} "
                f"{source}"
            )

    fields = [
        "family",
        "common_name",
        "taxon_id",
        "observation_id",
        "observation_created_at",
        "external_id_present",
        "reviewer_user_id",
        "prior_family_ids",
        "prior_external_family_ids",
        "experience_band",
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
        "REVIEWER EXPERIENCE SUMMARY"
    )
    print(
        "==========================="
    )

    for family in TAXON_IDS:
        family_rows = [
            row
            for row in output_rows
            if row["family"] == family
        ]

        no_external = [
            row
            for row in family_rows
            if not row[
                "external_id_present"
            ]
        ]

        with_external = [
            row
            for row in family_rows
            if row[
                "external_id_present"
            ]
        ]

        print()
        print(
            f"{family} "
            f"({COMMON_NAMES[family]})"
        )
        print(
            "=" * (
                len(family)
                + len(
                    COMMON_NAMES[family]
                )
                + 3
            )
        )

        print_group_summary(
            "NO EXTERNAL ID",
            no_external,
        )

        print_group_summary(
            "WITH EXTERNAL ID",
            with_external,
        )

    no_external_all = [
        row
        for row in output_rows
        if not row[
            "external_id_present"
        ]
    ]

    with_external_all = [
        row
        for row in output_rows
        if row[
            "external_id_present"
        ]
    ]

    print()
    print(
        "ALL FOUR FAMILIES"
    )
    print(
        "================="
    )

    print_group_summary(
        "NO EXTERNAL ID",
        no_external_all,
    )

    print_group_summary(
        "WITH EXTERNAL ID",
        with_external_all,
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Cache: "
        f"{EXPERIENCE_CACHE_FILE}"
    )


if __name__ == "__main__":
    main()