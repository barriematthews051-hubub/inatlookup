import csv
import gzip
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_DIR = REPO_ROOT / "research" / "data"

OPEN_DATA_DIR = Path(r"K:\inat-open-data")
PHOTOS_PATH = Path(
    r"C:\Users\Barrie\inat-data\photos.csv.gz"
)

OBSERVATIONS_PATH = (
    OPEN_DATA_DIR / "observations.csv.gz"
)
OBSERVATIONS_PROJECTS_PATH = (
    OPEN_DATA_DIR / "observations_projects.csv.gz"
)
OBSERVERS_PATH = (
    OPEN_DATA_DIR / "observers.csv.gz"
)
PROJECTS_PATH = (
    OPEN_DATA_DIR / "projects.csv.gz"
)
TAXA_PATH = (
    OPEN_DATA_DIR / "taxa.csv.gz"
)

DETAIL_OUTPUT = (
    PILOT_DIR / "open_data_audit_details.csv"
)
SUMMARY_OUTPUT = (
    PILOT_DIR / "open_data_audit_summary.csv"
)

FAMILIES = [
    "syrphidae",
    "asilidae",
    "geometridae",
    "nymphalidae",
    "staphylinidae",
    "asteraceae",
]

PROGRESS_EVERY = 5_000_000


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


def same_text(a, b):
    return clean(a) == clean(b)


def same_int(a, b):
    a_int = as_int(a)
    b_int = as_int(b)

    if a_int is None or b_int is None:
        return False

    return a_int == b_int


