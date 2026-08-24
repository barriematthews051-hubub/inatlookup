import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    REPO_ROOT
    / "research"
    / "data"
)

SAMPLE_PATH = (
    DATA_DIR
    / "candidate_family_sample_100.csv"
)

SCREEN_PATH = (
    DATA_DIR
    / "candidate_family_screen.csv"
)

OUTPUT_PATH = (
    DATA_DIR
    / "candidate_family_screen_stage3.csv"
)

CACHE_PATH = (
    REPO_ROOT
    / "research"
    / "cache"
    / "candidate_family_owner_rank_cache.json"
)

API_BASE = (
    "https://api.inaturalist.org/v1/identifications"
)

REQUEST_DELAY = 1.1
BATCH_SIZE = 50
PER_PAGE = 200


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def as_int(value):
    value = clean(value)

    if value == "":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def load_sample():
    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"Missing screening sample: "
            f"{SAMPLE_PATH}"
        )

    with SAMPLE_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    if len(rows) != 3600:
        raise ValueError(
            f"Expected 3,600 observations, "
            f"found {len(rows):,}"
        )

    return rows


def load_screen():
    if not SCREEN_PATH.exists():
        raise FileNotFoundError(
            f"Missing candidate screen: "
            f"{SCREEN_PATH}"
        )

    with SCREEN_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def load_cache():
    if not CACHE_PATH.exists():
        return {}

    with CACHE_PATH.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def save_cache(cache):
    CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CACHE_PATH.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            cache,
            handle,
            indent=2,
            sort_keys=True,
        )


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "inatlookup-research-pilot/0.4 "
                "candidate-family-owner-screen"
            ),
        },
    )

    delays = [
        5,
        10,
        20,
        40,
        60,
    ]

    for attempt in range(
        len(delays) + 1
    ):
        try:
            with urllib.request.urlopen(
                request,
                timeout=60,
            ) as response:
                payload = json.load(
                    response
                )

            time.sleep(
                REQUEST_DELAY
            )

            return payload

        except urllib.error.HTTPError as exc:
            if (
                exc.code == 429
                and attempt < len(delays)
            ):
                delay = delays[attempt]

                print(
                    f"  HTTP 429; retrying "
                    f"in {delay}s..."
                )

                time.sleep(delay)
                continue

            raise


def parse_time(value):
    value = clean(value)

    if not value:
        return datetime.max

    value = value.replace(
        "Z",
        "+00:00",
    )

    try:
        return datetime.fromisoformat(
            value
        )
    except ValueError:
        return datetime.max


def normalized_rank(rank):
    rank = clean(rank).lower()

    if rank == "":
        return "none"

    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    return "higher"


def chunks(items, size):
    for start in range(
        0,
        len(items),
        size,
    ):
        yield items[
            start:start + size
        ]


def fetch_batch_identifications(
    observation_ids,
):
    all_results = []
    page = 1

    while True:
        params = {
            "observation_id":
                ",".join(
                    str(obs_id)
                    for obs_id
                    in observation_ids
                ),
            "current": "any",
            "per_page": PER_PAGE,
            "page": page,
        }

        url = (
            API_BASE
            + "?"
            + urllib.parse.urlencode(
                params
            )
        )

        payload = fetch_json(url)

        results = payload.get(
            "results",
            [],
        )

        all_results.extend(
            results
        )

        if len(results) < PER_PAGE:
            break

        page += 1

    return all_results


def owner_rank_for_identification(
    identification,
):
    taxon = (
        identification.get("taxon")
        or {}
    )

    return normalized_rank(
        taxon.get("rank")
    )


def build_owner_rank_cache(sample):
    cache = load_cache()

    observation_lookup = {}

    for row in sample:
        obs_id = as_int(
            row["observation_id"]
        )

        observer_id = as_int(
            row["observer_id"]
        )

        if obs_id is None:
            raise ValueError(
                "Observation without numeric ID."
            )

        if observer_id is None:
            raise ValueError(
                f"Observation {obs_id} "
                f"without observer ID."
            )

        observation_lookup[obs_id] = {
            "observer_id":
                observer_id,
            "family":
                row["family"],
        }

    missing_ids = [
        obs_id
        for obs_id in observation_lookup
        if str(obs_id) not in cache
    ]

    print(
        f"Cached owner-rank results: "
        f"{len(cache):,}"
    )
    print(
        f"Observations requiring lookup: "
        f"{len(missing_ids):,}"
    )

    batches = list(
        chunks(
            missing_ids,
            BATCH_SIZE,
        )
    )

    for batch_number, batch_ids in enumerate(
        batches,
        start=1,
    ):
        print(
            f"Batch "
            f"{batch_number}/{len(batches)} "
            f"({len(batch_ids)} observations)"
        )

        identifications = (
            fetch_batch_identifications(
                batch_ids
            )
        )

        by_observation = defaultdict(list)

        for identification in identifications:
            observation = (
                identification.get(
                    "observation"
                )
                or {}
            )

            obs_id = as_int(
                observation.get("id")
            )

            if obs_id in observation_lookup:
                by_observation[
                    obs_id
                ].append(
                    identification
                )

        for obs_id in batch_ids:
            observer_id = (
                observation_lookup[
                    obs_id
                ]["observer_id"]
            )

            owner_identifications = []

            for identification in (
                by_observation.get(
                    obs_id,
                    []
                )
            ):
                user = (
                    identification.get(
                        "user"
                    )
                    or {}
                )

                identifier_id = as_int(
                    user.get("id")
                )

                if identifier_id == observer_id:
                    owner_identifications.append(
                        identification
                    )

            if owner_identifications:
                first_owner = min(
                    owner_identifications,
                    key=lambda item: (
                        parse_time(
                            item.get(
                                "created_at"
                            )
                        )
                    ),
                )

                cache[str(obs_id)] = {
                    "first_owner_rank":
                        owner_rank_for_identification(
                            first_owner
                        ),
                    "first_owner_created_at":
                        clean(
                            first_owner.get(
                                "created_at"
                            )
                        ),
                    "owner_history_count":
                        len(
                            owner_identifications
                        ),
                }

            else:
                cache[str(obs_id)] = {
                    "first_owner_rank": "none",
                    "first_owner_created_at": "",
                    "owner_history_count": 0,
                }

        save_cache(cache)

    return cache


