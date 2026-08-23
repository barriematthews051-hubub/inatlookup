import argparse
import csv
import os
import re
from collections import defaultdict
from datetime import datetime


DATA_DIR = "research/data"


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Build an observation-level analysis table "
            "for a taxon pilot sample."
        )
    )

    parser.add_argument(
        "--taxon-id",
        type=int,
        required=True,
        help="iNaturalist taxon ID.",
    )

    parser.add_argument(
        "--taxon-name",
        required=True,
        help="Taxon name, e.g. Syrphidae.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=500,
        help="Pilot sample size. Default: 500.",
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


def parse_datetime(text):
    if not text:
        return None

    return datetime.fromisoformat(
        text.replace("Z", "+00:00")
    )


def hours_between(start, end):
    if start is None or end is None:
        return ""

    return round(
        (end - start).total_seconds()
        / 3600,
        2
    )


def outcome_group(rank):
    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    if not rank:
        return "none"

    return "other"


def first_matching(rows, predicate):
    for row in rows:
        if predicate(row):
            return row

    return None


def main():
    args = parse_args()

    slug = slugify(
        args.taxon_name
    )

    observations_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"enriched.csv"
    )

    identifications_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"identifications_all.csv"
    )

    experience_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"identifier_experience.csv"
    )

    output_file = os.path.join(
        DATA_DIR,
        f"{slug}_pilot_"
        f"{args.sample_size}_"
        f"analysis.csv"
    )

    for filename in (
        observations_file,
        identifications_file,
        experience_file,
    ):
        if not os.path.exists(filename):
            raise RuntimeError(
                f"Required file not found: "
                f"{filename}"
            )

    observations = load_csv(
        observations_file
    )

    identifications = load_csv(
        identifications_file
    )

    experience_rows = load_csv(
        experience_file
    )

    experience_by_observation = {
        row["observation_id"]: row
        for row in experience_rows
    }

    by_observation = defaultdict(
        list
    )

    for identification in identifications:
        by_observation[
            identification[
                "observation_id"
            ]
        ].append(
            identification
        )

    output_rows = []

    for observation in observations:

        observation_id = (
            observation[
                "observation_id"
            ]
        )

        ids = sorted(
            by_observation[
                observation_id
            ],
            key=lambda row:
                parse_datetime(
                    row["created_at"]
                )
        )

        current_ids = [
            row
            for row in ids
            if row[
                "current"
            ] == "True"
        ]

        owner_ids = [
            row
            for row in ids
            if row[
                "own_observation"
            ] == "True"
        ]

        external_ids = [
            row
            for row in ids
            if row[
                "own_observation"
            ] != "True"
        ]

        current_owner_ids = [
            row
            for row in current_ids
            if row[
                "own_observation"
            ] == "True"
        ]

        first_owner = (
            owner_ids[0]
            if owner_ids
            else None
        )

        final_owner = (
            current_owner_ids[-1]
            if current_owner_ids
            else None
        )

        first_external = (
            external_ids[0]
            if external_ids
            else None
        )

        first_species = first_matching(
            ids,
            lambda row:
                row[
                    "taxon_rank"
                ] == "species"
        )

        first_external_species = (
            first_matching(
                external_ids,
                lambda row:
                    row[
                        "taxon_rank"
                    ] == "species"
            )
        )

        created = parse_datetime(
            observation[
                "created_at"
            ]
        )

        first_owner_time = (
            parse_datetime(
                first_owner[
                    "created_at"
                ]
            )
            if first_owner
            else None
        )

        first_external_time = (
            parse_datetime(
                first_external[
                    "created_at"
                ]
            )
            if first_external
            else None
        )

        first_species_time = (
            parse_datetime(
                first_species[
                    "created_at"
                ]
            )
            if first_species
            else None
        )

        first_external_species_time = (
            parse_datetime(
                first_external_species[
                    "created_at"
                ]
            )
            if first_external_species
            else None
        )

        owner_rank_changed = (
            len(
                {
                    row[
                        "taxon_rank"
                    ]
                    for row in owner_ids
                }
            ) > 1
        )

        withdrawn_id_count = sum(
            row[
                "current"
            ] == "False"
            for row in ids
        )

        historical_maverick = any(
            row[
                "category"
            ] == "maverick"
            for row in ids
        )

        historical_disagreement = any(
            row[
                "disagreement"
            ] == "True"
            for row in ids
        )

        species_first_by = ""

        if first_species:
            species_first_by = (
                "owner"
                if first_species[
                    "own_observation"
                ] == "True"
                else "external"
            )

        experience = (
            experience_by_observation.get(
                observation_id,
                {}
            )
        )

        output_rows.append(
            {
                **observation,

                "outcome_group":
                    outcome_group(
                        observation[
                            "community_taxon_rank"
                        ]
                    ),

                "history_id_count":
                    len(ids),

                "current_id_count":
                    len(current_ids),

                "withdrawn_id_count":
                    withdrawn_id_count,

                "owner_history_count":
                    len(owner_ids),

                "external_history_count":
                    len(external_ids),

                "first_owner_rank":
                    (
                        first_owner[
                            "taxon_rank"
                        ]
                        if first_owner
                        else ""
                    ),

                "final_owner_rank":
                    (
                        final_owner[
                            "taxon_rank"
                        ]
                        if final_owner
                        else ""
                    ),

                "owner_rank_changed":
                    owner_rank_changed,

                "first_external_rank":
                    (
                        first_external[
                            "taxon_rank"
                        ]
                        if first_external
                        else ""
                    ),

                "first_external_category":
                    (
                        first_external[
                            "category"
                        ]
                        if first_external
                        else ""
                    ),

                "first_external_disagreement":
                    (
                        first_external[
                            "disagreement"
                        ]
                        if first_external
                        else ""
                    ),

                "first_species_by":
                    species_first_by,

                "first_species_current":
                    (
                        first_species[
                            "current"
                        ]
                        if first_species
                        else ""
                    ),

                "historical_maverick":
                    historical_maverick,

                "historical_disagreement":
                    historical_disagreement,

                "hours_post_to_first_owner":
                    hours_between(
                        created,
                        first_owner_time
                    ),

                "hours_post_to_first_external":
                    hours_between(
                        created,
                        first_external_time
                    ),

                "hours_post_to_first_species":
                    hours_between(
                        created,
                        first_species_time
                    ),

                "hours_post_to_first_external_species":
                    hours_between(
                        created,
                        first_external_species_time
                    ),

                "hours_owner_to_first_external":
                    hours_between(
                        first_owner_time,
                        first_external_time
                    ),

                "first_external_prior_taxon_ids":
                    experience.get(
                        "first_external_prior_taxon_ids",
                        ""
                    ),

                "max_prior_taxon_ids":
                    experience.get(
                        "max_prior_taxon_ids",
                        ""
                    ),

                "most_experienced_login":
                    experience.get(
                        "most_experienced_login",
                        ""
                    ),

                "most_experienced_rank":
                    experience.get(
                        "most_experienced_rank",
                        ""
                    ),

                "zero_experience_external_ids":
                    experience.get(
                        "zero_experience_external_ids",
                        ""
                    ),
            }
        )

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(
                output_rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(
            output_rows
        )

    print(
        "Taxon:",
        args.taxon_name
    )

    print(
        "Analysis rows:",
        len(output_rows)
    )

    print(
        "Output:",
        output_file
    )


if __name__ == "__main__":
    main()