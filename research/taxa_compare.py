import csv
import os
import statistics
from collections import Counter, defaultdict
from identifier_concentration_utils import (
    calculate_identifier_concentration,
)

DATA_DIR = "research/data"

TAXA = [
    ("Syrphidae", 49995),
    ("Asilidae", 47982),
    ("Geometridae", 49530),
    ("Nymphalidae", 47922),
    ("Staphylinidae", 47951),
    ("Asteraceae", 47604),
]


def slugify(text):
    return text.strip().lower()


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8",
    ) as f:
        return list(csv.DictReader(f))


def percent(n, total):
    if total == 0:
        return 0.0

    return 100 * n / total


def median(values):
    if not values:
        return None

    return statistics.median(values)


def fmt_pct(value):
    if value is None:
        return "NA"

    return f"{value:.1f}%"


def fmt_hours(value):
    if value is None:
        return "NA"

    return f"{value:.1f}"

# Classify a value relative to the other pilot taxa.
# The lowest third is Low, middle third Medium,
# and highest third High.
def relative_level(
    value,
    all_values,
    reverse=False,
):
    ordered = sorted(all_values)

    n = len(ordered)

    low_cut = ordered[
        n // 3
    ]

    high_cut = ordered[
        (2 * n) // 3
    ]

    if value < low_cut:
        level = "Low"
    elif value < high_cut:
        level = "Medium"
    else:
        level = "High"

    if reverse:
        if level == "Low":
            return "High"
        if level == "High":
            return "Low"

    return level


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


