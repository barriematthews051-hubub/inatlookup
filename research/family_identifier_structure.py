import csv
import json
import os
import time

import requests


FAMILY_FILE = os.path.join(
    "research",
    "data",
    "family_model_a_dataset.csv",
)

CAPACITY_FILE = os.path.join(
    "research",
    "data",
    "family_identifier_capacity.csv",
)

OUTPUT_FILE = os.path.join(
    "research",
    "data",
    "family_identifier_structure.csv",
)

CACHE_FILE = os.path.join(
    "research",
    "cache",
    "family_identifier_structure_2024.json",
)

START_DATE = "2024-01-01"
END_DATE = "2024-12-31T23:59:59.999"

REQUEST_DELAY = 1.25


COMMON_NAMES = {
    "Syrphidae": "hoverflies",
    "Asilidae": "robber flies",
    "Geometridae": "geometer moths",
    "Nymphalidae": "brush-footed butterflies",
    "Staphylinidae": "rove beetles",
    "Asteraceae": "daisy/sunflower family",
    "Formicidae": "ants",
    "Libellulidae": "skimmers and perchers",
    "Orchidaceae": "orchid family",
    "Poaceae": "grass family",
    "Russulaceae": "russulas and milkcaps",
    "Parmeliaceae": "shield lichens",
    "Salticidae": "jumping spiders",
    "Lycosidae": "wolf spiders",
    "Anatidae": "ducks, geese and swans",
    "Colubridae": "colubrid snakes",
    "Limacidae": "keeled slugs",
    "Asteriidae": "common sea stars",
}


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


def load_families():
    rows = []

    with open(
        FAMILY_FILE,
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


def load_observation_counts():
    counts = {}

    with open(
        CAPACITY_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            counts[row["family"]] = int(
                row["observations_2024"]
            )

    return counts


def external_identification_count(
    taxon_id,
):
    data = api_get(
        "https://api.inaturalist.org/v1/identifications",
        {
            "taxon_id": taxon_id,
            "d1": START_DATE,
            "d2": END_DATE,
            "current": "any",
            "own_observation": "false",
            "per_page": 0,
        },
    )

    return int(
        data["total_results"]
    )


def identifier_summary(
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
            "per_page": 100,
            "page": 1,
        },
    )

    unique_identifiers = int(
        data["total_results"]
    )

    counts = [
        int(result["count"])
        for result in data["results"]
    ]

    return (
        unique_identifiers,
        counts,
    )


def share_top_n(
    counts,
    total,
    n,
):
    if total == 0:
        return 0.0

    return (
        sum(counts[:n])
        / total
        * 100
    )


def main():
    families = load_families()

    observation_counts = (
        load_observation_counts()
    )

    cache = load_cache()

    results = []

    print()
    print(
        "PRE-2025 EXTERNAL IDENTIFIER STRUCTURE"
    )
    print(
        "======================================"
    )
    print()
    print(
        f"Period: {START_DATE} "
        f"to {END_DATE}"
    )
    print(
        "own_observation=false"
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

        common_name = COMMON_NAMES.get(
            family,
            "",
        )

        key = str(taxon_id)

        if key in cache:
            cached = cache[key]

            external_ids = int(
                cached[
                    "external_identifications"
                ]
            )

            unique_identifiers = int(
                cached[
                    "unique_external_identifiers"
                ]
            )

            top_counts = [
                int(value)
                for value
                in cached["top_counts"]
            ]

            source = "cache"

        else:
            print(
                f"{index:2}/{len(families)} "
                f"{family} "
                f"({common_name})"
            )

            print(
                "   fetching external "
                "identification count..."
            )

            external_ids = (
                external_identification_count(
                    taxon_id
                )
            )

            print(
                f"   external IDs: "
                f"{external_ids:,}"
            )

            print(
                "   fetching identifier "
                "community..."
            )

            (
                unique_identifiers,
                top_counts,
            ) = identifier_summary(
                taxon_id
            )

            print(
                f"   unique identifiers: "
                f"{unique_identifiers:,}"
            )

            cache[key] = {
                "family": family,
                "common_name": common_name,
                "taxon_id": taxon_id,
                "start_date": START_DATE,
                "end_date": END_DATE,
                "own_observation": False,
                "external_identifications":
                    external_ids,
                "unique_external_identifiers":
                    unique_identifiers,
                "top_counts":
                    top_counts,
            }

            save_cache(cache)

            source = "API"

        observations = (
            observation_counts[family]
        )

        if observations:
            external_ids_per_obs = (
                external_ids
                / observations
            )
        else:
            external_ids_per_obs = 0.0

        if unique_identifiers:
            ids_per_identifier = (
                external_ids
                / unique_identifiers
            )
        else:
            ids_per_identifier = 0.0

        top1_pct = share_top_n(
            top_counts,
            external_ids,
            1,
        )

        top5_pct = share_top_n(
            top_counts,
            external_ids,
            5,
        )

        top10_pct = share_top_n(
            top_counts,
            external_ids,
            10,
        )

        top20_pct = share_top_n(
            top_counts,
            external_ids,
            20,
        )

        results.append(
            {
                "family": family,
                "common_name": common_name,
                "taxon_id": taxon_id,
                "observations_2024":
                    observations,
                "external_identifications_2024":
                    external_ids,
                "unique_external_identifiers_2024":
                    unique_identifiers,
                "external_ids_per_observation_2024":
                    external_ids_per_obs,
                "external_ids_per_identifier_2024":
                    ids_per_identifier,
                "top1_external_id_share_2024":
                    top1_pct,
                "top5_external_id_share_2024":
                    top5_pct,
                "top10_external_id_share_2024":
                    top10_pct,
                "top20_external_id_share_2024":
                    top20_pct,
            }
        )

        print(
            f"{index:2}/{len(families)} "
            f"{family:16} "
            f"ExtIDs/obs="
            f"{external_ids_per_obs:6.3f} "
            f"Identifiers="
            f"{unique_identifiers:7,d} "
            f"Top5="
            f"{top5_pct:5.1f}% "
            f"{source}"
        )

    fields = [
        "family",
        "common_name",
        "taxon_id",
        "observations_2024",
        "external_identifications_2024",
        "unique_external_identifiers_2024",
        "external_ids_per_observation_2024",
        "external_ids_per_identifier_2024",
        "top1_external_id_share_2024",
        "top5_external_id_share_2024",
        "top10_external_id_share_2024",
        "top20_external_id_share_2024",
    ]

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True,
    )

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
        "EXTERNAL IDENTIFIER STRUCTURE SUMMARY"
    )
    print(
        "====================================="
    )
    print()

    header = (
        f"{'Family':17}"
        f"{'Ext IDs/Obs':>12}"
        f"{'Identifiers':>13}"
        f"{'IDs/User':>10}"
        f"{'Top1':>8}"
        f"{'Top5':>8}"
        f"{'Top20':>8}"
    )

    print(header)
    print("-" * len(header))

    for row in results:
        print(
            f"{row['family']:17}"
            f"{row['external_ids_per_observation_2024']:12.3f}"
            f"{row['unique_external_identifiers_2024']:13,d}"
            f"{row['external_ids_per_identifier_2024']:10.1f}"
            f"{row['top1_external_id_share_2024']:7.1f}%"
            f"{row['top5_external_id_share_2024']:7.1f}%"
            f"{row['top20_external_id_share_2024']:7.1f}%"
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