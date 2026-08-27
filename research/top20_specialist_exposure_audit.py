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

AUDIT_FILE = os.path.join(
    DATA_DIR,
    "public_interaction_audit.csv",
)

OBSERVATION_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "public_interaction_audit.json",
)

SPECIALIST_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "top20_specialists_2024.json",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "top20_specialist_exposure_audit.csv",
)

START_DATE = "2024-01-01"
END_DATE = "2024-12-31T23:59:59.999"

TOP_N = 20
REQUEST_DELAY = 1.25


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


def save_json(
    filename,
    data,
):
    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True,
    )

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            data,
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
    rows = []

    with open(
        AUDIT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            rows.append(
                {
                    "family":
                        row["family"],
                    "common_name":
                        row["common_name"],
                    "observation_id":
                        int(
                            row[
                                "observation_id"
                            ]
                        ),
                    "external_id_count":
                        int(
                            row[
                                "external_id_count"
                            ]
                        ),
                }
            )

    return rows


def get_top20_specialists(
    family_row,
    cache,
):
    family = family_row["family"]
    taxon_id = family_row["taxon_id"]

    key = str(taxon_id)

    if key in cache:
        return (
            cache[key],
            "cache",
        )

    data = api_get(
        (
            "https://api.inaturalist.org/"
            "v1/identifications/identifiers"
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

    specialists = []

    for rank, result in enumerate(
        data.get("results", [])[:TOP_N],
        start=1,
    ):
        user = result.get(
            "user",
            {},
        )

        user_id = user.get("id")

        if user_id is None:
            continue

        specialists.append(
            {
                "rank": rank,
                "user_id":
                    int(user_id),
                "login":
                    user.get(
                        "login",
                        "",
                    ),
                "identifications_2024":
                    int(
                        result.get(
                            "count",
                            0,
                        )
                    ),
            }
        )

    cache[key] = specialists

    save_json(
        SPECIALIST_CACHE_FILE,
        cache,
    )

    return (
        specialists,
        "API",
    )


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


def analyse_observation(
    audit_row,
    observation,
    specialist_ids,
):
    owner = observation.get(
        "user",
        {},
    )

    owner_id = owner.get("id")

    if owner_id is not None:
        owner_id = int(owner_id)

    external_identifier_ids = set()

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

        if user_id is None:
            continue

        if user_id == owner_id:
            continue

        external_identifier_ids.add(
            user_id
        )

    reviewer_ids = set()

    for value in (
        observation.get(
            "reviewed_by",
            [],
        )
        or []
    ):
        try:
            user_id = int(value)
        except (
            TypeError,
            ValueError,
        ):
            continue

        if user_id == owner_id:
            continue

        reviewer_ids.add(user_id)

    specialist_identifier_ids = (
        external_identifier_ids
        & specialist_ids
    )

    specialist_reviewer_ids = (
        reviewer_ids
        & specialist_ids
    )

    specialist_review_no_id_ids = (
        specialist_reviewer_ids
        - external_identifier_ids
    )

    specialist_exposure_ids = (
        specialist_identifier_ids
        | specialist_review_no_id_ids
    )

    return {
        "family":
            audit_row["family"],
        "common_name":
            audit_row["common_name"],
        "observation_id":
            audit_row["observation_id"],
        "external_id_present":
            (
                audit_row[
                    "external_id_count"
                ]
                > 0
            ),
        "top20_identified_count":
            len(
                specialist_identifier_ids
            ),
        "top20_review_no_id_count":
            len(
                specialist_review_no_id_ids
            ),
        "top20_exposure_count":
            len(
                specialist_exposure_ids
            ),
        "top20_identified":
            bool(
                specialist_identifier_ids
            ),
        "top20_review_no_id":
            bool(
                specialist_review_no_id_ids
            ),
        "top20_detectable_exposure":
            bool(
                specialist_exposure_ids
            ),
    }


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


def summarize_group(
    title,
    rows,
):
    print()
    print(title)
    print("-" * len(title))

    n = len(rows)

    print(
        f"  Observations: {n}"
    )

    if n == 0:
        return

    identified_obs = sum(
        row["top20_identified"]
        for row in rows
    )

    silent_obs = sum(
        row["top20_review_no_id"]
        for row in rows
    )

    exposure_obs = sum(
        row[
            "top20_detectable_exposure"
        ]
        for row in rows
    )

    identified_pairs = sum(
        row[
            "top20_identified_count"
        ]
        for row in rows
    )

    silent_pairs = sum(
        row[
            "top20_review_no_id_count"
        ]
        for row in rows
    )

    exposure_pairs = (
        identified_pairs
        + silent_pairs
    )

    print(
        "  Top-20 identified: "
        f"{identified_obs}/{n} "
        f"({percent(identified_obs, n):.1f}%) "
        f"pairs={identified_pairs}"
    )

    print(
        "  Top-20 reviewed-no-ID: "
        f"{silent_obs}/{n} "
        f"({percent(silent_obs, n):.1f}%) "
        f"pairs={silent_pairs}"
    )

    print(
        "  Any Top-20 exposure: "
        f"{exposure_obs}/{n} "
        f"({percent(exposure_obs, n):.1f}%) "
        f"pairs={exposure_pairs}"
    )

    if exposure_pairs:
        print(
            "  Silent-review share "
            "of Top-20 exposure pairs: "
            f"{silent_pairs}/"
            f"{exposure_pairs} "
            f"({percent(silent_pairs, exposure_pairs):.1f}%)"
        )


def main():
    audit_rows = load_audit_rows()

    observation_cache = load_json(
        OBSERVATION_CACHE_FILE
    )

    specialist_cache = load_json(
        SPECIALIST_CACHE_FILE,
        default={},
    )

    family_lookup = {
        row["family"]: row
        for row in FAMILIES
    }

    specialists_by_family = {}

    print()
    print(
        "TOP-20 SPECIALIST EXPOSURE AUDIT"
    )
    print(
        "================================"
    )
    print()
    print(
        "Specialists defined by 2024 "
        "external family identification "
        "activity."
    )

    for family_row in FAMILIES:
        family = family_row["family"]
        common_name = (
            family_row["common_name"]
        )

        (
            specialists,
            source,
        ) = get_top20_specialists(
            family_row,
            specialist_cache,
        )

        specialists_by_family[
            family
        ] = {
            specialist["user_id"]
            for specialist
            in specialists
        }

        print()
        print(
            f"{family} "
            f"({common_name}): "
            f"{len(specialists)} "
            f"specialists "
            f"{source}"
        )

        for specialist in (
            specialists[:5]
        ):
            print(
                f"  {specialist['rank']:2}. "
                f"{specialist['login']:22} "
                f"{specialist['identifications_2024']:8,d}"
            )

    output_rows = []

    for audit_row in audit_rows:
        family = audit_row[
            "family"
        ]

        observation_id = (
            audit_row[
                "observation_id"
            ]
        )

        observation = (
            observation_cache[
                str(observation_id)
            ]
        )

        specialist_ids = (
            specialists_by_family[
                family
            ]
        )

        output_rows.append(
            analyse_observation(
                audit_row,
                observation,
                specialist_ids,
            )
        )

    fields = [
        "family",
        "common_name",
        "observation_id",
        "external_id_present",
        "top20_identified_count",
        "top20_review_no_id_count",
        "top20_exposure_count",
        "top20_identified",
        "top20_review_no_id",
        "top20_detectable_exposure",
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
        "TOP-20 SPECIALIST EXPOSURE SUMMARY"
    )
    print(
        "=================================="
    )

    for family_row in FAMILIES:
        family = family_row[
            "family"
        ]

        common_name = family_row[
            "common_name"
        ]

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
            f"({common_name})"
        )

        print(
            "=" * (
                len(family)
                + len(common_name)
                + 3
            )
        )

        summarize_group(
            "NO EXTERNAL ID",
            no_external,
        )

        summarize_group(
            "WITH EXTERNAL ID",
            with_external,
        )

    all_no_external = [
        row
        for row in output_rows
        if not row[
            "external_id_present"
        ]
    ]

    all_with_external = [
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

    summarize_group(
        "NO EXTERNAL ID",
        all_no_external,
    )

    summarize_group(
        "WITH EXTERNAL ID",
        all_with_external,
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )

    print(
        f"Specialist cache: "
        f"{SPECIALIST_CACHE_FILE}"
    )


if __name__ == "__main__":
    main()