def load_pilot_observations():
    print("Loading six pilot analysis files...")

    pilot = {}

    for family in FAMILIES:
        path = (
            PILOT_DIR
            / f"{family}_pilot_500_analysis.csv"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Missing pilot file: {path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            reader = csv.DictReader(handle)

            for row in reader:
                uuid = clean(
                    row["observation_uuid"]
                )

                if not uuid:
                    raise ValueError(
                        f"Missing observation UUID "
                        f"in {path}"
                    )

                if uuid in pilot:
                    raise ValueError(
                        f"Duplicate observation UUID "
                        f"across pilot files: {uuid}"
                    )

                row["_family"] = family
                pilot[uuid] = row



        family_count = sum(
            1
            for r in pilot.values()
            if r["_family"] == family
        )

        print(
            f"  {family:<18} "
            f"{family_count:>4}"
        )






    print(
        f"\nTotal pilot observations: "
        f"{len(pilot):,}"
    )

    return pilot


def stream_open_observations(target_uuids):
    print(
        "\nScanning observations.csv.gz..."
    )

    found = {}
    rows_read = 0

    with gzip.open(
        OBSERVATIONS_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            rows_read += 1

            uuid = clean(
                row["observation_uuid"]
            )

            if uuid in target_uuids:
                found[uuid] = row

            if rows_read % PROGRESS_EVERY == 0:
                print(
                    f"  rows scanned: "
                    f"{rows_read:,}; "
                    f"pilot matches: "
                    f"{len(found):,}"
                )

    print(
        f"Finished observations scan: "
        f"{rows_read:,} rows"
    )
    print(
        f"Pilot observations found: "
        f"{len(found):,} / "
        f"{len(target_uuids):,}"
    )

    return found


def stream_open_photos(target_uuids):
    print(
        "\nScanning photos.csv.gz..."
    )

    photo_count = defaultdict(int)
    positions = defaultdict(list)

    rows_read = 0
    matched_rows = 0

    with gzip.open(
        PHOTOS_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            rows_read += 1

            uuid = clean(
                row["observation_uuid"]
            )

            if uuid in target_uuids:
                matched_rows += 1
                photo_count[uuid] += 1

                position = as_int(
                    row.get("position")
                )

                if position is not None:
                    positions[uuid].append(
                        position
                    )

            if rows_read % PROGRESS_EVERY == 0:
                print(
                    f"  rows scanned: "
                    f"{rows_read:,}; "
                    f"matching photo rows: "
                    f"{matched_rows:,}"
                )

    print(
        f"Finished photos scan: "
        f"{rows_read:,} rows"
    )
    print(
        f"Matching licensed-photo rows: "
        f"{matched_rows:,}"
    )

    return photo_count, positions


def stream_project_memberships(
    target_uuids,
):
    print(
        "\nScanning "
        "observations_projects.csv.gz..."
    )

    projects_by_obs = defaultdict(set)

    rows_read = 0
    matched_rows = 0

    with gzip.open(
        OBSERVATIONS_PROJECTS_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            rows_read += 1

            uuid = clean(
                row["observation_uuid"]
            )

            if uuid in target_uuids:
                matched_rows += 1

                project_id = clean(
                    row["project_id"]
                )

                if project_id:
                    projects_by_obs[uuid].add(
                        project_id
                    )

            if rows_read % PROGRESS_EVERY == 0:
                print(
                    f"  rows scanned: "
                    f"{rows_read:,}; "
                    f"matching memberships: "
                    f"{matched_rows:,}"
                )

    print(
        f"Finished project-membership scan: "
        f"{rows_read:,} rows"
    )
    print(
        f"Matching membership rows: "
        f"{matched_rows:,}"
    )

    return projects_by_obs


def load_projects():
    print(
        "\nLoading projects.csv.gz..."
    )

    projects = {}

    with gzip.open(
        PROJECTS_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            project_id = clean(
                row["project_id"]
            )

            if project_id:
                projects[project_id] = row

    print(
        f"Projects loaded: "
        f"{len(projects):,}"
    )

    return projects


def load_taxa():
    print(
        "\nLoading taxa.csv.gz..."
    )

    taxa = {}

    with gzip.open(
        TAXA_PATH,
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle,
            delimiter="\t",
        )

        for row in reader:
            taxon_id = clean(
                row["taxon_id"]
            )

            if taxon_id:
                taxa[taxon_id] = row

    print(
        f"Taxa loaded: "
        f"{len(taxa):,}"
    )

    return taxa


def build_detail_rows(
    pilot,
    open_observations,
    photo_counts,
    photo_positions,
    projects_by_obs,
    projects,
    taxa,
):
    rows = []

    for uuid, api in pilot.items():
        od = open_observations.get(uuid)

        present = od is not None

        if present:
            od_taxon_id = clean(
                od.get("taxon_id")
            )
            taxon = taxa.get(
                od_taxon_id,
                {},
            )
        else:
            od_taxon_id = ""
            taxon = {}

        positions = sorted(
            photo_positions.get(
                uuid,
                [],
            )
        )

        position_text = ";".join(
            str(position)
            for position in positions
        )

        project_ids = sorted(
            projects_by_obs.get(
                uuid,
                set(),
            )
        )

        unknown_project_ids = [
            project_id
            for project_id in project_ids
            if project_id not in projects
        ]

        api_photo_count = as_int(
            api.get("photo_count")
        )
        local_photo_count = (
            photo_counts.get(uuid, 0)
        )

        api_project_count = as_int(
            api.get("project_count")
        )
        local_project_count = len(
            project_ids
        )

        row = {
            "family": api["_family"],
            "observation_id":
                clean(api.get("observation_id")),
            "observation_uuid": uuid,

            "open_data_present":
                int(present),

            "api_observer_id":
                clean(api.get("observer_id")),
            "open_observer_id":
                clean(
                    od.get("observer_id")
                    if od else ""
                ),
            "observer_id_match":
                int(
                    present
                    and same_int(
                        api.get("observer_id"),
                        od.get("observer_id"),
                    )
                ),

            "api_observed_on":
                clean(api.get("observed_on")),
            "open_observed_on":
                clean(
                    od.get("observed_on")
                    if od else ""
                ),
            "observed_on_match":
                int(
                    present
                    and same_text(
                        api.get("observed_on"),
                        od.get("observed_on"),
                    )
                ),

            "api_quality_grade":
                clean(
                    api.get("quality_grade")
                ),
            "open_quality_grade":
                clean(
                    od.get("quality_grade")
                    if od else ""
                ),
            "quality_grade_match":
                int(
                    present
                    and same_text(
                        api.get(
                            "quality_grade"
                        ),
                        od.get(
                            "quality_grade"
                        ),
                    )
                ),

            "api_taxon_id":
                clean(api.get("taxon_id")),
            "api_taxon_name":
                clean(api.get("taxon_name")),
            "api_taxon_rank":
                clean(api.get("taxon_rank")),

            "api_community_taxon_id":
                clean(
                    api.get(
                        "community_taxon_id"
                    )
                ),
            "api_community_taxon_name":
                clean(
                    api.get(
                        "community_taxon_name"
                    )
                ),
            "api_community_taxon_rank":
                clean(
                    api.get(
                        "community_taxon_rank"
                    )
                ),

            "open_taxon_id":
                od_taxon_id,
            "open_taxon_name":
                clean(taxon.get("name")),
            "open_taxon_rank":
                clean(taxon.get("rank")),
            "open_taxon_active":
                clean(taxon.get("active")),

            "open_taxon_matches_api_taxon":
                int(
                    present
                    and same_int(
                        od_taxon_id,
                        api.get("taxon_id"),
                    )
                ),

            "open_taxon_matches_community_taxon":
                int(
                    present
                    and same_int(
                        od_taxon_id,
                        api.get(
                            "community_taxon_id"
                        ),
                    )
                ),

            "api_photo_count":
                (
                    api_photo_count
                    if api_photo_count
                    is not None
                    else ""
                ),
            "open_licensed_photo_count":
                local_photo_count,

            "photo_count_match":
                int(
                    present
                    and api_photo_count
                    is not None
                    and api_photo_count
                    == local_photo_count
                ),

            "open_photo_positions":
                position_text,

            "api_project_count":
                (
                    api_project_count
                    if api_project_count
                    is not None
                    else ""
                ),
            "open_project_count":
                local_project_count,

            "project_count_match":
                int(
                    present
                    and api_project_count
                    is not None
                    and api_project_count
                    == local_project_count
                ),

            "open_project_ids":
                ";".join(project_ids),

            "unknown_open_project_ids":
                ";".join(
                    unknown_project_ids
                ),

            "anomaly_score":
                clean(
                    od.get("anomaly_score")
                    if od else ""
                ),

            "anomaly_score_present":
                int(
                    present
                    and clean(
                        od.get("anomaly_score")
                    )
                    != ""
                ),
        }

        rows.append(row)

    return rows


def percent(numerator, denominator):
    if denominator == 0:
        return 0.0

    return (
        100.0
        * numerator
        / denominator
    )


def make_summary(detail_rows):
    summary = []

    groups = [
        ("ALL", detail_rows)
    ]

    for family in FAMILIES:
        family_rows = [
            row
            for row in detail_rows
            if row["family"] == family
        ]

        groups.append(
            (family, family_rows)
        )

    for name, rows in groups:
        n = len(rows)

        present_rows = [
            row
            for row in rows
            if row["open_data_present"]
        ]

        present_n = len(present_rows)

        def count_true(field):
            return sum(
                int(row[field])
                for row in rows
            )

        def count_true_present(field):
            return sum(
                int(row[field])
                for row in present_rows
            )

        summary.append({
            "family": name,
            "pilot_n": n,

            "open_data_present_n":
                present_n,
            "open_data_present_pct":
                f"{percent(present_n, n):.1f}",

            "observer_id_match_pct_present":
                f"{percent(
                    count_true_present(
                        'observer_id_match'
                    ),
                    present_n,
                ):.1f}",

            "observed_on_match_pct_present":
                f"{percent(
                    count_true_present(
                        'observed_on_match'
                    ),
                    present_n,
                ):.1f}",

            "quality_grade_match_pct_present":
                f"{percent(
                    count_true_present(
                        'quality_grade_match'
                    ),
                    present_n,
                ):.1f}",

            "open_taxon_matches_api_taxon_pct_present":
                f"{percent(
                    count_true_present(
                        'open_taxon_matches_api_taxon'
                    ),
                    present_n,
                ):.1f}",

            "open_taxon_matches_community_taxon_pct_present":
                f"{percent(
                    count_true_present(
                        'open_taxon_matches_community_taxon'
                    ),
                    present_n,
                ):.1f}",

            "photo_count_match_pct_present":
                f"{percent(
                    count_true_present(
                        'photo_count_match'
                    ),
                    present_n,
                ):.1f}",

            "project_count_match_pct_present":
                f"{percent(
                    count_true_present(
                        'project_count_match'
                    ),
                    present_n,
                ):.1f}",

            "anomaly_score_present_n":
                count_true(
                    "anomaly_score_present"
                ),

            "anomaly_score_present_pct":
                f"{percent(
                    count_true(
                        'anomaly_score_present'
                    ),
                    n,
                ):.1f}",
        })

    return summary