def photo_group(count):
    if count <= 1:
        return "1_or_less"

    if count == 2:
        return "2"

    if count == 3:
        return "3"

    return "4_plus"


def percent(numerator, denominator):
    if denominator == 0:
        return 0.0

    return (
        100.0
        * numerator
        / denominator
    )


def summarize_sample(
    sample,
    owner_cache,
):
    by_family = defaultdict(list)

    for row in sample:
        by_family[
            row["family"]
        ].append(row)

    summary = {}

    for family, rows in by_family.items():
        owner_counts = defaultdict(int)
        photo_counts = defaultdict(int)

        photo_total = 0

        for row in rows:
            obs_id = clean(
                row["observation_id"]
            )

            owner = owner_cache[
                obs_id
            ]

            rank = owner[
                "first_owner_rank"
            ]

            owner_counts[
                rank
            ] += 1

            count = as_int(
                row["photo_count"]
            )

            if count is None:
                count = 0

            photo_total += count

            photo_counts[
                photo_group(count)
            ] += 1

        n = len(rows)

        summary[family] = {
            "screen_sample_n": n,

            "owner_species_pct":
                f"{percent(
                    owner_counts['species'],
                    n,
                ):.1f}",

            "owner_genus_pct":
                f"{percent(
                    owner_counts['genus'],
                    n,
                ):.1f}",

            "owner_higher_pct":
                f"{percent(
                    owner_counts['higher'],
                    n,
                ):.1f}",

            "owner_none_pct":
                f"{percent(
                    owner_counts['none'],
                    n,
                ):.1f}",

            "mean_photo_count":
                f"{photo_total / n:.2f}",

            "photo_1_or_less_pct":
                f"{percent(
                    photo_counts['1_or_less'],
                    n,
                ):.1f}",

            "photo_2_pct":
                f"{percent(
                    photo_counts['2'],
                    n,
                ):.1f}",

            "photo_3_pct":
                f"{percent(
                    photo_counts['3'],
                    n,
                ):.1f}",

            "photo_4_plus_pct":
                f"{percent(
                    photo_counts['4_plus'],
                    n,
                ):.1f}",
        }

    return summary


def merge_screen(
    screen_rows,
    sample_summary,
):
    rows = []

    for row in screen_rows:
        family = row["family"]

        merged = dict(row)

        extra = sample_summary.get(
            family,
            {}
        )

        merged.update(extra)

        rows.append(
            merged
        )

    return rows


def write_output(rows):
    if not rows:
        raise ValueError(
            "No output rows."
        )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                rows[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows):
    print(
        "\nCANDIDATE OWNER / PHOTO SCREEN"
    )
    print(
        "=============================="
    )

    print(
        f"{'Family':<18}"
        f"{'OwnerSp':>9}"
        f"{'OwnerGen':>10}"
        f"{'OwnerHi':>9}"
        f"{'OwnerNone':>11}"
        f"{'MeanPic':>9}"
        f"{'4+Pic':>9}"
    )

    print("-" * 75)

    for row in rows:
        print(
            f"{row['family']:<18}"
            f"{row[
                'owner_species_pct'
            ] + '%':>9}"
            f"{row[
                'owner_genus_pct'
            ] + '%':>10}"
            f"{row[
                'owner_higher_pct'
            ] + '%':>9}"
            f"{row[
                'owner_none_pct'
            ] + '%':>11}"
            f"{row[
                'mean_photo_count'
            ]:>9}"
            f"{row[
                'photo_4_plus_pct'
            ] + '%':>9}"
        )


def main():
    sample = load_sample()
    screen = load_screen()

    print(
        f"Screening observations loaded: "
        f"{len(sample):,}"
    )

    owner_cache = (
        build_owner_rank_cache(
            sample
        )
    )

    sample_summary = (
        summarize_sample(
            sample,
            owner_cache,
        )
    )

    rows = merge_screen(
        screen,
        sample_summary,
    )

    write_output(
        rows
    )

    print_summary(
        rows
    )

    print(
        "\nStage-3 candidate table "
        "written to:"
    )
    print(
        f"  {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()