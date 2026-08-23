import csv
import statistics
from collections import Counter, defaultdict


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


def attention_group(count):
    count = int(count)

    if count == 1:
        return "1"

    if count == 2:
        return "2"

    if count >= 3:
        return "3+"

    return "0"


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


OUTCOME_ORDER = [
    "species",
    "genus",
    "other",
    "none",
]


def percent(n, total):
    if total == 0:
        return 0.0

    return 100 * n / total


def median_or_none(values):
    if not values:
        return None

    return statistics.median(values)


def fmt_number(value):
    if value is None:
        return "NA"

    return f"{value:,.0f}"


def print_attention_summary(rows):

    print()
    print("EXTERNAL ATTENTION BY OUTCOME")
    print("=============================")

    for outcome in OUTCOME_ORDER:

        group = [
            row
            for row in rows
            if row["outcome_group"] == outcome
        ]

        counts = Counter(
            attention_group(
                row["external_history_count"]
            )
            for row in group
        )

        print()
        print(
            outcome.upper(),
            "N=",
            len(group)
        )

        for level in [
            "0",
            "1",
            "2",
            "3+",
        ]:

            n = counts[level]

            print(
                f"  {level:<2} external IDs: "
                f"{n:3d} "
                f"({percent(n,len(group)):5.1f}%)"
            )


def print_experience_by_attention(rows):

    print()
    print(
        "FIRST IDENTIFIER EXPERIENCE "
        "BY ATTENTION AND OUTCOME"
    )

    print(
        "=" * 52
    )

    for attention in [
        "1",
        "2",
        "3+",
    ]:

        print()
        print(
            f"EXTERNAL ID COUNT: {attention}"
        )

        for outcome in OUTCOME_ORDER:

            values = [
                int(
                    row[
                        "first_external_prior_syrphidae_ids"
                    ]
                )
                for row in rows
                if (
                    row["outcome_group"]
                    == outcome
                    and attention_group(
                        row[
                            "external_history_count"
                        ]
                    )
                    == attention
                    and row[
                        "first_external_prior_syrphidae_ids"
                    ]
                    != ""
                )
            ]

            print(
                f"  {outcome:<7} "
                f"N={len(values):3d} "
                f"median="
                f"{fmt_number(median_or_none(values))}"
            )


def print_exactly_one(rows):

    group = [
        row
        for row in rows
        if int(
            row["external_history_count"]
        ) == 1
    ]

    print()
    print("EXACTLY ONE EXTERNAL IDENTIFIER")
    print("===============================")

    print(
        "Observations:",
        len(group)
    )

    for outcome in OUTCOME_ORDER:

        outcome_rows = [
            row
            for row in group
            if row["outcome_group"] == outcome
        ]

        values = [
            int(
                row[
                    "first_external_prior_syrphidae_ids"
                ]
            )
            for row in outcome_rows
            if row[
                "first_external_prior_syrphidae_ids"
            ] != ""
        ]

        bands = Counter(
            experience_band(value)
            for value in values
        )

        print()
        print(
            outcome.upper(),
            "N=",
            len(outcome_rows),
            "median=",
            fmt_number(
                median_or_none(values)
            )
        )

        for band in BAND_ORDER:

            n = bands[band]

            if n == 0:
                continue

            print(
                f"  {band:<15} "
                f"{n:3d} "
                f"({percent(n,len(values)):5.1f}%)"
            )


def print_first_rank_by_experience(rows):

    usable = [
        row
        for row in rows
        if row[
            "first_external_prior_syrphidae_ids"
        ] != ""
    ]

    print()
    print(
        "FIRST EXTERNAL RANK "
        "BY IDENTIFIER EXPERIENCE"
    )

    print(
        "=" * 44
    )

    for band in BAND_ORDER:

        group = [
            row
            for row in usable
            if experience_band(
                int(
                    row[
                        "first_external_prior_syrphidae_ids"
                    ]
                )
            ) == band
        ]

        if not group:
            continue

        ranks = Counter(
            row["first_external_rank"]
            or "NONE"
            for row in group
        )

        print()
        print(
            band,
            "N=",
            len(group)
        )

        for rank, n in ranks.most_common():

            print(
                f"  {rank:<15} "
                f"{n:3d} "
                f"({percent(n,len(group)):5.1f}%)"
            )


def print_rank_outcomes(rows):

    usable = [
        row
        for row in rows
        if row[
            "first_external_prior_syrphidae_ids"
        ] != ""
    ]

    print()
    print(
        "OUTCOME BY FIRST EXTERNAL RANK"
    )

    print(
        "=" * 30
    )

    rank_groups = defaultdict(list)

    for row in usable:

        rank = (
            row["first_external_rank"]
            or "NONE"
        )

        rank_groups[rank].append(row)

    ordered_ranks = sorted(
        rank_groups,
        key=lambda rank:
            (
                -len(rank_groups[rank]),
                rank
            )
    )

    for rank in ordered_ranks:

        group = rank_groups[rank]

        outcomes = Counter(
            row["outcome_group"]
            for row in group
        )

        print()
        print(
            rank.upper(),
            "N=",
            len(group)
        )

        for outcome in OUTCOME_ORDER:

            n = outcomes[outcome]

            print(
                f"  {outcome:<7} "
                f"{n:3d} "
                f"({percent(n,len(group)):5.1f}%)"
            )


def print_high_experience_rank_outcomes(rows):

    print()
    print(
        "HIGH-EXPERIENCE FIRST IDENTIFIERS"
    )

    print(
        "=" * 33
    )

    high = [
        row
        for row in rows
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
        "Prior Syrphidae IDs >= 10,000:",
        len(high)
    )

    combinations = Counter(
        (
            row["first_external_rank"]
            or "NONE",
            row["outcome_group"]
        )
        for row in high
    )

    for (
        rank,
        outcome
    ), n in combinations.most_common():

        print(
            f"  {n:3d}  "
            f"first rank={rank:<12} "
            f"outcome={outcome}"
        )


def main():

    history = load_csv(
        HISTORY_FILE
    )

    experience = load_csv(
        EXPERIENCE_FILE
    )

    history_by_id = {
        row["observation_id"]: row
        for row in history
    }

    joined = []

    for exp in experience:

        observation_id = (
            exp["observation_id"]
        )

        if observation_id not in history_by_id:
            continue

        hist = history_by_id[
            observation_id
        ]

        joined.append(
            {
                **hist,
                **exp,
                "outcome_group":
                    hist["outcome_group"],
            }
        )

    print(
        "History rows:",
        len(history)
    )

    print(
        "Experience rows:",
        len(experience)
    )

    print(
        "Joined rows:",
        len(joined)
    )

    print_attention_summary(
        joined
    )

    print_experience_by_attention(
        joined
    )

    print_exactly_one(
        joined
    )

    print_first_rank_by_experience(
        joined
    )

    print_rank_outcomes(
        joined
    )

    print_high_experience_rank_outcomes(
        joined
    )


if __name__ == "__main__":
    main()