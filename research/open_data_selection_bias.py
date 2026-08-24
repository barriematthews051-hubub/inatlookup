import csv
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "research" / "data"

AUDIT_PATH = (
    DATA_DIR / "open_data_audit_details.csv"
)

OUTPUT_PATH = (
    DATA_DIR / "open_data_selection_bias.csv"
)

FAMILIES = [
    "syrphidae",
    "asilidae",
    "geometridae",
    "nymphalidae",
    "staphylinidae",
    "asteraceae",
]


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


def percent(numerator, denominator):
    if denominator == 0:
        return 0.0

    return 100.0 * numerator / denominator


def load_open_data_presence():
    if not AUDIT_PATH.exists():
        raise FileNotFoundError(
            f"Missing audit file: {AUDIT_PATH}"
        )

    presence = {}

    with AUDIT_PATH.open(
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
                continue

            presence[uuid] = as_int(
                row["open_data_present"]
            )

    print(
        f"Loaded Open Data status for "
        f"{len(presence):,} observations."
    )

    return presence


def load_analysis_rows(presence):
    rows = []

    for family in FAMILIES:
        path = (
            DATA_DIR
            / f"{family}_pilot_500_analysis.csv"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Missing analysis file: {path}"
            )

        family_count = 0

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

                if uuid not in presence:
                    raise ValueError(
                        "Observation missing from "
                        "Open Data audit: "
                        f"{uuid}"
                    )

                row["_family"] = family
                row["_open_data_present"] = (
                    presence[uuid]
                )

                rows.append(row)
                family_count += 1

        print(
            f"  {family:<18} "
            f"{family_count:>4}"
        )

    print(
        f"\nMerged pilot observations: "
        f"{len(rows):,}"
    )

    return rows


def received_external_id(row):
    count = as_int(
        row.get(
            "external_history_count"
        )
    )

    if count is None:
        return None

    return int(count > 0)


def community_outcome(row):
    rank = clean(
        row.get(
            "community_taxon_rank"
        )
    ).lower()

    if rank == "":
        return "no_ct"

    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    return "higher"


def owner_rank(row):
    rank = clean(
        row.get(
            "first_owner_rank"
        )
    ).lower()

    if rank == "":
        return "none"

    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    return "higher"


def project_flag(row):
    count = as_int(
        row.get("project_count")
    )

    if count is None:
        return None

    return int(count > 0)


def photo_group(row):
    count = as_int(
        row.get("photo_count")
    )

    if count is None:
        return "unknown"

    if count <= 1:
        return "1_or_less"

    if count == 2:
        return "2"

    if count == 3:
        return "3"

    return "4_plus"


def summarize_rows(
    family,
    status,
    rows,
):
    n = len(rows)

    external_values = [
        received_external_id(row)
        for row in rows
    ]

    external_values = [
        value
        for value in external_values
        if value is not None
    ]

    external_n = sum(
        external_values
    )

    outcomes = defaultdict(int)

    for row in rows:
        outcomes[
            community_outcome(row)
        ] += 1

    project_values = [
        project_flag(row)
        for row in rows
    ]

    project_values = [
        value
        for value in project_values
        if value is not None
    ]

    project_n = sum(
        project_values
    )

    photos = defaultdict(int)

    for row in rows:
        photos[
            photo_group(row)
        ] += 1

    owners = defaultdict(int)

    for row in rows:
        owners[
            owner_rank(row)
        ] += 1

    identification_counts = [
        as_int(
            row.get(
                "identifications_count"
            )
        )
        for row in rows
    ]

    identification_counts = [
        value
        for value in identification_counts
        if value is not None
    ]

    if identification_counts:
        mean_identifications = (
            sum(identification_counts)
            / len(identification_counts)
        )
    else:
        mean_identifications = 0.0

    return {
        "family": family,
        "open_data_status": status,
        "n": n,

        "received_external_id_n":
            external_n,
        "received_external_id_pct":
            f"{percent(
                external_n,
                len(external_values),
            ):.1f}",

        "species_ct_n":
            outcomes["species"],
        "species_ct_pct":
            f"{percent(
                outcomes['species'],
                n,
            ):.1f}",

        "genus_ct_n":
            outcomes["genus"],
        "genus_ct_pct":
            f"{percent(
                outcomes['genus'],
                n,
            ):.1f}",

        "higher_ct_n":
            outcomes["higher"],
        "higher_ct_pct":
            f"{percent(
                outcomes['higher'],
                n,
            ):.1f}",

        "no_ct_n":
            outcomes["no_ct"],
        "no_ct_pct":
            f"{percent(
                outcomes['no_ct'],
                n,
            ):.1f}",

        "project_n":
            project_n,
        "project_pct":
            f"{percent(
                project_n,
                len(project_values),
            ):.1f}",

        "photo_1_or_less_n":
            photos["1_or_less"],
        "photo_1_or_less_pct":
            f"{percent(
                photos['1_or_less'],
                n,
            ):.1f}",

        "photo_2_n":
            photos["2"],
        "photo_2_pct":
            f"{percent(
                photos['2'],
                n,
            ):.1f}",

        "photo_3_n":
            photos["3"],
        "photo_3_pct":
            f"{percent(
                photos['3'],
                n,
            ):.1f}",

        "photo_4_plus_n":
            photos["4_plus"],
        "photo_4_plus_pct":
            f"{percent(
                photos['4_plus'],
                n,
            ):.1f}",

        "owner_species_n":
            owners["species"],
        "owner_species_pct":
            f"{percent(
                owners['species'],
                n,
            ):.1f}",

        "owner_genus_n":
            owners["genus"],
        "owner_genus_pct":
            f"{percent(
                owners['genus'],
                n,
            ):.1f}",

        "owner_higher_n":
            owners["higher"],
        "owner_higher_pct":
            f"{percent(
                owners['higher'],
                n,
            ):.1f}",

        "owner_none_n":
            owners["none"],
        "owner_none_pct":
            f"{percent(
                owners['none'],
                n,
            ):.1f}",

        "mean_identifications_count":
            f"{mean_identifications:.2f}",
    }


