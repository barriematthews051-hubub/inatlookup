import argparse
import csv
import os
import re
from collections import Counter, defaultdict


DATA_DIR = "research/data"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Measure concentration of external "
            "identification activity in a taxon pilot."
        )
    )

    parser.add_argument(
        "--taxon-id",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--taxon-name",
        required=True,
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=500,
    )

    return parser.parse_args()


def slugify(text):
    text = text.strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    )

    return text.strip("_")


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def percent(n, total):
    if total == 0:
        return 0.0

    return round(
        100 * n / total,
        1
    )


def main():
    args = parse_args()

    slug = slugify(
        args.taxon_name
    )

    ids_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"identifications_all.csv"
    )

    if not os.path.exists(ids_file):
        raise RuntimeError(
            f"Identification file not found: "
            f"{ids_file}"
        )

    rows = load_csv(
        ids_file
    )

    external = [
        row
        for row in rows
        if row["own_observation"] != "True"
    ]

    by_identifier = Counter(
        row["identifier_login"]
        or row["identifier_user_id"]
        or "UNKNOWN"
        for row in external
    )

    observations_by_identifier = defaultdict(set)
    ranks_by_identifier = defaultdict(Counter)

    for row in external:
        identifier = (
            row["identifier_login"]
            or row["identifier_user_id"]
            or "UNKNOWN"
        )

        observations_by_identifier[
            identifier
        ].add(
            row["observation_id"]
        )

        rank = (
            row["taxon_rank"]
            or "UNKNOWN"
        )

        ranks_by_identifier[
            identifier
        ][rank] += 1

    total_external = len(
        external
    )

    unique_identifiers = len(
        by_identifier
    )

    ranked = (
        by_identifier.most_common()
    )

    print()
    print(
        f"{args.taxon_name.upper()} "
        f"IDENTIFIER CONCENTRATION"
    )

    print(
        "=" * (
            len(args.taxon_name)
            + 25
        )
    )

    print()
    print(
        "Historical external IDs:",
        total_external
    )

    print(
        "Unique external identifiers:",
        unique_identifiers
    )

    if unique_identifiers:
        print(
            "Mean external IDs per identifier:",
            round(
                total_external
                / unique_identifiers,
                2
            )
        )

    print()
    print(
        "SHARE OF ALL EXTERNAL IDS"
    )

    for top_n in (
        1,
        5,
        10,
        20,
    ):
        count = sum(
            value
            for _, value
            in ranked[:top_n]
        )

        print(
            f"Top {top_n:<2}: "
            f"{count:4d}/"
            f"{total_external} "
            f"({percent(count,total_external):5.1f}%)"
        )

    print()
    print(
        "TOP IDENTIFIERS"
    )

    for number, (
        identifier,
        count
    ) in enumerate(
        ranked[:20],
        start=1
    ):

        obs_count = len(
            observations_by_identifier[
                identifier
            ]
        )

        ranks = (
            ranks_by_identifier[
                identifier
            ]
        )

        species = ranks[
            "species"
        ]

        genus = ranks[
            "genus"
        ]

        higher = (
            count
            - species
            - genus
        )

        print(
            f"{number:2d}. "
            f"{identifier:<25} "
            f"IDs={count:4d} "
            f"observations={obs_count:3d} "
            f"species={species:3d} "
            f"genus={genus:3d} "
            f"other={higher:3d}"
        )

    print()
    print(
        "OBSERVATION COVERAGE BY TOP IDENTIFIERS"
    )

    all_observations = {
        row["observation_id"]
        for row in external
    }

    for top_n in (
        1,
        5,
        10,
        20,
    ):

        covered = set()

        for identifier, _ in ranked[
            :top_n
        ]:
            covered.update(
                observations_by_identifier[
                    identifier
                ]
            )

        print(
            f"Top {top_n:<2}: "
            f"{len(covered):3d}/"
            f"{len(all_observations)} "
            f"externally-attended observations "
            f"({percent(len(covered),len(all_observations)):5.1f}%)"
        )


if __name__ == "__main__":
    main()