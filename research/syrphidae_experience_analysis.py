import csv
import math
import statistics
from collections import Counter, defaultdict


ANALYSIS_FILE = (
    "research/"
    "syrphidae_pilot_500_analysis.csv"
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


def percentile(values, p):
    """
    Linear interpolation percentile.
    values must contain numbers.
    p is between 0 and 1.
    """
    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * p

    lower = math.floor(position)
    upper = math.ceil(position)

    if lower == upper:
        return values[lower]

    fraction = position - lower

    return (
        values[lower]
        + (
            values[upper]
            - values[lower]
        ) * fraction
    )


def experience_band(value):
    if value < 10:
        return "0-9"

    if value < 100:
        return "10-99"

    if value < 1000:
        return "100-999"

    if value < 10000:
        return "1,000-9,999"

    if value < 100000:
        return "10,000-99,999"

    return "100,000+"


BAND_ORDER = [
    "0-9",
    "10-99",
    "100-999",
    "1,000-9,999",
    "10,000-99,999",
    "100,000+",
]


def describe(values):
    if not values:
        return None

    return {
        "n": len(values),
        "median": statistics.median(values),
        "q1": percentile(values, 0.25),
        "q3": percentile(values, 0.75),
        "min": min(values),
        "max": max(values),
    }


def fmt(value):
    if value is None:
        return "NA"

    return f"{value:,.0f}"


def print_distribution(
    title,
    rows,
    field
):
    print()
    print(title)
    print("=" * len(title))

    for outcome in [
        "species",
        "genus",
        "none",
        "other",
    ]:

        values = [
            int(row[field])
            for row in rows
            if row["outcome_group"] == outcome
            and row[field] != ""
        ]

        stats = describe(values)

        print()
        print(outcome.upper())

        if stats is None:
            print("  No experience values")
            continue

        print(
            "  N:",
            stats["n"]
        )

        print(
            "  Median:",
            fmt(stats["median"])
        )

        print(
            "  Q1-Q3:",
            f"{fmt(stats['q1'])}"
            f" - "
            f"{fmt(stats['q3'])}"
        )

        print(
            "  Range:",
            f"{fmt(stats['min'])}"
            f" - "
            f"{fmt(stats['max'])}"
        )

        bands = Counter(
            experience_band(value)
            for value in values
        )

        print("  Bands:")

        for band in BAND_ORDER:
            count = bands[band]

            percentage = (
                100 * count / len(values)
            )

            print(
                f"    {band:<15} "
                f"{count:3d} "
                f"({percentage:5.1f}%)"
            )


def print_species_success(
    title,
    rows,
    field
):
    print()
    print(title)
    print("=" * len(title))

    grouped = defaultdict(list)

    for row in rows:
        if row[field] == "":
            continue

        value = int(row[field])

        grouped[
            experience_band(value)
        ].append(row)

    for band in BAND_ORDER:

        group = grouped[band]

        if not group:
            continue

        species_count = sum(
            row["outcome_group"] == "species"
            for row in group
        )

        genus_count = sum(
            row["outcome_group"] == "genus"
            for row in group
        )

        other_count = sum(
            row["outcome_group"] == "other"
            for row in group
        )

        none_count = sum(
            row["outcome_group"] == "none"
            for row in group
        )

        n = len(group)

        print()
        print(
            f"{band:<15} N={n}"
        )

        print(
            f"  Species: "
            f"{species_count:3d} "
            f"({100 * species_count / n:5.1f}%)"
        )

        print(
            f"  Genus:   "
            f"{genus_count:3d} "
            f"({100 * genus_count / n:5.1f}%)"
        )

        print(
            f"  Other:   "
            f"{other_count:3d} "
            f"({100 * other_count / n:5.1f}%)"
        )

        print(
            f"  None:    "
            f"{none_count:3d} "
            f"({100 * none_count / n:5.1f}%)"
        )


def main():

    analysis = load_csv(
        ANALYSIS_FILE
    )

    experience = load_csv(
        EXPERIENCE_FILE
    )

    analysis_by_id = {
        row["observation_id"]: row
        for row in analysis
    }

    joined = []

    for exp in experience:

        observation_id = (
            exp["observation_id"]
        )

        if (
            observation_id
            not in analysis_by_id
        ):
            continue

        joined.append(
            {
                **analysis_by_id[
                    observation_id
                ],
                **exp,
            }
        )

    print(
        "Analysis rows:",
        len(analysis)
    )

    print(
        "Experience rows:",
        len(experience)
    )

    print(
        "Joined rows:",
        len(joined)
    )

    print(
        "Outcomes:",
        dict(
            Counter(
                row["outcome_group"]
                for row in joined
            )
        )
    )

    with_external = [
        row
        for row in joined
        if (
            row[
                "first_external_prior_syrphidae_ids"
            ]
            != ""
        )
    ]

    print(
        "Observations with external ID:",
        len(with_external)
    )

    print(
        "Observations without external ID:",
        len(joined) - len(with_external)
    )

    print_distribution(
        "FIRST EXTERNAL IDENTIFIER EXPERIENCE",
        joined,
        "first_external_prior_syrphidae_ids"
    )

    print_distribution(
        "MAXIMUM EXTERNAL IDENTIFIER EXPERIENCE",
        joined,
        "max_prior_syrphidae_ids"
    )

    print_species_success(
        "OUTCOME BY FIRST IDENTIFIER EXPERIENCE",
        joined,
        "first_external_prior_syrphidae_ids"
    )

    print_species_success(
        "OUTCOME BY MAXIMUM IDENTIFIER EXPERIENCE",
        joined,
        "max_prior_syrphidae_ids"
    )


if __name__ == "__main__":
    main()