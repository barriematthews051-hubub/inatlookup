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
        row
        for row in data["records"].values()
        if row.get("status") == "ok"
    ]


def reviewer_ids(row):
    return {
        int(value)
        for value in row.get(
            "reviewer_no_id_user_ids",
            [],
        )
    }


def reviewer_ranking(no_id_rows):
    counter = Counter()

    for row in no_id_rows:
        for user_id in reviewer_ids(row):
            counter[user_id] += 1

    return counter.most_common()


def review_reached(
    row,
    excluded_reviewers,
):
    if row["external_id_present"]:
        return True

    remaining_reviewers = (
        reviewer_ids(row)
        - excluded_reviewers
    )

    return bool(
        remaining_reviewers
    )


def reach_count(
    rows,
    excluded_reviewers,
):
    return sum(
        review_reached(
            row,
            excluded_reviewers,
        )
        for row in rows
    )


def main():
    records = load_records()

    print()
    print(
        "REVIEW-BASED REACH ROBUSTNESS"
    )
    print(
        "============================="
    )

    print()
    print(
        "Reach = external identification "
        "OR reviewed-without-ID."
    )

    print()
    print(
        "Top-1 and Top-5 sensitivity "
        "remove only review evidence from "
        "the most prevalent silent reviewers."
    )

    print()
    print(
        f"{'Family':15}"
        f"{'ID':>8}"
        f"{'Raw reach':>12}"
        f"{'-Top1':>10}"
        f"{'-Top5':>10}"
        f"{'Raw conv':>11}"
        f"{'Top5 conv':>11}"
    )

    print(
        "-" * 77
    )

    for family, common_name in FAMILIES:
        rows = [
            row
            for row in records
            if row["family"] == family
        ]

        no_id_rows = [
            row
            for row in rows
            if not row[
                "external_id_present"
            ]
        ]

        external = sum(
            bool(
                row[
                    "external_id_present"
                ]
            )
            for row in rows
        )

        ranked = reviewer_ranking(
            no_id_rows
        )

        top1 = (
            {ranked[0][0]}
            if ranked
            else set()
        )

        top5 = {
            user_id
            for user_id, count
            in ranked[:5]
        }

        raw_reach = reach_count(
            rows,
            set(),
        )

        top1_reach = reach_count(
            rows,
            top1,
        )

        top5_reach = reach_count(
            rows,
            top5,
        )

        raw_conversion = percent(
            external,
            raw_reach,
        )

        top5_conversion = percent(
            external,
            top5_reach,
        )

        print(
            f"{family:15}"
            f"{external:4}/500"
            f"{raw_reach:5}/500"
            f"{top1_reach:5}/500"
            f"{top5_reach:5}/500"
            f"{raw_conversion:10.1f}%"
            f"{top5_conversion:10.1f}%"
        )

    print()
    print(
        "FAMILY DETAIL"
    )
    print(
        "============="
    )

    for family, common_name in FAMILIES:
        rows = [
            row
            for row in records
            if row["family"] == family
        ]

        no_id_rows = [
            row
            for row in rows
            if not row[
                "external_id_present"
            ]
        ]

        external = sum(
            bool(
                row[
                    "external_id_present"
                ]
            )
            for row in rows
        )

        ranked = reviewer_ranking(
            no_id_rows
        )

        top1 = (
            {ranked[0][0]}
            if ranked
            else set()
        )

        top5 = {
            user_id
            for user_id, count
            in ranked[:5]
        }

        raw_reach = reach_count(
            rows,
            set(),
        )

        top1_reach = reach_count(
            rows,
            top1,
        )

        top5_reach = reach_count(
            rows,
            top5,
        )

        raw_no_id_reach = (
            raw_reach
            - external
        )

        top1_no_id_reach = (
            top1_reach
            - external
        )

        top5_no_id_reach = (
            top5_reach
            - external
        )

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
            f"  External ID: "
            f"{external}/500 "
            f"({percent(external, 500):.1f}%)"
        )

        print(
            f"  Raw review-based reach: "
            f"{raw_reach}/500 "
            f"({percent(raw_reach, 500):.1f}%)"
        )

        print(
            f"  Top-1-adjusted reach: "
            f"{top1_reach}/500 "
            f"({percent(top1_reach, 500):.1f}%)"
        )

        print(
            f"  Top-5-adjusted reach: "
            f"{top5_reach}/500 "
            f"({percent(top5_reach, 500):.1f}%)"
        )

        print(
            f"  No-ID reviewed observations:"
        )

        print(
            f"    Raw: "
            f"{raw_no_id_reach}/"
            f"{len(no_id_rows)}"
        )

        print(
            f"    Top-1 adjusted: "
            f"{top1_no_id_reach}/"
            f"{len(no_id_rows)}"
        )

        print(
            f"    Top-5 adjusted: "
            f"{top5_no_id_reach}/"
            f"{len(no_id_rows)}"
        )

        if ranked:
            print(
                f"  Dominant reviewer: "
                f"user={ranked[0][0]} "
                f"on {ranked[0][1]} "
                f"no-ID observations"
            )

        print(
            f"  Raw ID conversion: "
            f"{external}/{raw_reach} "
            f"({percent(external, raw_reach):.1f}%)"
        )

        print(
            f"  Top-5-adjusted "
            f"ID conversion: "
            f"{external}/{top5_reach} "
            f"({percent(external, top5_reach):.1f}%)"
        )


if __name__ == "__main__":
    main()