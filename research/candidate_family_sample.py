import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    REPO_ROOT
    / "research"
    / "data"
)

SCREEN_PATH = (
    DATA_DIR
    / "candidate_family_screen.csv"
)

OUTPUT_PATH = (
    DATA_DIR
    / "candidate_family_sample_100.csv"
)

CACHE_PATH = (
    REPO_ROOT
    / "research"
    / "cache"
    / "candidate_family_sample_cache.json"
)

API_BASE = (
    "https://api.inaturalist.org/v1/observations"
)

REQUEST_DELAY = 1.1

MONTHS = [
    ("2025-01", "2025-01-01", "2025-01-31", 17),
    ("2025-02", "2025-02-01", "2025-02-28", 17),
    ("2025-03", "2025-03-01", "2025-03-31", 17),
    ("2025-04", "2025-04-01", "2025-04-30", 17),
    ("2025-05", "2025-05-01", "2025-05-31", 16),
    ("2025-06", "2025-06-01", "2025-06-30", 16),
]


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def load_families():
    with SCREEN_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    rows = [
        row
        for row in rows
        if row["resolved"] == "1"
    ]

    print(
        f"Candidate families loaded: "
        f"{len(rows)}"
    )

    return rows


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
                "candidate-family-sample"
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
                    f"    HTTP 429; retrying "
                    f"in {delay}s..."
                )

                time.sleep(delay)
                continue

            raise


def fetch_month_sample(
    taxon_id,
    month,
    start,
    end,
    sample_n,
    cache,
):
    key = (
        f"{taxon_id}|{month}|"
        f"{sample_n}"
    )

    if key in cache:
        print(
            f"  {month}: "
            f"{len(cache[key])} "
            f"(cached)"
        )

        return cache[key]

    params = {
        "taxon_id": taxon_id,
        "created_d1": start,
        "created_d2": (
            f"{end}T23:59:59"
        ),
        "order_by": "random",
        "per_page": sample_n,
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

    if len(results) != sample_n:
        raise ValueError(
            f"{taxon_id} {month}: "
            f"wanted {sample_n}, "
            f"received {len(results)}"
        )

    cache[key] = results
    save_cache(cache)

    print(
        f"  {month}: "
        f"{len(results)}"
    )

    return results


def observation_row(
    family,
    month,
    observation,
):
    user = (
        observation.get("user")
        or {}
    )

    taxon = (
        observation.get("taxon")
        or {}
    )

    photos = (
        observation.get("photos")
        or []
    )

    project_ids = (
        observation.get("project_ids")
        or []
    )

    return {
        "family":
            family["family"],
        "broad_group":
            family["broad_group"],
        "family_taxon_id":
            family["taxon_id"],
        "sampling_month":
            month,

        "observation_id":
            clean(
                observation.get("id")
            ),
        "observation_uuid":
            clean(
                observation.get("uuid")
            ),
        "observer_id":
            clean(
                user.get("id")
            ),

        "created_at":
            clean(
                observation.get(
                    "created_at"
                )
            ),
        "observed_on":
            clean(
                observation.get(
                    "observed_on"
                )
            ),

        "current_taxon_id":
            clean(
                taxon.get("id")
            ),
        "current_taxon_name":
            clean(
                taxon.get("name")
            ),
        "current_taxon_rank":
            clean(
                taxon.get("rank")
            ),

        "quality_grade":
            clean(
                observation.get(
                    "quality_grade"
                )
            ),

        "photo_count":
            len(photos),

        "project_count":
            len(project_ids),
    }


def build_sample(families):
    cache = load_cache()

    rows = []
    seen_uuids = set()

    for index, family in enumerate(
        families,
        start=1,
    ):
        name = family["family"]
        taxon_id = family["taxon_id"]

        print(
            f"\n[{index}/{len(families)}] "
            f"{name} ({taxon_id})"
        )

        family_rows = []

        for (
            month,
            start,
            end,
            sample_n,
        ) in MONTHS:
            observations = (
                fetch_month_sample(
                    taxon_id,
                    month,
                    start,
                    end,
                    sample_n,
                    cache,
                )
            )

            for observation in observations:
                row = observation_row(
                    family,
                    month,
                    observation,
                )

                uuid = row[
                    "observation_uuid"
                ]

                if not uuid:
                    raise ValueError(
                        f"{name}: observation "
                        f"without UUID"
                    )

                if uuid in seen_uuids:
                    raise ValueError(
                        "Duplicate observation "
                        f"UUID: {uuid}"
                    )

                seen_uuids.add(uuid)
                family_rows.append(row)

        if len(family_rows) != 100:
            raise ValueError(
                f"{name}: expected 100 "
                f"observations, got "
                f"{len(family_rows)}"
            )

        rows.extend(
            family_rows
        )

        print(
            f"  Total: "
            f"{len(family_rows)}"
        )

    return rows


def write_output(rows):
    if not rows:
        raise ValueError(
            "No sample rows produced."
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
    family_counts = {}

    for row in rows:
        family = row["family"]

        family_counts[family] = (
            family_counts.get(
                family,
                0,
            )
            + 1
        )

    print(
        "\nCANDIDATE SCREENING SAMPLE"
    )
    print(
        "=========================="
    )

    print(
        f"Families: "
        f"{len(family_counts)}"
    )

    print(
        f"Observations: "
        f"{len(rows):,}"
    )

    print(
        f"Unique UUIDs: "
        f"{len(set(
            row['observation_uuid']
            for row in rows
        )):,}"
    )

    bad = [
        family
        for family, count
        in family_counts.items()
        if count != 100
    ]

    if bad:
        print(
            "WARNING: families without "
            "exactly 100 observations:"
        )

        for family in bad:
            print(
                f"  {family}: "
                f"{family_counts[family]}"
            )
    else:
        print(
            "All families have exactly "
            "100 observations."
        )


def main():
    if not SCREEN_PATH.exists():
        raise FileNotFoundError(
            f"Missing candidate screen: "
            f"{SCREEN_PATH}"
        )

    families = load_families()

    rows = build_sample(
        families
    )

    write_output(
        rows
    )

    print_summary(
        rows
    )

    print(
        "\nFixed screening sample "
        "written to:"
    )
    print(
        f"  {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()