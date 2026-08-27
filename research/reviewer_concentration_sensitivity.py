import json
import os
from collections import Counter


CACHE_FILE = os.path.join(
    "research",
    "cache",
    "public_interactions_9000.json",
)


FAMILIES = [
    ("Syrphidae", "hoverflies"),
    ("Asilidae", "robber flies"),
    ("Geometridae", "geometer moths"),
    ("Nymphalidae", "brush-footed butterflies"),
    ("Staphylinidae", "rove beetles"),
    ("Asteraceae", "daisy/sunflower family"),
    ("Formicidae", "ants"),
    ("Libellulidae", "skimmers and perchers"),
    ("Orchidaceae", "orchid family"),
    ("Poaceae", "grass family"),
    ("Russulaceae", "russulas and milkcaps"),
    ("Parmeliaceae", "shield lichens"),
    ("Salticidae", "jumping spiders"),
    ("Lycosidae", "wolf spiders"),
    ("Anatidae", "ducks, geese and swans"),
    ("Colubridae", "colubrid snakes"),
    ("Limacidae", "keeled slugs"),
    ("Asteriidae", "common sea stars"),
]


def percent(numerator, denominator):
    if not denominator:
        return 0.0

    return (
        numerator
        / denominator
        * 100
    )


def load_records():
    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    return [
        record
        for record in data["records"].values()
        if record.get("status") == "ok"
    ]


def int_set(record, field):
    return {
        int(value)
        for value in record.get(
            field,
            [],
        )
    }


def non_review_evidence_users(record):
    result = set()

    for field in [
        "commenter_no_id_user_ids",
        "annotator_no_id_user_ids",
        "dqa_no_id_user_ids",
        "field_no_id_user_ids",
        "fave_no_id_user_ids",
    ]:
        result |= int_set(
            record,
            field,
        )

    return result


def reviewer_counter(no_id_rows):
    counter = Counter()

    for row in no_id_rows:
        for user_id in int_set(
            row,
            "reviewer_no_id_user_ids",
        ):
            counter[user_id] += 1

    return counter


def is_reached_after_exclusion(
    row,
    excluded_reviewers,
):
    reviewers = (
        int_set(
            row,
            "reviewer_no_id_user_ids",
        )
        - excluded_reviewers
    )

    other_evidence = (
        non_review_evidence_users(
            row
        )
    )

    return bool(
        reviewers
        or other_evidence
    )


def adjusted_no_id_reach(
    no_id_rows,
    excluded_reviewers,
):
    return sum(
        is_reached_after_exclusion(
            row,
            excluded_reviewers,
        )
        for row in no_id_rows
    )


def main():
    records = load_records()

    print()
    print(
        "REVIEWER-CONCENTRATION "
        "SENSITIVITY"
    )
    print(
        "========================="
        "============"
    )

    for family, common_name in FAMILIES:
        rows = [
            row
            for row in records
            if row["family"] == family
        ]

        external_rows = [
            row
            for row in rows
            if row[
                "external_id_present"
            ]
        ]

        no_id_rows = [
            row
            for row in rows
            if not row[
                "external_id_present"
            ]
        ]

        external_count = len(
            external_rows
        )

        no_id_count = len(
            no_id_rows
        )

        counter = reviewer_counter(
            no_id_rows
        )

        ranked = (
            counter.most_common()
        )

        top1 = {
            ranked[0][0]
        } if ranked else set()

        top5 = {
            user_id
            for user_id, count
            in ranked[:5]
        }

        raw_no_id_reach = (
            adjusted_no_id_reach(
                no_id_rows,
                set(),
            )
        )

        minus_top1_no_id_reach = (
            adjusted_no_id_reach(
                no_id_rows,
                top1,
            )
        )

        minus_top5_no_id_reach = (
            adjusted_no_id_reach(
                no_id_rows,
                top5,
            )
        )

        raw_total_reach = (
            external_count
            + raw_no_id_reach
        )

        minus_top1_total_reach = (
            external_count
            + minus_top1_no_id_reach
        )

        minus_top5_total_reach = (
            external_count
            + minus_top5_no_id_reach
        )

        lost_top1 = (
            raw_no_id_reach
            - minus_top1_no_id_reach
        )

        lost_top5 = (
            raw_no_id_reach
            - minus_top5_no_id_reach
        )

        print()
        print(
            f"{family} "
            f"({common_name})"
        )

        print(
            "=" * (
                len(family)
                + len(common_name)
                + 3
            )
        )

        print(
            f"  External ID: "
            f"{external_count}/500 "
            f"({percent(
                external_count,
                500
            ):.1f}%)"
        )

        print(
            f"  No external ID: "
            f"{no_id_count}"
        )

        if ranked:
            top_user, top_count = (
                ranked[0]
            )

            print(
                f"  Top silent reviewer: "
                f"user={top_user} "
                f"on {top_count}/"
                f"{no_id_count} "
                f"no-ID observations "
                f"({percent(
                    top_count,
                    no_id_count
                ):.1f}%)"
            )

        else:
            print(
                "  Top silent reviewer: "
                "none"
            )

        print()
        print(
            "  NO-ID DETECTABLE REACH"
        )

        print(
            f"    Raw: "
            f"{raw_no_id_reach}/"
            f"{no_id_count} "
            f"({percent(
                raw_no_id_reach,
                no_id_count
            ):.1f}%)"
        )

        print(
            f"    Ignore Top-1 "
            f"review evidence: "
            f"{minus_top1_no_id_reach}/"
            f"{no_id_count} "
            f"({percent(
                minus_top1_no_id_reach,
                no_id_count
            ):.1f}%)"
        )

        print(
            f"    Ignore Top-5 "
            f"review evidence: "
            f"{minus_top5_no_id_reach}/"
            f"{no_id_count} "
            f"({percent(
                minus_top5_no_id_reach,
                no_id_count
            ):.1f}%)"
        )

        print(
            f"    Lost if Top-1 removed: "
            f"{lost_top1}"
        )

        print(
            f"    Lost if Top-5 removed: "
            f"{lost_top5}"
        )

        print()
        print(
            "  TOTAL DETECTABLE REACH"
        )

        print(
            f"    Raw: "
            f"{raw_total_reach}/500 "
            f"({percent(
                raw_total_reach,
                500
            ):.1f}%)"
        )

        print(
            f"    Ignore Top-1: "
            f"{minus_top1_total_reach}/500 "
            f"({percent(
                minus_top1_total_reach,
                500
            ):.1f}%)"
        )

        print(
            f"    Ignore Top-5: "
            f"{minus_top5_total_reach}/500 "
            f"({percent(
                minus_top5_total_reach,
                500
            ):.1f}%)"
        )


if __name__ == "__main__":
    main()