def write_csv(path, rows):
    if not rows:
        raise ValueError(
            f"No rows to write: {path}"
        )

    with path.open(
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


def print_summary(summary):
    print(
        "\nOPEN DATA COMPATIBILITY SUMMARY"
    )
    print(
        "==============================="
    )

    print(
        f"{'Family':<18}"
        f"{'Present':>10}"
        f"{'Taxon=API':>12}"
        f"{'Taxon=CT':>11}"
        f"{'Photos':>10}"
        f"{'Projects':>10}"
        f"{'Anomaly':>10}"
    )

    print("-" * 81)

    for row in summary:
        present = (
            f"{row['open_data_present_pct']}%"
        )
        taxon_api = (
            f"{row[
                'open_taxon_matches_api_taxon_pct_present'
            ]}%"
        )
        taxon_ct = (
            f"{row[
                'open_taxon_matches_community_taxon_pct_present'
            ]}%"
        )
        photos = (
            f"{row[
                'photo_count_match_pct_present'
            ]}%"
        )
        projects = (
            f"{row[
                'project_count_match_pct_present'
            ]}%"
        )
        anomaly = (
            f"{row[
                'anomaly_score_present_pct'
            ]}%"
        )

        print(
            f"{row['family']:<18}"
            f"{present:>10}"
            f"{taxon_api:>12}"
            f"{taxon_ct:>11}"
            f"{photos:>10}"
            f"{projects:>10}"
            f"{anomaly:>10}"
        )


