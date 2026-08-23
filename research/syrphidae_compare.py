import csv
from collections import Counter, defaultdict


INPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_analysis.csv"
)


def load_rows():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def percent(part, total):
    if total == 0:
        return 0.0

    return round(
        100 * part / total,
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


def id_group(count):
    count = int(count)

    if count >= 4:
        return "4+"

    return str(count)


def print_cross_table(
    rows,
    label,
    group_function
):
    outcomes = [
        "species",
        "genus",
        "none",
        "other",
    ]

    groups = defaultdict(Counter)

    for row in rows:
        group = group_function(row)

        groups[group][
            row["outcome_group"]
        ] += 1

    print()
    print(label)
    print(
        "Group        N   "
        "Species       Genus"
        "        None       Other"
    )

    for group in sorted(
        groups,
        key=lambda x: (
            int(x.rstrip("+"))
            if x.rstrip("+").isdigit()
            else x
        )
    ):

        counts = groups[group]

        total = sum(
            counts.values()
        )

        values = []

        for outcome in outcomes:

            count = counts[outcome]

            values.append(
                f"{count:3d} "
                f"({percent(count,total):4.1f}%)"
            )

        print(
            f"{group:<8} "
            f"{total:4d}   "
            + "   ".join(values)
        )


def binary_comparison(
    rows,
    label,
    predicate
):
    groups = {
        "No": Counter(),
        "Yes": Counter(),
    }

    for row in rows:

        key = (
            "Yes"
            if predicate(row)
            else "No"
        )

        groups[key][
            row["outcome_group"]
        ] += 1

    print()
    print(label)

    for key in ("No", "Yes"):

        counts = groups[key]

        total = sum(
            counts.values()
        )

        species = (
            counts["species"]
        )

        genus_or_species = (
            counts["species"]
            + counts["genus"]
        )

        print(
            f"{key:<3}  "
            f"N={total:3d}   "
            f"species="
            f"{species:3d} "
            f"({percent(species,total):4.1f}%)   "
            f"genus+species="
            f"{genus_or_species:3d} "
            f"({percent(genus_or_species,total):4.1f}%)"
        )


def main():
    rows = load_rows()

    print(
        "Observations:",
        len(rows)
    )

    print_cross_table(
        rows,
        "PHOTO COUNT",
        lambda row: photo_group(
            row["photo_count"]
        ),
    )

    print_cross_table(
        rows,
        "CURRENT IDENTIFIER COUNT",
        lambda row: id_group(
            row["current_id_count"]
        ),
    )

    print_cross_table(
        rows,
        "EXTERNAL IDENTIFIER COUNT",
        lambda row: id_group(
            row["external_id_count"]
        ),
    )

    binary_comparison(
        rows,
        "PROJECT MEMBERSHIP",
        lambda row:
            int(row["project_count"]) > 0,
    )

    binary_comparison(
        rows,
        "ANY VISION-ASSOCIATED ID",
        lambda row:
            int(row["vision_id_count"]) > 0,
    )

    binary_comparison(
        rows,
        "ANY DISAGREEMENT",
        lambda row:
            int(
                row[
                    "disagreement_id_count"
                ]
            ) > 0,
    )


if __name__ == "__main__":
    main()