def summarize_taxon(
    taxon_name,
    taxon_id,
):
    slug = slugify(
        taxon_name
    )

    filename = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_500_analysis.csv",
    )

    if not os.path.exists(filename):
        raise RuntimeError(
            f"Missing analysis file: "
            f"{filename}"
        )

    rows = load_csv(
        filename
    )

    identifications_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_500_identifications_all.csv",
    )

    identification_rows = load_csv(
        identifications_file
    )

    concentration = (
        calculate_identifier_concentration(
            identification_rows
        )
    )

    total = len(rows)

    attended = [
        row
        for row in rows
        if int(
            row["external_history_count"]
        ) > 0
    ]

    outcome_counts = Counter(
        row["outcome_group"]
        for row in rows
    )

    attended_outcomes = Counter(
        row["outcome_group"]
        for row in attended
    )

    timing = [
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

    experienced_first = [
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
            row["outcome_group"]
            == "species"
        ):
            photo_stats[
                group
            ]["species"] += 1

    result = {
        "taxon":
            taxon_name,

        "taxon_id":
            taxon_id,

        "n":
            total,

        "external_id_rate":
            percent(
                len(attended),
                total,
            ),

        "species_ct_rate":
            percent(
                outcome_counts[
                    "species"
                ],
                total,
            ),

        "genus_ct_rate":
            percent(
                outcome_counts[
                    "genus"
                ],
                total,
            ),

        "other_ct_rate":
            percent(
                outcome_counts[
                    "other"
                ],
                total,
            ),

        "none_ct_rate":
            percent(
                outcome_counts[
                    "none"
                ],
                total,
            ),

        "species_given_external":
            percent(
                attended_outcomes[
                    "species"
                ],
                len(attended),
            ),

        "genus_given_external":
            percent(
                attended_outcomes[
                    "genus"
                ],
                len(attended),
            ),

        "other_given_external":
            percent(
                attended_outcomes[
                    "other"
                ],
                len(attended),
            ),

        "none_given_external":
            percent(
                attended_outcomes[
                    "none"
                ],
                len(attended),
            ),

        "median_hours_first_external":
            median(timing),

        "experienced_first_rate":
            percent(
                len(
                    experienced_first
                ),
                len(attended),
            ),

        "owner_rank_changed_rate":
            percent(
                owner_changed,
                total,
            ),

        "withdrawn_observation_rate":
            percent(
                withdrawn,
                total,
            ),

        "disagreement_rate":
            percent(
                disagreement,
                total,
            ),

         "maverick_rate":
            percent(
                maverick,
                total,
            ),

        
        "historical_external_ids":
            concentration[
                "historical_external_ids"
            ],

        "unique_external_identifiers":
            concentration[
                "unique_external_identifiers"
            ],

        "mean_external_ids_per_identifier":
            concentration[
                "mean_external_ids_per_identifier"
            ],

        "top_1_id_share":
            concentration[
                "top_1_id_share"
            ],

        "top_5_id_share":
            concentration[
                "top_5_id_share"
            ],

        "top_10_id_share":
            concentration[
                "top_10_id_share"
            ],

        "top_20_id_share":
            concentration[
                "top_20_id_share"
            ],

        "top_1_observation_coverage":
            concentration[
                "top_1_observation_coverage"
            ],

        "top_5_observation_coverage":
            concentration[
                "top_5_observation_coverage"
            ],

        "top_10_observation_coverage":
            concentration[
                "top_10_observation_coverage"
            ],

        "top_20_observation_coverage":
            concentration[
                "top_20_observation_coverage"
            ],

        "friction_score":
            (
                percent(
                    owner_changed,
                    total,
                )
                + percent(
                    withdrawn,
                    total,
                )
                + percent(
                    disagreement,
                    total,
                )
                + percent(
                    maverick,
                    total,
                )
            ) / 4,
    }

    for group in (        "0",
        "1",
        "2",
        "3",
        "4+",
    ):
        total_group = (
            photo_stats[
                group
            ]["total"]
        )

        species_group = (
            photo_stats[
                group
            ]["species"]
        )

        result[
            f"photo_{group}_species_rate"
        ] = (
            percent(
                species_group,
                total_group,
            )
            if total_group
            else None
        )

        result[
            f"photo_{group}_n"
        ] = total_group

    return result


def print_main_table(
    summaries
):
    print()
    print(
        "SIX-TAXON COMPARISON"
    )

    print(
        "===================="
    )

    print()

    header = (
        f"{'Taxon':<16}"
        f"{'Ext ID':>9}"
        f"{'Species CT':>12}"
        f"{'Genus CT':>10}"
        f"{'No CT':>9}"
        f"{'Species|Ext':>13}"
        f"{'Median h':>10}"
        f"{'10k+ first':>12}"
    )

    print(header)

    print(
        "-" * len(header)
    )

    for row in summaries:

        print(
            f"{row['taxon']:<16}"
            f"{fmt_pct(row['external_id_rate']):>9}"
            f"{fmt_pct(row['species_ct_rate']):>12}"
            f"{fmt_pct(row['genus_ct_rate']):>10}"
            f"{fmt_pct(row['none_ct_rate']):>9}"
            f"{fmt_pct(row['species_given_external']):>13}"
            f"{fmt_hours(row['median_hours_first_external']):>10}"
            f"{fmt_pct(row['experienced_first_rate']):>12}"
        )


def print_history_table(
    summaries
):
    print()
    print(
        "HISTORICAL IDENTIFICATION DYNAMICS"
    )

    print(
        "=================================="
    )

    print()

    header = (
        f"{'Taxon':<16}"
        f"{'Owner change':>14}"
        f"{'Withdrawn':>12}"
        f"{'Disagree':>11}"
        f"{'Maverick':>11}"
    )

    print(header)

    print(
        "-" * len(header)
    )

    for row in summaries:

        print(
            f"{row['taxon']:<16}"
            f"{fmt_pct(row['owner_rank_changed_rate']):>14}"
            f"{fmt_pct(row['withdrawn_observation_rate']):>12}"
            f"{fmt_pct(row['disagreement_rate']):>11}"
            f"{fmt_pct(row['maverick_rate']):>11}"
        )


def print_photo_table(
    summaries
):
    print()
    print(
        "SPECIES OUTCOME BY PHOTO COUNT"
    )

    print(
        "=============================="
    )

    print()

    header = (
        f"{'Taxon':<16}"
        f"{'1 photo':>11}"
        f"{'2 photos':>11}"
        f"{'3 photos':>11}"
        f"{'4+ photos':>12}"
    )

    print(header)

    print(
        "-" * len(header)
    )

    for row in summaries:

        print(
            f"{row['taxon']:<16}"
            f"{fmt_pct(row['photo_1_species_rate']):>11}"
            f"{fmt_pct(row['photo_2_species_rate']):>11}"
            f"{fmt_pct(row['photo_3_species_rate']):>11}"
            f"{fmt_pct(row['photo_4+_species_rate']):>12}"
        )

def print_concentration_table(
    summaries
):
    print()
    print(
        "IDENTIFIER COMMUNITY CONCENTRATION"
    )

    print(
        "=================================="
    )

    print()

    header = (
        f"{'Taxon':<16}"
        f"{'Unique':>8}"
        f"{'IDs/user':>10}"
        f"{'Top1':>9}"
        f"{'Top5':>9}"
        f"{'Top10':>9}"
        f"{'Top20':>9}"
        f"{'Top1 obs':>10}"
        f"{'Top5 obs':>10}"
    )

    print(header)

    print(
        "-" * len(header)
    )

    for row in summaries:
        print(
            f"{row['taxon']:<16}"
            f"{row['unique_external_identifiers']:>8}"
            f"{row['mean_external_ids_per_identifier']:>10.2f}"
            f"{fmt_pct(row['top_1_id_share']):>9}"
            f"{fmt_pct(row['top_5_id_share']):>9}"
            f"{fmt_pct(row['top_10_id_share']):>9}"
            f"{fmt_pct(row['top_20_id_share']):>9}"
            f"{fmt_pct(row['top_1_observation_coverage']):>10}"
            f"{fmt_pct(row['top_5_observation_coverage']):>10}"
        )

def print_hypothesis_table(
    summaries
):
    attention_values = [
        row["external_id_rate"]
        for row in summaries
    ]

    resolution_values = [
        row["species_given_external"]
        for row in summaries
    ]

    speed_values = [
        row["median_hours_first_external"]
        for row in summaries
    ]

    concentration_values = [
        row["top_5_id_share"]
        for row in summaries
    ]

    friction_values = [
        row["friction_score"]
        for row in summaries
    ]

    print()
    print(
        "FAMILY-LEVEL HYPOTHESIS TABLE"
    )

    print(
        "============================="
    )

    print()

    header = (
        f"{'Taxon':<16}"
        f"{'Attention':>15}"
        f"{'Resolution':>17}"
        f"{'Speed':>16}"
        f"{'Concentration':>19}"
        f"{'Friction':>16}"
    )

    print(header)
    print(
        "-" * len(header)
    )

    for row in summaries:
        attention_level = relative_level(
            row["external_id_rate"],
            attention_values,
        )

        resolution_level = relative_level(
            row["species_given_external"],
            resolution_values,
        )

        speed_level = relative_level(
            row["median_hours_first_external"],
            speed_values,
            reverse=True,
        )

        concentration_level = relative_level(
            row["top_5_id_share"],
            concentration_values,
        )

        friction_level = relative_level(
            row["friction_score"],
            friction_values,
        )

        attention = (
            f"{attention_level} "
            f"{row['external_id_rate']:.1f}%"
        )

        resolution = (
            f"{resolution_level} "
            f"{row['species_given_external']:.1f}%"
        )

        speed = (
            f"{speed_level} "
            f"{row['median_hours_first_external']:.1f}h"
        )

        concentration = (
            f"{concentration_level} "
            f"{row['top_5_id_share']:.1f}%"
        )

        friction = (
            f"{friction_level} "
            f"{row['friction_score']:.1f}"
        )

        print(
            f"{row['taxon']:<16}"
            f"{attention:>15}"
            f"{resolution:>17}"
            f"{speed:>16}"
            f"{concentration:>19}"
            f"{friction:>16}"
        )

def write_csv(
    summaries
):
    output_file = os.path.join(
        DATA_DIR,
        "taxa_comparison.csv",
    )

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                summaries[0].keys()
            ),
        )

        writer.writeheader()
        writer.writerows(
            summaries
        )

    print()
    print(
        "Comparison CSV:",
        output_file
    )


def main():
    summaries = []

    for (
        taxon_name,
        taxon_id,
    ) in TAXA:

        summaries.append(
            summarize_taxon(
                taxon_name,
                taxon_id,
            )
        )

    print_main_table(
        summaries
    )

    print_history_table(
        summaries
    )

    print_photo_table(
        summaries
    )

    print_concentration_table(
        summaries
    )

    print_hypothesis_table(
        summaries
    )

    write_csv(
        summaries
    )

if __name__ == "__main__":
    main()