def check_input_files():
    paths = [
        OBSERVATIONS_PATH,
        OBSERVATIONS_PROJECTS_PATH,
        OBSERVERS_PATH,
        PROJECTS_PATH,
        TAXA_PATH,
        PHOTOS_PATH,
    ]

    missing = [
        path
        for path in paths
        if not path.exists()
    ]

    if missing:
        print(
            "Missing required Open Data files:"
        )

        for path in missing:
            print(f"  {path}")

        raise SystemExit(1)


def main():
    check_input_files()

    pilot = load_pilot_observations()
    target_uuids = set(pilot)

    open_observations = (
        stream_open_observations(
            target_uuids
        )
    )

    photo_counts, photo_positions = (
        stream_open_photos(
            target_uuids
        )
    )

    projects_by_obs = (
        stream_project_memberships(
            target_uuids
        )
    )

    projects = load_projects()
    taxa = load_taxa()

    detail_rows = build_detail_rows(
        pilot,
        open_observations,
        photo_counts,
        photo_positions,
        projects_by_obs,
        projects,
        taxa,
    )

    summary = make_summary(
        detail_rows
    )

    write_csv(
        DETAIL_OUTPUT,
        detail_rows,
    )

    write_csv(
        SUMMARY_OUTPUT,
        summary,
    )

    print_summary(summary)

    print(
        "\nDetailed audit written to:"
    )
    print(
        f"  {DETAIL_OUTPUT}"
    )

    print(
        "\nSummary written to:"
    )
    print(
        f"  {SUMMARY_OUTPUT}"
    )


if __name__ == "__main__":
    main()