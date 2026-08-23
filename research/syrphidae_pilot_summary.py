import csv
from collections import Counter, defaultdict


ANALYSIS_FILE = (
    "research/"
    "syrphidae_pilot_500_analysis.csv"
)

HISTORY_FILE = (
    "research/"
    "syrphidae_pilot_500_history.csv"
)

EXPERIENCE_FILE = (
    "research/"
    "syrphidae_pilot_500_identifier_experience.csv"
)


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


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
    analysis = load_csv(
        ANALYSIS_FILE
    )

    history = {
        row["observation_id"]: row
        for row in load_csv(
            HISTORY_FILE
        )
    }

    experience = {
        row["observation_id"]: row
        for row in load_csv(
            EXPERIENCE_FILE
        )
    }

    rows = []

    for row in analysis:

        observation_id = (
            row["observation_id"]
        )

        rows.append(
            {
                **row,
                **history[
                    observation_id
                ],
                **experience[
                    observation_id
                ],
                "outcome_group":
                    history[
                        observation_id
                    ]["outcome_group"],
            }
        )

    print(
        "SYRPHIDAE PILOT SUMMARY"
    )
    print(
        "======================="
    )

    print()
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

        count = outcomes[outcome]

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
        if row["outcome_group"]
        == "none"
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
        row["outcome_group"]
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

    for rank in sorted(
        first_rank,
        key=lambda x:
            -sum(
                first_rank[x]
                .values()
            )
    )[:8]:

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
            row["photo_count"]
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

        if (
            photo_stats[
                group
            ]["total"]
            == 0
        ):
            continue

        total = (
            photo_stats[
                group
            ]["total"]
        )

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
                "first_external_prior_syrphidae_ids"
            ]
            != ""
            and int(
                row[
                    "first_external_prior_syrphidae_ids"
                ]
            ) >= 10000
        )
    ]

    print(
        "First external identifier "
        "with >=10,000 prior Syrphidae IDs:",
        len(high_first),
        f"({percent(len(high_first),len(attended))}%)"
    )

    high_first_outcomes = Counter(
        row["outcome_group"]
        for row in high_first
    )

    print(
        "  species:",
        high_first_outcomes[
            "species"
        ]
    )

    print(
        "  genus:",
        high_first_outcomes[
            "genus"
        ]
    )

    print(
        "  other:",
        high_first_outcomes[
            "other"
        ]
    )

    print(
        "  none:",
        high_first_outcomes[
            "none"
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
        "INTERPRETIVE CHECKPOINT"
    )
    print(
        "-----------------------"
    )

    print(
        "1. Most no-Community-Taxon "
        "observations received no external ID."
    )

    print(
        "2. Once external attention occurred, "
        "species or genus resolution was common."
    )

    print(
        "3. First external taxonomic rank "
        "strongly tracked final resolution."
    )

    print(
        "4. More photos did not show a simple "
        "positive relationship with species outcome."
    )

    print(
        "5. Very experienced Syrphidae identifiers "
        "often stopped at genus rather than species."
    )

    print(
        "6. Historical withdrawn IDs and owner-rank "
        "changes were common enough to matter."
    )


if __name__ == "__main__":
    main()