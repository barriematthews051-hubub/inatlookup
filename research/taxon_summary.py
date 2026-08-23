import argparse
import csv
import os
import re
from collections import Counter, defaultdict


DATA_DIR = "research/data"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Print a descriptive summary "
            "for a taxon pilot analysis."
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
        help="Pilot sample size. Default: 500.",
    )

    return parser.parse_args()


def slugify(text):
    text = text.strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    )

    return text.strip("_")


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(
            csv.DictReader(f)
        )


def percent(n, total):
    if total == 0:
        return 0.0

    return round(
        100 * n / total,
        1
    )


def photo_group(count):
    count = int(count)

    if count == 0:
        return "0"

    if count == 1:
        return "1"

    if count == 2:
        return "2"

    if count == 3:
        return "3"

    return "4+"


def main():
    args = parse_args()

    slug = slugify(
        args.taxon_name
    )

    input_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"analysis.csv"
    )

    if not os.path.exists(
        input_file
    ):
        raise RuntimeError(
            f"Analysis file not found: "
            f"{input_file}"
        )

    rows = load_csv(
        input_file
    )

    print()
    print(
        f"{args.taxon_name.upper()} "
        f"PILOT SUMMARY"
    )

    print(
        "=" * (
            len(args.taxon_name)
            + 14
        )
    )

    print()
    print(
        "Taxon ID:",
        args.taxon_id
    )

    print(
        "Observations:",
        len(rows)
    )

    outcomes = Counter(
        row["outcome_group"]
        for row in rows
    )

    print()
    print(
        "FINAL COMMUNITY TAXON OUTCOME"
    )

    for outcome in (
        "species",
        "genus",
        "other",
        "none",
    ):

        count = (
            outcomes[outcome]
        )

        print(
            f"  {outcome:<7} "
            f"{count:3d} "
            f"({percent(count,len(rows)):5.1f}%)"
        )

    print()
    print(
        "STAGE 1 - EXTERNAL ATTENTION"
    )

    print(
        "----------------------------"
    )

    attended = [
        row
        for row in rows
        if int(
            row[
                "external_history_count"
            ]
        ) > 0
    ]

    unattended = [
        row
        for row in rows
        if int(
            row[
                "external_history_count"
            ]
        ) == 0
    ]

    print(
        "Received external ID:",
        len(attended),
        f"({percent(len(attended),len(rows))}%)"
    )

    print(
        "No external ID:",
        len(unattended),
        f"({percent(len(unattended),len(rows))}%)"
    )

    none_rows = [
        row
        for row in rows
        if row[
            "outcome_group"
        ] == "none"
    ]

    none_unattended = sum(
        int(
            row[
                "external_history_count"
            ]
        ) == 0
        for row in none_rows
    )

    print(
        "No-CT observations with "
        "no external ID:",
        f"{none_unattended}/"
        f"{len(none_rows)} "
        f"({percent(none_unattended,len(none_rows))}%)"
    )

    project_attention = defaultdict(
        lambda: {
            "total": 0,
            "attended": 0,
        }
    )

    for row in rows:

        key = (
            "project"
            if int(
                row[
                    "project_count"
                ]
            ) > 0
            else "no_project"
        )

        project_attention[
            key
        ]["total"] += 1

        if int(
            row[
                "external_history_count"
            ]
        ) > 0:

            project_attention[
                key
            ]["attended"] += 1

    print()
    print(
        "External attention by project:"
    )

    for key in (
        "no_project",
        "project",
    ):

        total = (
            project_attention[
                key
            ]["total"]
        )

        attended_count = (
            project_attention[
                key
            ]["attended"]
        )

        print(
            f"  {key:<10} "
            f"{attended_count}/"
            f"{total} "
            f"({percent(attended_count,total)}%)"
        )

    print()
    print(
        "STAGE 2 - RESOLUTION "
        "AFTER EXTERNAL ATTENTION"
    )

    print(
        "-------------------------------------"
    )

    attended_outcomes = Counter(
        row[
            "outcome_group"
        ]
        for row in attended
    )

    for outcome in (
        "species",
        "genus",
        "other",
        "none",
    ):

        count = (
            attended_outcomes[
                outcome
            ]
        )

        print(
            f"  {outcome:<7} "
            f"{count:3d} "
            f"({percent(count,len(attended)):5.1f}%)"
        )

    print()
    print(
        "FIRST EXTERNAL RANK "
        "AND FINAL OUTCOME"
    )

    first_rank = defaultdict(
        Counter
    )

    for row in attended:

        rank = (
            row[
                "first_external_rank"
            ]
            or "NONE"
        )

        first_rank[
            rank
        ][
            row[
                "outcome_group"
            ]
        ] += 1

    ordered_ranks = sorted(
        first_rank,
        key=lambda rank:
            -sum(
                first_rank[
                    rank
                ].values()
            )
    )

    for rank in ordered_ranks[
        :8
    ]:

        counts = (
            first_rank[
                rank
            ]
        )

        total = sum(
            counts.values()
        )

        print(
            f"  {rank:<12} "
            f"N={total:3d}  "
            f"species="
            f"{counts['species']:3d} "
            f"({percent(counts['species'],total):4.1f}%)  "
            f"genus="
            f"{counts['genus']:3d} "
            f"({percent(counts['genus'],total):4.1f}%)"
        )

    print()
    print(
        "PHOTO COUNT VS SPECIES OUTCOME"
    )

    photo_stats = defaultdict(
        lambda: {
            "total": 0,
            "species": 0,
        }
    )

    for row in rows:

        group = photo_group(
            row[
                "photo_count"
            ]
        )

        photo_stats[
            group
        ]["total"] += 1

        if (
            row[
                "outcome_group"
            ]
            == "species"
        ):

            photo_stats[
                group
            ]["species"] += 1

    for group in (
        "1",
        "2",
        "3",
        "4+",
        "0",
    ):

        total = (
            photo_stats[
                group
            ]["total"]
        )

        if total == 0:
            continue

        species = (
            photo_stats[
                group
            ]["species"]
        )

        print(
            f"  Photos {group:<2} "
            f"{species:3d}/"
            f"{total:3d} "
            f"({percent(species,total):5.1f}%)"
        )

    print()
    print(
        "IDENTIFIER EXPERIENCE"
    )

    high_first = [
        row
        for row in attended
        if (
            row[
                "first_external_prior_taxon_ids"
            ]
            != ""
            and int(
                row[
                    "first_external_prior_taxon_ids"
                ]
            ) >= 10000
        )
    ]

    print(
        "First external identifier "
        "with >=10,000 prior "
        f"{args.taxon_name} IDs:",
        len(high_first),
        f"({percent(len(high_first),len(attended))}%)"
    )

    high_first_outcomes = Counter(
        row[
            "outcome_group"
        ]
        for row in high_first
    )

    for outcome in (
        "species",
        "genus",
        "other",
        "none",
    ):

        print(
            f"  {outcome}:",
            high_first_outcomes[
                outcome
            ]
        )

    print()
    print(
        "HISTORICAL IDENTIFICATION CHANGE"
    )

    owner_changed = sum(
        row[
            "owner_rank_changed"
        ] == "True"
        for row in rows
    )

    withdrawn = sum(
        int(
            row[
                "withdrawn_id_count"
            ]
        ) > 0
        for row in rows
    )

    disagreement = sum(
        row[
            "historical_disagreement"
        ] == "True"
        for row in rows
    )

    maverick = sum(
        row[
            "historical_maverick"
        ] == "True"
        for row in rows
    )

    print(
        "Owner changed rank:",
        owner_changed,
        f"({percent(owner_changed,len(rows))}%)"
    )

    print(
        "Observation with withdrawn ID:",
        withdrawn,
        f"({percent(withdrawn,len(rows))}%)"
    )

    print(
        "Historical disagreement:",
        disagreement,
        f"({percent(disagreement,len(rows))}%)"
    )

    print(
        "Historical maverick:",
        maverick,
        f"({percent(maverick,len(rows))}%)"
    )

    print()
    print(
        "TIMING"
    )

    external_hours = [
        float(
            row[
                "hours_post_to_first_external"
            ]
        )
        for row in rows
        if row[
            "hours_post_to_first_external"
        ] != ""
    ]

    if external_hours:

        external_hours.sort()

        middle = (
            len(external_hours)
            // 2
        )

        if (
            len(external_hours)
            % 2
        ):
            median = (
                external_hours[
                    middle
                ]
            )
        else:
            median = (
                external_hours[
                    middle - 1
                ]
                + external_hours[
                    middle
                ]
            ) / 2

        print(
            "Median hours to first "
            "external ID:",
            round(
                median,
                1
            )
        )

    print()
    print(
        "INTERPRETIVE CHECKPOINT"
    )

    print(
        "-----------------------"
    )

    print(
        "1. Separate lack of external "
        "attention from taxonomic resolution."
    )

    print(
        "2. Compare first external rank "
        "with eventual Community Taxon rank."
    )

    print(
        "3. Treat genus as a potentially "
        "appropriate expert endpoint, "
        "not automatically as failure."
    )

    print(
        "4. Interpret photo-count associations "
        "cautiously because difficult "
        "observations may attract more photos."
    )

    print(
        "5. Historical withdrawn IDs, "
        "rank changes and disagreements "
        "must be retained."
    )

    print()
    print(
        "Analysis source:",
        input_file
    )


if __name__ == "__main__":
    main()