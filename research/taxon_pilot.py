import argparse
import csv
import json
import os
import random
import re
import time
from collections import defaultdict
from datetime import date, datetime, timedelta

import requests

API_URL = "https://api.inaturalist.org/v1/observations"

REQUEST_DELAY = 1.25
PER_PAGE = 200
MAX_STANDARD_PAGE = 50

DATA_DIR = "research/data"
CACHE_DIR = "research/cache"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build a reproducible stratified "
            "iNaturalist taxon pilot sample."
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
        help="Total sample size. Default: 500.",
    )

    parser.add_argument(
        "--start-date",
        default="2025-01-01",
        help="Start creation date YYYY-MM-DD.",
    )

    parser.add_argument(
        "--end-date",
        default="2025-06-30",
        help="End creation date YYYY-MM-DD.",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=(
            "Random seed. "
            "Defaults to taxon ID."
        ),
    )

    return parser.parse_args()


def parse_date(text):
    return datetime.strptime(
        text,
        "%Y-%m-%d"
    ).date()


def slugify(text):
    text = text.strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    )

    return text.strip("_")


def api_get(params):
    max_attempts = 8

    for attempt in range(
        1,
        max_attempts + 1
    ):
        response = requests.get(
            API_URL,
            params=params,
            timeout=60,
            headers={
                "User-Agent":
                    "inatlookup-research-pilot"
            },
        )

        if response.status_code == 429:

            retry_after = (
                response.headers.get(
                    "Retry-After"
                )
            )

            if retry_after:
                try:
                    wait_seconds = float(
                        retry_after
                    )
                except ValueError:
                    wait_seconds = 0
            else:
                wait_seconds = 0

            if wait_seconds <= 0:
                wait_seconds = min(
                    60,
                    5 * attempt
                )

            print(
                "    API throttled "
                f"(429). Waiting "
                f"{wait_seconds:.0f} "
                "seconds before retry..."
            )

            time.sleep(
                wait_seconds
            )

            continue

        response.raise_for_status()

        data = response.json()

        time.sleep(
            REQUEST_DELAY
        )

        return data

    raise RuntimeError(
        "API request failed after "
        f"{max_attempts} attempts: "
        f"{params}"
    )

def month_ranges(
    start_date,
    end_date
):
    current = date(
        start_date.year,
        start_date.month,
        1
    )

    while current <= end_date:

        if current.month == 12:
            next_month = date(
                current.year + 1,
                1,
                1
            )
        else:
            next_month = date(
                current.year,
                current.month + 1,
                1
            )

        month_start = max(
            current,
            start_date
        )

        month_end = min(
            next_month - timedelta(days=1),
            end_date
        )

        yield (
            month_start,
            month_end
        )

        current = next_month


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


def get_daily_counts(
    taxon_id,
    month_start,
    month_end,
    cache_file
):
    cache = load_cache(
        cache_file
    )

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
                    "taxon_id": taxon_id,
                    "created_d1": key,
                    "created_d2": key,
                    "per_page": 1,
                }
            )

            count = (
                data["total_results"]
            )

            cache[key] = count

            save_cache(
                cache_file,
                cache
            )

            source = "API"

        counts.append(
            {
                "date": current,
                "count": count,
            }
        )

        print(
            f"  {current}: "
            f"{count:,} "
            f"({source})"
        )

        current += timedelta(
            days=1
        )

    return counts


