import csv
import random
import time
from collections import defaultdict
from datetime import date, timedelta
import json
import os

import requests


TAXON_ID = 49995
TAXON_NAME = "Syrphidae"

START_DATE = date(2025, 1, 1)
END_DATE = date(2025, 6, 30)

# Keep this at 12 for the second test.
TARGET_SAMPLE = 500

RANDOM_SEED = 49995

API_URL = "https://api.inaturalist.org/v1/observations"
REQUEST_DELAY = 1.0
PER_PAGE = 200

COUNTS_CACHE = "research/syrphidae_daily_counts.json"


def api_get(params):
    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    time.sleep(REQUEST_DELAY)

    return response.json()


def month_ranges(start_date, end_date):
    current = date(start_date.year, start_date.month, 1)

    while current <= end_date:

        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(
                current.year,
                current.month + 1,
                1
            )

        month_end = next_month - timedelta(days=1)

        if month_end > end_date:
            month_end = end_date

        yield current, month_end

        current = next_month


def get_daily_counts(month_start, month_end):
    cache = {}

    if os.path.exists(COUNTS_CACHE):
        with open(
            COUNTS_CACHE,
            "r",
            encoding="utf-8"
        ) as f:
            cache = json.load(f)

    counts = []

    current = month_start

    while current <= month_end:

        key = current.isoformat()

        if key in cache:
            count = cache[key]
            source = "cached"

        else:
            data = api_get(
                {
                    "taxon_id": TAXON_ID,
                    "created_d1": key,
                    "created_d2": key,
                    "per_page": 1,
                }
            )

            count = data["total_results"]
            cache[key] = count
            source = "API"

            with open(
                COUNTS_CACHE,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    cache,
                    f,
                    indent=2,
                    sort_keys=True
                )

        counts.append(
            {
                "date": current,
                "count": count,
            }
        )

        print(
            f"  {current}: "
            f"{count:,} ({source})"
        )

        current += timedelta(days=1)

    return counts

def choose_positions(daily_counts, target, rng):
    total = sum(
        item["count"]
        for item in daily_counts
    )

    if total < target:
        raise RuntimeError(
            f"Only {total} observations available "
            f"for target sample of {target}."
        )

    positions = sorted(
        rng.sample(
            range(total),
            target
        )
    )

    selections = []

    cumulative = 0
    position_index = 0

    for item in daily_counts:

        day = item["date"]
        count = item["count"]
        day_end = cumulative + count

        while (
            position_index < len(positions)
            and positions[position_index] < day_end
        ):

            position = positions[position_index]

            offset_in_day = position - cumulative

            page = (
                offset_in_day // PER_PAGE
            ) + 1

            offset_in_page = (
                offset_in_day % PER_PAGE
            )

            selections.append(
                {
                    "date": day,
                    "page": page,
                    "offset": offset_in_page,
                }
            )

            position_index += 1

        cumulative = day_end

    return selections, total


def fetch_selected_observations(selections):
    grouped = defaultdict(list)

    for selection in selections:
        key = (
            selection["date"],
            selection["page"]
        )

        grouped[key].append(
            selection["offset"]
        )

    observations = []

    requests_needed = len(grouped)

    print(
        f"API pages to fetch: {requests_needed}"
    )

    for request_number, (
        (day, page),
        offsets
    ) in enumerate(
        sorted(grouped.items()),
        start=1
    ):

        print(
            f"  Fetching page "
            f"{request_number}/{requests_needed}: "
            f"{day} page {page}"
        )
        data = api_get(
            {
                "taxon_id": TAXON_ID,
                "created_d1": day.isoformat(),
                "created_d2": day.isoformat(),
                "per_page": PER_PAGE,
                "page": page,
                "order_by": "id",
                "order": "asc",
            }
        )

        results = data["results"]

        for offset in sorted(offsets):

            if offset >= len(results):
                raise RuntimeError(
                    f"Sampling offset {offset} "
                    f"missing for {day}, page {page}."
                )

            observations.append(
                results[offset]
            )

    return observations


