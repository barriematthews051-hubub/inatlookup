import csv
import json
import os
from collections import Counter


DATA_DIR = os.path.join(
    "research",
    "data",
)

CACHE_DIR = os.path.join(
    "research",
    "cache",
)

AUDIT_FILE = os.path.join(
    DATA_DIR,
    "public_interaction_audit.csv",
)

EXPERIENCE_FILE = os.path.join(
    DATA_DIR,
    "reviewer_experience_audit.csv",
)

TOP20_FILE = os.path.join(
    CACHE_DIR,
    "top20_specialists_2024.json",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "reviewer_reach_tier_audit.csv",
)


TAXON_IDS = {
    "Asteriidae": 47671,
    "Salticidae": 48139,
    "Russulaceae": 48340,
    "Anatidae": 6912,
}


COMMON_NAMES = {
    "Asteriidae": "common sea stars",
    "Salticidae": "jumping spiders",
    "Russulaceae": "russulas and milkcaps",
    "Anatidae": "ducks, geese and swans",
}


TIER_ORDER = [
    "No detectable reviewer",
    "0 prior external IDs",
    "1-9 prior external IDs",
    "10-99 prior external IDs",
    "100-999 prior external IDs",
    "1,000+ prior external IDs",
    "2024 Top-20 specialist",
]


def parse_bool(value):
    return str(value).strip().lower() in {
        "true",
        "1",
        "yes",
    }


