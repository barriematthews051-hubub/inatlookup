import json
import os
from collections import Counter, defaultdict


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

    return numerator / denominator * 100


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


def annotators(row):
    return {
        int(value)
        for value in row.get(
            "annotator_no_id_user_ids",
            [],
        )
    }


def analyse(rows):
    counter = Counter()
    observations_by_user = defaultdict(set)

    annotated_observations = 0

    for row in rows:
        users = annotators(row)

        if users:
            annotated_observations += 1

        observation_id = int(
            row["observation_id"]
        )

        for user_id in users:
            counter[user_id] += 1
            observations_by_user[
                user_id
            ].add(
                observation_id
            )

    total_pairs = sum(
        counter.values()
    )

    ranked = counter.most_common()

    if ranked:
        top1_user, top1_count = ranked[0]
    else:
        top1_user = None
        top1_count = 0

    top5 = ranked[:5]

    top5_count = sum(
        count
        for _, count in top5
    )

    top5_observations = set()

    for user_id, _ in top5:
        top5_observations |= (
            observations_by_user[
                user_id
            ]
        )

    return {
        "observations":
            len(rows),

        "annotated_observations":
            annotated_observations,

        "pairs":
            total_pairs,

        "unique_users":
            len(counter),

        "top1_user":
            top1_user,

        "top1_count":
            top1_count,

        "top1_share":
            percent(
                top1_count,
                total_pairs,
            ),

        "top5_count":
            top5_count,

        "top5_share":
            percent(
                top5_count,
                total_pairs,
            ),

        "top5_observations":
            len(
                top5_observations
            ),

        "ranked":
            ranked,
    }


def print_result(
    title,
    result,
):
    print()
    print(title)
    print("-" * len(title))

    n = result[
        "observations"
    ]

    annotated = result[
        "annotated_observations"
    ]

    print(
        f"  Annotation-no-ID observations: "
        f"{annotated}/{n} "
        f"({percent(annotated, n):.1f}%)"
    )

    print(
        f"  User-observation pairs: "
        f"{result['pairs']}"
    )

    print(
        f"  Unique annotators: "
        f"{result['unique_users']}"
    )

    if not result[
        "pairs"
    ]:
        return

    print(
        f"  Top annotator: "
        f"user={result['top1_user']} "
        f"on {result['top1_count']} "
        f"observations"
    )

    print(
        f"  Top annotator share "
        f"of pairs: "
        f"{result['top1_share']:.1f}%"
    )

    print(
        f"  Top-5 share "
        f"of pairs: "
        f"{result['top5_share']:.1f}%"
    )

    print(
        f"  Observations covered "
        f"by Top-5 annotators: "
        f"{result['top5_observations']}/"
        f"{n} "
        f"({percent(
            result['top5_observations'],
            n
        ):.1f}%)"
    )

    print(
        "  Top 5 annotators:"
    )

    for (
        rank,
        (
            user_id,
            count,
        ),
    ) in enumerate(
        result["ranked"][:5],
        start=1,
    ):
        print(
            f"    {rank}. "
            f"user={user_id:<10} "
            f"observations={count}"
        )


def main():
    records = load_records()

    global_user_families = (
        defaultdict(set)
    )

    global_user_observations = (
        defaultdict(set)
    )

    print()
    print(
        "ANNOTATION CONCENTRATION "
        "DIAGNOSTICS"
    )
    print(
        "================================"
    )

    print()
    print(
        "Annotation users here are users "
        "who added an annotation but never "
        "identified that same observation."
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

        with_id_rows = [
            row
            for row in rows
            if row[
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

        print_result(
            "ALL 500",
            analyse(rows),
        )

        print_result(
            "NO EXTERNAL ID",
            analyse(
                no_id_rows
            ),
        )

        print_result(
            "WITH EXTERNAL ID",
            analyse(
                with_id_rows
            ),
        )

        for row in rows:
            observation_id = int(
                row["observation_id"]
            )

            for user_id in annotators(
                row
            ):
                global_user_families[
                    user_id
                ].add(
                    family
                )

                global_user_observations[
                    user_id
                ].add(
                    observation_id
                )

    print()
    print(
        "CROSS-FAMILY ANNOTATORS"
    )
    print(
        "======================="
    )

    ranked_users = sorted(
        global_user_observations,
        key=lambda user_id: (
            -len(
                global_user_observations[
                    user_id
                ]
            ),
            -len(
                global_user_families[
                    user_id
                ]
            ),
            user_id,
        ),
    )

    for rank, user_id in enumerate(
        ranked_users[:20],
        start=1,
    ):
        families = sorted(
            global_user_families[
                user_id
            ]
        )

        print(
            f"{rank:2}. "
            f"user={user_id:<10} "
            f"observations="
            f"{len(
                global_user_observations[
                    user_id
                ]
            ):4} "
            f"families="
            f"{len(families):2}"
        )

        print(
            "    "
            + ", ".join(
                families
            )
        )


if __name__ == "__main__":
    main()