def build_summary(rows):
    summary = []

    groups = [
        ("ALL", rows)
    ]

    for family in FAMILIES:
        family_rows = [
            row
            for row in rows
            if row["_family"] == family
        ]

        groups.append(
            (family, family_rows)
        )

    for family, group_rows in groups:
        present = [
            row
            for row in group_rows
            if row["_open_data_present"] == 1
        ]

        absent = [
            row
            for row in group_rows
            if row["_open_data_present"] == 0
        ]

        summary.append(
            summarize_rows(
                family,
                "present",
                present,
            )
        )

        summary.append(
            summarize_rows(
                family,
                "absent",
                absent,
            )
        )

    return summary


def write_summary(summary):
    if not summary:
        raise ValueError(
            "No summary rows produced."
        )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(
                summary[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(summary)


def get_pair(summary, family):
    matching = [
        row
        for row in summary
        if row["family"] == family
    ]

    pair = {
        row["open_data_status"]: row
        for row in matching
    }

    return (
        pair["present"],
        pair["absent"],
    )


def print_main_table(summary):
    print(
        "\nOPEN DATA SELECTION-BIAS CHECK"
    )
    print(
        "=============================="
    )

    print(
        f"{'Family':<18}"
        f"{'N in':>7}"
        f"{'N out':>8}"
        f"{'Ext in':>9}"
        f"{'Ext out':>9}"
        f"{'Sp in':>9}"
        f"{'Sp out':>9}"
        f"{'NoCT in':>10}"
        f"{'NoCT out':>10}"
    )

    print("-" * 89)

    families = [
        "ALL",
        *FAMILIES,
    ]

    for family in families:
        present, absent = get_pair(
            summary,
            family,
        )

        print(
            f"{family:<18}"
            f"{present['n']:>7}"
            f"{absent['n']:>8}"
            f"{present[
                'received_external_id_pct'
            ] + '%':>9}"
            f"{absent[
                'received_external_id_pct'
            ] + '%':>9}"
            f"{present[
                'species_ct_pct'
            ] + '%':>9}"
            f"{absent[
                'species_ct_pct'
            ] + '%':>9}"
            f"{present[
                'no_ct_pct'
            ] + '%':>10}"
            f"{absent[
                'no_ct_pct'
            ] + '%':>10}"
        )


def print_secondary_table(summary):
    print(
        "\nPOTENTIAL SELECTION VARIABLES"
    )
    print(
        "============================="
    )

    print(
        f"{'Family':<18}"
        f"{'Proj in':>9}"
        f"{'Proj out':>10}"
        f"{'OwnerSp in':>12}"
        f"{'OwnerSp out':>13}"
        f"{'IDs in':>9}"
        f"{'IDs out':>10}"
    )

    print("-" * 81)

    families = [
        "ALL",
        *FAMILIES,
    ]

    for family in families:
        present, absent = get_pair(
            summary,
            family,
        )

        print(
            f"{family:<18}"
            f"{present[
                'project_pct'
            ] + '%':>9}"
            f"{absent[
                'project_pct'
            ] + '%':>10}"
            f"{present[
                'owner_species_pct'
            ] + '%':>12}"
            f"{absent[
                'owner_species_pct'
            ] + '%':>13}"
            f"{present[
                'mean_identifications_count'
            ]:>9}"
            f"{absent[
                'mean_identifications_count'
            ]:>10}"
        )


def main():
    presence = load_open_data_presence()

    print(
        "\nLoading and merging "
        "six pilot analysis files..."
    )

    rows = load_analysis_rows(
        presence
    )

    summary = build_summary(
        rows
    )

    write_summary(
        summary
    )

    print_main_table(
        summary
    )

    print_secondary_table(
        summary
    )

    print(
        "\nFull summary written to:"
    )
    print(
        f"  {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()