def choose_positions(
    daily_counts,
    target,
    rng
):
    total = sum(
        item["count"]
        for item in daily_counts
    )

    if total < target:

        raise RuntimeError(
            f"Only {total:,} observations "
            f"available for target "
            f"sample of {target}."
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

        day_end = (
            cumulative + count
        )

        while (
            position_index
            < len(positions)
            and positions[
                position_index
            ] < day_end
        ):

            position = (
                positions[
                    position_index
                ]
            )

            offset_in_day = (
                position - cumulative
            )

            page = (
                offset_in_day
                // PER_PAGE
            ) + 1

            offset_in_page = (
                offset_in_day
                % PER_PAGE
            )

            selections.append(
                {
                    "date": day,
                    "page": page,
                    "offset":
                        offset_in_page,
                }
            )

            position_index += 1

        cumulative = day_end

    return (
        selections,
        total
    )


def fetch_large_day_positions(
    taxon_id,
    day,
    selections,
):
    """
    Fetch selected positions from a day whose
    results extend beyond the normal 10,000-result
    pagination limit.

    Instead of walking every page with id_above,
    jump through the result set in 10,000-record
    blocks. Within each block, ordinary page
    pagination is used.
    """

    block_size = (
        MAX_STANDARD_PAGE
        * PER_PAGE
    )

    # Convert each requested page/offset into
    # absolute zero-based position.
    requested = []

    for selection in selections:

        absolute_position = (
            (selection["page"] - 1)
            * PER_PAGE
            + selection["offset"]
        )

        block_index = (
            absolute_position
            // block_size
        )

        position_in_block = (
            absolute_position
            % block_size
        )

        relative_page = (
            position_in_block
            // PER_PAGE
        ) + 1

        relative_offset = (
            position_in_block
            % PER_PAGE
        )

        requested.append(
            {
                "absolute_position":
                    absolute_position,

                "block_index":
                    block_index,

                "relative_page":
                    relative_page,

                "relative_offset":
                    relative_offset,
            }
        )

    requested.sort(
        key=lambda item:
            item[
                "absolute_position"
            ]
    )

    max_block = max(
        item["block_index"]
        for item in requested
    )

    print(
        "    Large day requires "
        f"{max_block + 1} "
        "10,000-record block(s)"
    )

    # boundary_ids[n] is the id_above value
    # used to enter block n.
    #
    # Block 0 starts at the beginning, so None.
    boundary_ids = {
        0: None
    }

    current_boundary = None

    for block_index in range(
        1,
        max_block + 1
    ):

        params = {
            "taxon_id":
                taxon_id,

            "created_d1":
                day.isoformat(),

            "created_d2":
                day.isoformat(),

            "per_page":
                PER_PAGE,

            "page":
                MAX_STANDARD_PAGE,

            "order_by":
                "id",

            "order":
                "asc",
        }

        if current_boundary is not None:
            params[
                "id_above"
            ] = current_boundary

        print(
            "    Finding boundary "
            f"for block "
            f"{block_index}..."
        )

        data = api_get(
            params
        )

        results = (
            data["results"]
        )

        if not results:

            raise RuntimeError(
                "Could not establish "
                f"block {block_index} "
                f"for {day}."
            )

        current_boundary = (
            results[-1]["id"]
        )

        boundary_ids[
            block_index
        ] = current_boundary

        print(
            "      Boundary ID:",
            current_boundary
        )

    # Group requested observations by
    # block and relative page.
    page_groups = defaultdict(
        list
    )

    for item in requested:

        key = (
            item["block_index"],
            item["relative_page"],
        )

        page_groups[
            key
        ].append(
            item
        )

    found = {}

    for (
        block_index,
        relative_page
    ) in sorted(
        page_groups
    ):

        params = {
            "taxon_id":
                taxon_id,

            "created_d1":
                day.isoformat(),

            "created_d2":
                day.isoformat(),

            "per_page":
                PER_PAGE,

            "page":
                relative_page,

            "order_by":
                "id",

            "order":
                "asc",
        }

        boundary = (
            boundary_ids[
                block_index
            ]
        )

        if boundary is not None:
            params[
                "id_above"
            ] = boundary

        print(
            "    Fetching block "
            f"{block_index + 1}, "
            f"page {relative_page}"
        )

        data = api_get(
            params
        )

        results = (
            data["results"]
        )

        for item in page_groups[
            (
                block_index,
                relative_page,
            )
        ]:

            offset = (
                item[
                    "relative_offset"
                ]
            )

            if offset >= len(
                results
            ):

                raise RuntimeError(
                    "Sampling offset "
                    f"{offset} missing "
                    f"for {day}, "
                    f"block "
                    f"{block_index + 1}, "
                    f"page "
                    f"{relative_page}."
                )

            found[
                item[
                    "absolute_position"
                ]
            ] = (
                results[offset]
            )

    missing = [
        item[
            "absolute_position"
        ]
        for item in requested
        if item[
            "absolute_position"
        ] not in found
    ]

    if missing:

        raise RuntimeError(
            "Could not resolve "
            "large-day positions "
            f"{missing} "
            f"for {day}."
        )

    return [
        found[
            item[
                "absolute_position"
            ]
        ]
        for item in requested
    ]

def fetch_selected_observations(
    taxon_id,
    selections
):
    grouped = defaultdict(list)

    for selection in selections:

        day = selection["date"]

        grouped[
            day
        ].append(
            selection
        )

    observations = []

    days = sorted(
        grouped
    )

    print(
        "Selected days to fetch:",
        len(days)
    )

    for day_number, day in enumerate(
        days,
        start=1
    ):

        day_selections = (
            grouped[day]
        )

        max_page = max(
            selection["page"]
            for selection
            in day_selections
        )

        print(
            f"  Day "
            f"{day_number}/"
            f"{len(days)}: "
            f"{day} "
            f"(max page {max_page})"
        )

        if (
            max_page
            > MAX_STANDARD_PAGE
        ):

            print(
                "    Using "
                "id_above pagination"
            )

            day_observations = (
                fetch_large_day_positions(
                    taxon_id,
                    day,
                    day_selections
                )
            )

            observations.extend(
                day_observations
            )

            continue

        page_groups = defaultdict(
            list
        )

        for selection in day_selections:

            page_groups[
                selection["page"]
            ].append(
                selection["offset"]
            )

        for page in sorted(
            page_groups
        ):

            offsets = (
                page_groups[
                    page
                ]
            )

            print(
                f"    Fetching "
                f"page {page}"
            )

            data = api_get(
                {
                    "taxon_id":
                        taxon_id,

                    "created_d1":
                        day.isoformat(),

                    "created_d2":
                        day.isoformat(),

                    "per_page":
                        PER_PAGE,

                    "page":
                        page,

                    "order_by":
                        "id",

                    "order":
                        "asc",
                }
            )

            results = (
                data["results"]
            )

            for offset in sorted(
                offsets
            ):

                if offset >= len(
                    results
                ):

                    raise RuntimeError(
                        f"Sampling offset "
                        f"{offset} missing "
                        f"for {day}, "
                        f"page {page}."
                    )

                observations.append(
                    results[
                        offset
                    ]
                )

    return observations


def make_row(
    observation,
    sampling_month
):
    taxon = (
        observation.get("taxon")
        or {}
    )

    geojson = (
        observation.get("geojson")
    )

    if geojson:

        coordinates = (
            geojson.get(
                "coordinates",
                ["", ""]
            )
        )

        longitude = (
            coordinates[0]
        )

        latitude = (
            coordinates[1]
        )

    else:

        latitude = ""
        longitude = ""

    return {
        "sampling_month":
            sampling_month,

        "observation_id":
            observation["id"],

        "observation_uuid":
            observation["uuid"],

        "observer_id":
            observation.get(
                "user_id",
                ""
            ),

        "created_at":
            observation.get(
                "created_at",
                ""
            ),

        "observed_on":
            observation.get(
                "observed_on",
                ""
            ),

        "taxon_id":
            taxon.get(
                "id",
                ""
            ),

        "taxon_name":
            taxon.get(
                "name",
                ""
            ),

        "taxon_rank":
            taxon.get(
                "rank",
                ""
            ),

        "community_taxon_id":
            observation.get(
                "community_taxon_id",
                ""
            ),

        "quality_grade":
            observation.get(
                "quality_grade",
                ""
            ),

        "photo_count":
            len(
                observation.get(
                    "photos",
                    []
                )
            ),

        "identifications_count":
            observation.get(
                "identifications_count",
                ""
            ),

        "identification_agreements":
            observation.get(
                "num_identification_agreements",
                ""
            ),

        "identification_disagreements":
            observation.get(
                "num_identification_disagreements",
                ""
            ),

        "latitude":
            latitude,

        "longitude":
            longitude,

        "project_count":
            len(
                observation.get(
                    "project_ids",
                    []
                )
            ),
    }


def main():
    args = parse_args()

    start_date = parse_date(
        args.start_date
    )

    end_date = parse_date(
        args.end_date
    )

    if end_date < start_date:
        raise RuntimeError(
            "End date must not "
            "precede start date."
        )

    seed = (
        args.seed
        if args.seed is not None
        else args.taxon_id
    )

    rng = random.Random(
        seed
    )

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    os.makedirs(
        CACHE_DIR,
        exist_ok=True
    )

    slug = slugify(
        args.taxon_name
    )

    cache_file = os.path.join(
        CACHE_DIR,
        f"{args.taxon_id}"
        "_daily_counts.json"
    )

    output_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}.csv"
    )

    months = list(
        month_ranges(
            start_date,
            end_date
        )
    )

    if not months:
        raise RuntimeError(
            "No months in date range."
        )

    base = (
        args.sample_size
        // len(months)
    )

    remainder = (
        args.sample_size
        % len(months)
    )

    all_rows = []

    print(
        "Taxon:",
        args.taxon_name
    )

    print(
        "Taxon ID:",
        args.taxon_id
    )

    print(
        "Sample size:",
        args.sample_size
    )

    print(
        "Date range:",
        start_date,
        "to",
        end_date
    )

    print(
        "Random seed:",
        seed
    )

    for index, (
        month_start,
        month_end
    ) in enumerate(
        months
    ):

        target = base

        if index < remainder:
            target += 1

        print()
        print(
            f"{month_start:%B %Y}"
        )

        print(
            "Target sample:",
            target
        )

        print(
            "Counting observations "
            "by day..."
        )

        daily_counts = (
            get_daily_counts(
                args.taxon_id,
                month_start,
                month_end,
                cache_file
            )
        )

        (
            selections,
            month_total,
        ) = choose_positions(
            daily_counts,
            target,
            rng
        )

        print(
            "Month population:",
            f"{month_total:,}"
        )

        print(
            "Fetching selected "
            "observations..."
        )

        observations = (
            fetch_selected_observations(
                args.taxon_id,
                selections
            )
        )

        print(
            "Selected:",
            len(observations)
        )

        sampling_month = (
            month_start.strftime(
                "%Y-%m"
            )
        )

        for observation in observations:

            all_rows.append(
                make_row(
                    observation,
                    sampling_month
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
        writer.writerows(
            all_rows
        )

    unique_ids = {
        row["observation_id"]
        for row in all_rows
    }

    print()
    print(
        "Pilot sample complete"
    )

    print(
        "Rows:",
        len(all_rows)
    )

    print(
        "Unique observations:",
        len(unique_ids)
    )

    print(
        "Output:",
        output_file
    )


if __name__ == "__main__":
    main()