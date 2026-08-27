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


ACTIONS = [
    (
        "Comment",
        "commenter_no_id_user_ids",
    ),
    (
        "Annotation",
        "annotator_no_id_user_ids",
    ),
    (
        "DQA",
        "dqa_no_id_user_ids",
    ),
    (
        "Observation field",
        "field_no_id_user_ids",
    ),
]


DETAIL_THRESHOLD = 10.0


def percent(
    numerator,
    denominator,
):
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
        for record
        in data["records"].values()
        if record.get("status") == "ok"
    ]


def int_set(
    row,
    field,
):
    return {
        int(value)
        for value
        in row.get(
            field,
            [],
        )
    }


def strict_users(row):
    return int_set(
        row,
        "strict_non_id_user_ids",
    )


def action_users(
    row,
    field,
):
    return int_set(
        row,
        field,
    )


def observation_count(
    rows,
    field,
):
    return sum(
        bool(
            action_users(
                row,
                field,
            )
        )
        for row in rows
    )


def pair_count(
    rows,
    field,
):
    return sum(
        len(
            action_users(
                row,
                field,
            )
        )
        for row in rows
    )


def unique_users(
    rows,
    field,
):
    users = set()

    for row in rows:
        users |= action_users(
            row,
            field,
        )

    return users


def strict_observation_count(
    rows,
):
    return sum(
        bool(
            strict_users(row)
        )
        for row in rows
    )


def strict_pair_count(
    rows,
):
    return sum(
        len(
            strict_users(row)
        )
        for row in rows
    )


def strict_unique_users(
    rows,
):
    users = set()

    for row in rows:
        users |= strict_users(
            row
        )

    return users


def concentration(
    rows,
    user_getter,
):
    counter = Counter()
    observations_by_user = {}

    for row in rows:
        users = user_getter(
            row
        )

        for user_id in users:
            counter[
                user_id
            ] += 1

            observations_by_user.setdefault(
                user_id,
                set(),
            ).add(
                int(
                    row[
                        "observation_id"
                    ]
                )
            )

    total_pairs = sum(
        counter.values()
    )

    if not counter:
        return {
            "total_pairs": 0,
            "unique_users": 0,
            "top1_user": None,
            "top1_count": 0,
            "top1_share": 0.0,
            "top5_count": 0,
            "top5_share": 0.0,
            "top5_observations": 0,
            "ranked": [],
        }

    ranked = (
        counter.most_common()
    )

    top1_user, top1_count = (
        ranked[0]
    )

    top5 = ranked[:5]

    top5_count = sum(
        count
        for _, count
        in top5
    )

    top5_users = {
        user_id
        for user_id, _
        in top5
    }

    top5_observations = set()

    for user_id in top5_users:
        top5_observations |= (
            observations_by_user[
                user_id
            ]
        )

    return {
        "total_pairs":
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


def dominant_action(rows):
    results = []

    for label, field in ACTIONS:
        count = observation_count(
            rows,
            field,
        )

        results.append(
            (
                count,
                label,
            )
        )

    results.sort(
        reverse=True
    )

    if (
        not results
        or results[0][0] == 0
    ):
        return "none"

    return results[0][1]


def action_combination(row):
    active = []

    for label, field in ACTIONS:
        if action_users(
            row,
            field,
        ):
            active.append(
                label
            )

    if not active:
        return None

    return " + ".join(
        active
    )


def print_summary_matrix(
    records,
):
    print()
    print(
        "STRICT NON-ID ACTION SUMMARY"
    )
    print(
        "============================"
    )
    print()

    print(
        f"{'Family':15}"
        f"{'All':>9}"
        f"{'No-ID':>11}"
        f"{'With-ID':>11}"
        f"  Dominant action"
    )

    print(
        "-" * 68
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

        all_count = (
            strict_observation_count(
                rows
            )
        )

        no_id_count = (
            strict_observation_count(
                no_id_rows
            )
        )

        with_id_count = (
            strict_observation_count(
                with_id_rows
            )
        )

        print(
            f"{family:15}"
            f"{all_count:4}/500"
            f"{no_id_count:4}/"
            f"{len(no_id_rows):<4}"
            f"{with_id_count:4}/"
            f"{len(with_id_rows):<4}"
            f"  {dominant_action(rows)}"
        )


def print_action_matrix(
    records,
):
    print()
    print(
        "ACTION TYPE MATRIX - ALL 500"
    )
    print(
        "============================"
    )
    print()

    print(
        f"{'Family':15}"
        f"{'Comment':>9}"
        f"{'Annot':>9}"
        f"{'DQA':>9}"
        f"{'Field':>9}"
    )

    print(
        "-" * 51
    )

    for family, common_name in FAMILIES:
        rows = [
            row
            for row in records
            if row["family"] == family
        ]

        counts = []

        for label, field in ACTIONS:
            counts.append(
                observation_count(
                    rows,
                    field,
                )
            )

        print(
            f"{family:15}"
            f"{counts[0]:9}"
            f"{counts[1]:9}"
            f"{counts[2]:9}"
            f"{counts[3]:9}"
        )


def print_subset_breakdown(
    title,
    rows,
):
    print()
    print(title)
    print("-" * len(title))

    n = len(rows)

    strict_obs = (
        strict_observation_count(
            rows
        )
    )

    strict_pairs = (
        strict_pair_count(
            rows
        )
    )

    strict_users_count = len(
        strict_unique_users(
            rows
        )
    )

    print(
        f"  Observations: {n}"
    )

    print(
        f"  Any strict non-ID action: "
        f"{strict_obs}/{n} "
        f"({percent(
            strict_obs,
            n
        ):.1f}%)"
    )

    print(
        f"  User-observation pairs: "
        f"{strict_pairs}"
    )

    print(
        f"  Unique action users: "
        f"{strict_users_count}"
    )

    print()

    for label, field in ACTIONS:
        obs_count = (
            observation_count(
                rows,
                field,
            )
        )

        pairs = pair_count(
            rows,
            field,
        )

        users = len(
            unique_users(
                rows,
                field,
            )
        )

        print(
            f"  {label}"
        )

        print(
            f"    Observations: "
            f"{obs_count}/{n} "
            f"({percent(
                obs_count,
                n
            ):.1f}%)"
        )

        print(
            f"    Pairs: "
            f"{pairs}"
        )

        print(
            f"    Unique users: "
            f"{users}"
        )


