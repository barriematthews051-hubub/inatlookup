import json
import os
import statistics
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


def any_count(rows, field):
    return sum(
        row.get(field, 0) > 0
        for row in rows
    )


def print_action_breakdown(rows):
    n = len(rows)

    actions = [
        (
            "Comment",
            "commenter_no_id_count",
        ),
        (
            "Annotation",
            "annotator_no_id_count",
        ),
        (
            "DQA",
            "dqa_no_id_count",
        ),
        (
            "Observation field",
            "field_no_id_count",
        ),
        (
            "Favourite",
            "fave_no_id_count",
        ),
    ]

    for label, field in actions:
        count = any_count(
            rows,
            field,
        )

        print(
            f"    {label:18} "
            f"{count:3}/{n:<3} "
            f"({percent(count, n):5.1f}%)"
        )


def print_reviewer_concentration(
    no_id_rows,
):
    reviewer_counter = Counter()

    observations_by_reviewer = {}

    reviewed_observation_counts = []

    for row in no_id_rows:
        user_ids = set(
            row.get(
                "reviewer_no_id_user_ids",
                [],
            )
        )

        if user_ids:
            reviewed_observation_counts.append(
                len(user_ids)
            )

        for user_id in user_ids:
            reviewer_counter[
                int(user_id)
            ] += 1

            observations_by_reviewer.setdefault(
                int(user_id),
                set(),
            ).add(
                int(
                    row["observation_id"]
                )
            )

    total_pairs = sum(
        reviewer_counter.values()
    )

    unique_reviewers = len(
        reviewer_counter
    )

    print(
        f"    Silent-review pairs: "
        f"{total_pairs}"
    )

    print(
        f"    Unique silent reviewers: "
        f"{unique_reviewers}"
    )

    if not reviewer_counter:
        return

    ranked = (
        reviewer_counter.most_common()
    )

    top1_user, top1_count = (
        ranked[0]
    )

    top5 = ranked[:5]

    top5_count = sum(
        count
        for _, count in top5
    )

    top5_users = {
        user_id
        for user_id, _ in top5
    }

    top5_observations = set()

    for user_id in top5_users:
        top5_observations |= (
            observations_by_reviewer[
                user_id
            ]
        )

    print(
        f"    Top reviewer user ID: "
        f"{top1_user}"
    )

    print(
        f"    Top reviewer coverage: "
        f"{top1_count}/"
        f"{len(no_id_rows)} no-ID obs "
        f"({percent(
            top1_count,
            len(no_id_rows)
        ):.1f}%)"
    )

    print(
        f"    Top reviewer share "
        f"of silent-review pairs: "
        f"{top1_count}/{total_pairs} "
        f"({percent(
            top1_count,
            total_pairs
        ):.1f}%)"
    )

    print(
        f"    Top-5 share of "
        f"silent-review pairs: "
        f"{top5_count}/{total_pairs} "
        f"({percent(
            top5_count,
            total_pairs
        ):.1f}%)"
    )

    print(
        f"    No-ID observations "
        f"covered by Top-5: "
        f"{len(top5_observations)}/"
        f"{len(no_id_rows)} "
        f"({percent(
            len(top5_observations),
            len(no_id_rows)
        ):.1f}%)"
    )

    if reviewed_observation_counts:
        print(
            "    Median silent reviewers "
            "per reviewed observation: "
            f"{statistics.median(
                reviewed_observation_counts
            ):.1f}"
        )

    print(
        "    Top 5 reviewers:"
    )

    for (
        rank,
        (
            user_id,
            count,
        ),
    ) in enumerate(
        top5,
        start=1,
    ):
        print(
            f"      {rank}. "
            f"user={user_id:<10} "
            f"observations={count}"
        )


def main():
    records = load_records()

    print()
    print(
        "PUBLIC INTERACTION DIAGNOSTICS"
    )
    print(
        "=============================="
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
            f"  Observations: "
            f"{len(rows)}"
        )

        print(
            f"  No external ID: "
            f"{len(no_id_rows)}"
        )

        reviewed_no_id = (
            any_count(
                no_id_rows,
                "reviewer_no_id_count",
            )
        )

        print(
            f"  No-ID obs with silent review: "
            f"{reviewed_no_id}/"
            f"{len(no_id_rows)} "
            f"({percent(
                reviewed_no_id,
                len(no_id_rows)
            ):.1f}%)"
        )

        print()
        print(
            "  SILENT-REVIEW CONCENTRATION"
        )

        print_reviewer_concentration(
            no_id_rows
        )

        print()
        print(
            "  NON-ID ACTION TYPES "
            "(ALL 500)"
        )

        print_action_breakdown(
            rows
        )

        print()
        print(
            "  NON-ID ACTION TYPES "
            "(NO-EXTERNAL-ID ONLY)"
        )

        print_action_breakdown(
            no_id_rows
        )


if __name__ == "__main__":
    main()