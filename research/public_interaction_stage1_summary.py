import csv
from collections import OrderedDict


INPUT_FILE = (
    "research/data/"
    "public_interaction_audit.csv"
)


INTEGER_FIELDS = [
    "external_id_count",
    "reviewer_no_id_count",
    "reviewed_only_count",
    "commenter_no_id_count",
    "annotator_no_id_count",
    "dqa_no_id_count",
    "field_no_id_count",
    "fave_no_id_count",
    "strict_non_id_action_count",
    "action_no_id_not_reviewed_count",
    "detectable_non_id_user_count",
]


def load_rows():
    rows = []

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            for field in INTEGER_FIELDS:
                row[field] = int(
                    row[field]
                )

            rows.append(row)

    return rows


def count_observations(
    rows,
    field,
):
    return sum(
        row[field] > 0
        for row in rows
    )


def count_pairs(
    rows,
    field,
):
    return sum(
        row[field]
        for row in rows
    )


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


def print_interaction_block(
    title,
    rows,
):
    n = len(rows)

    reviewer_obs = count_observations(
        rows,
        "reviewer_no_id_count",
    )

    reviewer_pairs = count_pairs(
        rows,
        "reviewer_no_id_count",
    )

    reviewed_only_obs = (
        count_observations(
            rows,
            "reviewed_only_count",
        )
    )

    strict_obs = count_observations(
        rows,
        "strict_non_id_action_count",
    )

    strict_pairs = count_pairs(
        rows,
        "strict_non_id_action_count",
    )

    not_reviewed_obs = (
        count_observations(
            rows,
            "action_no_id_not_reviewed_count",
        )
    )

    detectable_obs = (
        count_observations(
            rows,
            "detectable_non_id_user_count",
        )
    )

    detectable_pairs = count_pairs(
        rows,
        "detectable_non_id_user_count",
    )

    print()
    print(
        f"  {title}: {n}"
    )

    if n == 0:
        return

    print(
        "    Reviewer-no-ID: "
        f"{reviewer_obs}/{n} "
        f"({percent(reviewer_obs, n):.1f}%) "
        f"pairs={reviewer_pairs}"
    )

    print(
        "    Reviewed-only: "
        f"{reviewed_only_obs}/{n} "
        f"({percent(reviewed_only_obs, n):.1f}%)"
    )

    print(
        "    Strict non-ID action: "
        f"{strict_obs}/{n} "
        f"({percent(strict_obs, n):.1f}%) "
        f"pairs={strict_pairs}"
    )

    print(
        "    Non-ID action, not reviewed: "
        f"{not_reviewed_obs}/{n} "
        f"({percent(not_reviewed_obs, n):.1f}%)"
    )

    print(
        "    Any detectable non-ID interaction: "
        f"{detectable_obs}/{n} "
        f"({percent(detectable_obs, n):.1f}%) "
        f"pairs={detectable_pairs}"
    )


def main():
    rows = load_rows()

    families = OrderedDict()

    for row in rows:
        key = (
            row["family"],
            row["common_name"],
        )

        families.setdefault(
            key,
            [],
        ).append(row)

    print()
    print(
        "STAGE 1 PUBLIC INTERACTION SUMMARY"
    )
    print(
        "=================================="
    )
    print()
    print(
        "No external ID here means "
        "external_id_count == 0 "
        "in the detailed public "
        "observation record."
    )

    for (
        family,
        common_name,
    ), family_rows in families.items():

        no_external = [
            row
            for row in family_rows
            if row[
                "external_id_count"
            ] == 0
        ]

        with_external = [
            row
            for row in family_rows
            if row[
                "external_id_count"
            ] > 0
        ]

        print()
        print(
            f"{family} "
            f"({common_name})"
        )
        print(
            "-" * (
                len(family)
                + len(common_name)
                + 3
            )
        )

        print(
            f"  Total observations: "
            f"{len(family_rows)}"
        )

        print(
            f"  No external ID: "
            f"{len(no_external)}"
        )

        print(
            f"  With external ID: "
            f"{len(with_external)}"
        )

        print_interaction_block(
            "NO EXTERNAL ID",
            no_external,
        )

        print_interaction_block(
            "WITH EXTERNAL ID",
            with_external,
        )

    no_external_all = [
        row
        for row in rows
        if row[
            "external_id_count"
        ] == 0
    ]

    with_external_all = [
        row
        for row in rows
        if row[
            "external_id_count"
        ] > 0
    ]

    print()
    print(
        "ALL FOUR FAMILIES"
    )
    print(
        "================="
    )

    print_interaction_block(
        "NO EXTERNAL ID",
        no_external_all,
    )

    print_interaction_block(
        "WITH EXTERNAL ID",
        with_external_all,
    )


if __name__ == "__main__":
    main()