def load_observations():
    observations = {}

    with open(
        AUDIT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            observation_id = int(
                row["observation_id"]
            )

            observations[
                observation_id
            ] = {
                "family":
                    row["family"],
                "common_name":
                    row["common_name"],
                "observation_id":
                    observation_id,
                "external_id_present":
                    int(
                        row[
                            "external_id_count"
                        ]
                    ) > 0,
                "reviewer_no_id_count":
                    int(
                        row[
                            "reviewer_no_id_count"
                        ]
                    ),
                "strict_non_id_action_count":
                    int(
                        row[
                            "strict_non_id_action_count"
                        ]
                    ),
            }

    return observations


def load_experience_pairs():
    pairs_by_observation = {}

    with open(
        EXPERIENCE_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            observation_id = int(
                row["observation_id"]
            )

            pair = {
                "family":
                    row["family"],
                "observation_id":
                    observation_id,
                "reviewer_user_id":
                    int(
                        row[
                            "reviewer_user_id"
                        ]
                    ),
                "prior_family_ids":
                    int(
                        row[
                            "prior_family_ids"
                        ]
                    ),
                "prior_external_family_ids":
                    int(
                        row[
                            "prior_external_family_ids"
                        ]
                    ),
            }

            pairs_by_observation.setdefault(
                observation_id,
                [],
            ).append(pair)

    return pairs_by_observation


def load_top20():
    with open(
        TOP20_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        raw = json.load(handle)

    top20_by_family = {}

    for family, taxon_id in TAXON_IDS.items():
        specialists = raw.get(
            str(taxon_id),
            [],
        )

        top20_by_family[
            family
        ] = {
            int(
                specialist["user_id"]
            )
            for specialist in specialists
        }

    return top20_by_family


def experience_tier(
    highest_external_ids,
):
    if highest_external_ids is None:
        return "No detectable reviewer"

    if highest_external_ids == 0:
        return "0 prior external IDs"

    if highest_external_ids < 10:
        return "1-9 prior external IDs"

    if highest_external_ids < 100:
        return "10-99 prior external IDs"

    if highest_external_ids < 1000:
        return "100-999 prior external IDs"

    return "1,000+ prior external IDs"


def analyse_observation(
    observation,
    pairs,
    top20_ids,
):
    if not pairs:
        return {
            **observation,
            "silent_reviewer_pairs": 0,
            "unique_silent_reviewers": 0,
            "highest_prior_external_ids": "",
            "highest_prior_family_ids": "",
            "any_10plus": False,
            "any_100plus": False,
            "any_1000plus": False,
            "any_top20_silent_reviewer": False,
            "highest_reviewer_tier":
                "No detectable reviewer",
        }

    highest_external = max(
        pair[
            "prior_external_family_ids"
        ]
        for pair in pairs
    )

    highest_family = max(
        pair["prior_family_ids"]
        for pair in pairs
    )

    reviewer_ids = {
        pair["reviewer_user_id"]
        for pair in pairs
    }

    any_top20 = bool(
        reviewer_ids
        & top20_ids
    )

    if any_top20:
        highest_tier = (
            "2024 Top-20 specialist"
        )
    else:
        highest_tier = experience_tier(
            highest_external
        )

    return {
        **observation,
        "silent_reviewer_pairs":
            len(pairs),
        "unique_silent_reviewers":
            len(reviewer_ids),
        "highest_prior_external_ids":
            highest_external,
        "highest_prior_family_ids":
            highest_family,
        "any_10plus":
            highest_external >= 10,
        "any_100plus":
            highest_external >= 100,
        "any_1000plus":
            highest_external >= 1000,
        "any_top20_silent_reviewer":
            any_top20,
        "highest_reviewer_tier":
            highest_tier,
    }


def percent(
    numerator,
    denominator,
):
    if denominator == 0:
        return 0.0

    return (
        numerator
        / denominator
        * 100
    )


def print_distribution(
    title,
    rows,
):
    print()
    print(title)
    print("-" * len(title))

    n = len(rows)

    print(
        f"  Observations: {n}"
    )

    if n == 0:
        return

    counts = Counter(
        row["highest_reviewer_tier"]
        for row in rows
    )

    for tier in TIER_ORDER:
        count = counts.get(
            tier,
            0,
        )

        print(
            f"  {tier:31} "
            f"{count:2}/{n} "
            f"({percent(count, n):5.1f}%)"
        )

    detectable = sum(
        row[
            "highest_reviewer_tier"
        ] != "No detectable reviewer"
        for row in rows
    )

    ten_plus = sum(
        row["any_10plus"]
        for row in rows
    )

    hundred_plus = sum(
        row["any_100plus"]
        for row in rows
    )

    thousand_plus = sum(
        row["any_1000plus"]
        for row in rows
    )

    top20 = sum(
        row[
            "any_top20_silent_reviewer"
        ]
        for row in rows
    )

    print()
    print(
        f"  Any silent reviewer: "
        f"{detectable}/{n} "
        f"({percent(detectable, n):.1f}%)"
    )

    print(
        f"  Reached reviewer with >=10 "
        f"prior external IDs: "
        f"{ten_plus}/{n} "
        f"({percent(ten_plus, n):.1f}%)"
    )

    print(
        f"  Reached reviewer with >=100 "
        f"prior external IDs: "
        f"{hundred_plus}/{n} "
        f"({percent(hundred_plus, n):.1f}%)"
    )

    print(
        f"  Reached reviewer with >=1,000 "
        f"prior external IDs: "
        f"{thousand_plus}/{n} "
        f"({percent(thousand_plus, n):.1f}%)"
    )

    print(
        f"  Reached 2024 Top-20 specialist: "
        f"{top20}/{n} "
        f"({percent(top20, n):.1f}%)"
    )


def print_no_id_observations(rows):
    print()
    print(
        "NO-EXTERNAL-ID OBSERVATION DETAIL"
    )
    print(
        "================================="
    )

    for family in TAXON_IDS:
        subset = [
            row
            for row in rows
            if (
                row["family"] == family
                and not row[
                    "external_id_present"
                ]
            )
        ]

        print()
        print(
            f"{family} "
            f"({COMMON_NAMES[family]})"
        )

        for row in sorted(
            subset,
            key=lambda item:
                item["observation_id"],
        ):
            highest = row[
                "highest_prior_external_ids"
            ]

            if highest == "":
                highest_text = "-"
            else:
                highest_text = (
                    f"{highest:,}"
                )

            print(
                f"  obs "
                f"{row['observation_id']}  "
                f"{row['highest_reviewer_tier']}"
                f"  highest_prior_external="
                f"{highest_text}"
                f"  reviewers="
                f"{row['unique_silent_reviewers']}"
            )


def main():
    observations = (
        load_observations()
    )

    pairs_by_observation = (
        load_experience_pairs()
    )

    top20_by_family = (
        load_top20()
    )

    output_rows = []

    for observation_id in sorted(
        observations
    ):
        observation = observations[
            observation_id
        ]

        family = observation[
            "family"
        ]

        pairs = (
            pairs_by_observation.get(
                observation_id,
                [],
            )
        )

        output_rows.append(
            analyse_observation(
                observation,
                pairs,
                top20_by_family[
                    family
                ],
            )
        )

    fields = [
        "family",
        "common_name",
        "observation_id",
        "external_id_present",
        "reviewer_no_id_count",
        "strict_non_id_action_count",
        "silent_reviewer_pairs",
        "unique_silent_reviewers",
        "highest_prior_external_ids",
        "highest_prior_family_ids",
        "any_10plus",
        "any_100plus",
        "any_1000plus",
        "any_top20_silent_reviewer",
        "highest_reviewer_tier",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        for row in output_rows:
            writer.writerow(row)

    print()
    print(
        "REVIEWER REACH-TIER ANALYSIS"
    )
    print(
        "============================"
    )
    print()
    print(
        "Highest detectable reviewer "
        "experience among reviewers who "
        "never identified that observation."
    )

    for family in TAXON_IDS:
        family_rows = [
            row
            for row in output_rows
            if row["family"] == family
        ]

        no_external = [
            row
            for row in family_rows
            if not row[
                "external_id_present"
            ]
        ]

        with_external = [
            row
            for row in family_rows
            if row[
                "external_id_present"
            ]
        ]

        print()
        print(
            f"{family} "
            f"({COMMON_NAMES[family]})"
        )

        print(
            "=" * (
                len(family)
                + len(
                    COMMON_NAMES[family]
                )
                + 3
            )
        )

        print_distribution(
            "NO EXTERNAL ID",
            no_external,
        )

        print_distribution(
            "WITH EXTERNAL ID",
            with_external,
        )

    all_no_external = [
        row
        for row in output_rows
        if not row[
            "external_id_present"
        ]
    ]

    all_with_external = [
        row
        for row in output_rows
        if row[
            "external_id_present"
        ]
    ]

    print()
    print(
        "ALL FOUR FAMILIES"
    )
    print(
        "================="
    )

    print_distribution(
        "NO EXTERNAL ID",
        all_no_external,
    )

    print_distribution(
        "WITH EXTERNAL ID",
        all_with_external,
    )

    print_no_id_observations(
        output_rows
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()