def photo_count(observation):
    return len(
        observation.get("photos", [])
    )


def make_row(observation, sampling_month):
    taxon = observation.get("taxon") or {}

    geojson = observation.get("geojson")

    if geojson:
        coordinates = geojson.get(
            "coordinates",
            ["", ""]
        )
        longitude = coordinates[0]
        latitude = coordinates[1]
    else:
        latitude = ""
        longitude = ""

    return {
        "sampling_month": sampling_month,
        "observation_id": observation["id"],
        "observation_uuid": observation["uuid"],
        "observer_id": observation.get(
            "user_id",
            ""
        ),
        "created_at": observation.get(
            "created_at",
            ""
        ),
        "observed_on": observation.get(
            "observed_on",
            ""
        ),
        "taxon_id": taxon.get(
            "id",
            ""
        ),
        "taxon_name": taxon.get(
            "name",
            ""
        ),
        "taxon_rank": taxon.get(
            "rank",
            ""
        ),
        "community_taxon_id": observation.get(
            "community_taxon_id",
            ""
        ),
        "quality_grade": observation.get(
            "quality_grade",
            ""
        ),
        "photo_count": photo_count(
            observation
        ),
        "identifications_count": observation.get(
            "identifications_count",
            ""
        ),
        "identification_agreements": observation.get(
            "num_identification_agreements",
            ""
        ),
        "identification_disagreements": observation.get(
            "num_identification_disagreements",
            ""
        ),
        "latitude": latitude,
        "longitude": longitude,
        "project_count": len(
            observation.get(
                "project_ids",
                []
            )
        ),
    }


def main():
    rng = random.Random(
        RANDOM_SEED
    )

    months = list(
        month_ranges(
            START_DATE,
            END_DATE
        )
    )

    base = (
        TARGET_SAMPLE
        // len(months)
    )

    remainder = (
        TARGET_SAMPLE
        % len(months)
    )

    rows = []

    for index, (
        month_start,
        month_end
    ) in enumerate(months):

        target = base

        if index < remainder:
            target += 1

        print()
        print(
            f"{month_start:%B %Y}"
        )
        print(
            f"Target sample: {target}"
        )
        print("Counting observations by day...")

        daily_counts = get_daily_counts(
            month_start,
            month_end
        )

        selections, month_total = (
            choose_positions(
                daily_counts,
                target,
                rng
            )
        )

        print(
            f"Month population: "
            f"{month_total:,}"
        )

        print("Fetching selected observations...")

        observations = (
            fetch_selected_observations(
                selections
            )
        )

        print(
            "Selected observation IDs:",
            ", ".join(
                str(obs["id"])
                for obs in observations
            )
        )

        for obs in observations:

            rows.append(
                make_row(
                    obs,
                    month_start.strftime(
                        "%Y-%m"
                    )
                )
            )

    fieldnames = [
        "sampling_month",
        "observation_id",
        "observation_uuid",
        "observer_id",
        "created_at",
        "observed_on",
        "taxon_id",
        "taxon_name",
        "taxon_rank",
        "community_taxon_id",
        "quality_grade",
        "photo_count",
        "identifications_count",
        "identification_agreements",
        "identification_disagreements",
        "latitude",
        "longitude",
        "project_count",
    ]

    output_file = (
        f"research/"
        f"syrphidae_pilot_"
        f"{TARGET_SAMPLE}.csv"
    )

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
        writer.writerows(rows)

    print()
    print("Pilot sample complete")
    print("Taxon:", TAXON_NAME)
    print(
        "Observations:",
        len(rows)
    )
    print(
        "Random seed:",
        RANDOM_SEED
    )
    print(
        "Output:",
        output_file
    )


if __name__ == "__main__":
    main()