def print_action_concentration(
    rows,
):
    print()
    print(
        "  USER CONCENTRATION"
    )

    print(
        "  ------------------"
    )

    strict = concentration(
        rows,
        strict_users,
    )

    print()
    print(
        "  ALL STRICT ACTIONS"
    )

    if not strict[
        "total_pairs"
    ]:
        print(
            "    No strict non-ID "
            "action pairs."
        )

    else:
        print(
            f"    Pairs: "
            f"{strict['total_pairs']}"
        )

        print(
            f"    Unique users: "
            f"{strict['unique_users']}"
        )

        print(
            f"    Top user: "
            f"{strict['top1_user']} "
            f"on "
            f"{strict['top1_count']} "
            f"observations"
        )

        print(
            f"    Top user share "
            f"of pairs: "
            f"{strict['top1_share']:.1f}%"
        )

        print(
            f"    Top-5 share "
            f"of pairs: "
            f"{strict['top5_share']:.1f}%"
        )

        print(
            f"    Observations covered "
            f"by Top-5 users: "
            f"{strict['top5_observations']}"
        )

        print(
            "    Top 5:"
        )

        for (
            rank,
            (
                user_id,
                count,
            ),
        ) in enumerate(
            strict["ranked"][:5],
            start=1,
        ):
            print(
                f"      {rank}. "
                f"user={user_id:<10} "
                f"observations={count}"
            )

    for label, field in ACTIONS:
        result = concentration(
            rows,
            lambda row,
            field=field:
                action_users(
                    row,
                    field,
                ),
        )

        print()
        print(
            f"  {label.upper()}"
        )

        if not result[
            "total_pairs"
        ]:
            print(
                "    No pairs."
            )
            continue

        print(
            f"    Pairs: "
            f"{result['total_pairs']}"
        )

        print(
            f"    Unique users: "
            f"{result['unique_users']}"
        )

        print(
            f"    Top user: "
            f"{result['top1_user']} "
            f"on "
            f"{result['top1_count']} "
            f"observations"
        )

        print(
            f"    Top user share: "
            f"{result['top1_share']:.1f}%"
        )

        print(
            f"    Top-5 share: "
            f"{result['top5_share']:.1f}%"
        )


def print_combinations(
    rows,
):
    counter = Counter()

    for row in rows:
        combination = (
            action_combination(
                row
            )
        )

        if combination:
            counter[
                combination
            ] += 1

    print()
    print(
        "  ACTION COMBINATIONS"
    )

    print(
        "  -------------------"
    )

    if not counter:
        print(
            "    None."
        )
        return

    for (
        combination,
        count,
    ) in counter.most_common():
        print(
            f"    {combination:45}"
            f"{count}"
        )


def print_detailed_families(
    records,
):
    print()
    print(
        "DETAILED HIGH-ACTION FAMILIES"
    )
    print(
        "============================="
    )

    for family, common_name in FAMILIES:
        rows = [
            row
            for row in records
            if row["family"] == family
        ]

        strict_count = (
            strict_observation_count(
                rows
            )
        )

        strict_rate = percent(
            strict_count,
            len(rows),
        )

        if (
            strict_rate
            < DETAIL_THRESHOLD
        ):
            continue

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

        print_subset_breakdown(
            "ALL OBSERVATIONS",
            rows,
        )

        print_subset_breakdown(
            "NO EXTERNAL ID",
            no_id_rows,
        )

        print_subset_breakdown(
            "WITH EXTERNAL ID",
            with_id_rows,
        )

        print_action_concentration(
            rows
        )

        print_combinations(
            rows
        )


def print_global_summary(
    records,
):
    print()
    print(
        "ALL 18 FAMILIES"
    )
    print(
        "==============="
    )

    strict_obs = (
        strict_observation_count(
            records
        )
    )

    no_id_rows = [
        row
        for row in records
        if not row[
            "external_id_present"
        ]
    ]

    with_id_rows = [
        row
        for row in records
        if row[
            "external_id_present"
        ]
    ]

    print_subset_breakdown(
        "ALL 9,000 OBSERVATIONS",
        records,
    )

    print_subset_breakdown(
        "NO EXTERNAL ID",
        no_id_rows,
    )

    print_subset_breakdown(
        "WITH EXTERNAL ID",
        with_id_rows,
    )

    print()
    print(
        f"Overall strict-action "
        f"observations: "
        f"{strict_obs}/"
        f"{len(records)} "
        f"({percent(
            strict_obs,
            len(records)
        ):.1f}%)"
    )


def main():
    records = load_records()

    print()
    print(
        "NON-ID ACTION DIAGNOSTICS"
    )
    print(
        "========================="
    )

    print()
    print(
        "Strict actions = comments, "
        "annotations, DQA votes, "
        "or observation-field activity "
        "by users who never identified "
        "that observation."
    )

    print_summary_matrix(
        records
    )

    print_action_matrix(
        records
    )

    print_detailed_families(
        records
    )

    print_global_summary(
        records
    )


if __name__ == "__main__":
    main()