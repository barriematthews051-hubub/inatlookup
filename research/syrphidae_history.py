import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime


OBSERVATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_enriched.csv"
)

IDENTIFICATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_identifications_all.csv"
)

OUTPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_history.csv"
)


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


def outcome(rank):
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
    observations = load_csv(
        OBSERVATIONS_FILE
    )

    identifications = load_csv(
        IDENTIFICATIONS_FILE
    )

    by_observation = defaultdict(list)

    for identification in identifications:
        by_observation[
            identification["observation_id"]
        ].append(identification)

    output_rows = []

    for obs in observations:

        obs_id = obs["observation_id"]

        ids = sorted(
            by_observation[obs_id],
            key=lambda x:
                parse_datetime(x["created_at"])
        )

        current_ids = [
            x for x in ids
            if x["current"] == "True"
        ]

        owner_ids = [
            x for x in ids
            if x["own_observation"] == "True"
        ]

        external_ids = [
            x for x in ids
            if x["own_observation"] != "True"
        ]

        current_owner_ids = [
            x for x in current_ids
            if x["own_observation"] == "True"
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
            lambda x:
                x["taxon_rank"] == "species"
        )

        first_external_species = first_matching(
            external_ids,
            lambda x:
                x["taxon_rank"] == "species"
        )

        first_genus = first_matching(
            ids,
            lambda x:
                x["taxon_rank"] == "genus"
        )

        created = parse_datetime(
            obs["created_at"]
        )

        first_owner_time = (
            parse_datetime(
                first_owner["created_at"]
            )
            if first_owner
            else None
        )

        first_external_time = (
            parse_datetime(
                first_external["created_at"]
            )
            if first_external
            else None
        )

        first_species_time = (
            parse_datetime(
                first_species["created_at"]
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
                    x["taxon_rank"]
                    for x in owner_ids
                }
            ) > 1
        )

        withdrawn_count = sum(
            x["current"] == "False"
            for x in ids
        )

        historical_maverick = any(
            x["category"] == "maverick"
            for x in ids
        )

        historical_disagreement = any(
            x["disagreement"] == "True"
            for x in ids
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

        output_rows.append(
            {
                "observation_id":
                    obs_id,

                "outcome_group":
                    outcome(
                        obs[
                            "community_taxon_rank"
                        ]
                    ),

                "community_taxon_rank":
                    obs[
                        "community_taxon_rank"
                    ],

                "photo_count":
                    obs["photo_count"],

                "project_count":
                    obs["project_count"],

                "history_id_count":
                    len(ids),

                "current_id_count":
                    len(current_ids),

                "withdrawn_id_count":
                    withdrawn_count,

                "owner_history_count":
                    len(owner_ids),

                "external_history_count":
                    len(external_ids),

                "first_owner_rank":
                    (
                        first_owner["taxon_rank"]
                        if first_owner
                        else ""
                    ),

                "final_owner_rank":
                    (
                        final_owner["taxon_rank"]
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
                        first_species["current"]
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
            }
        )

    with open(
        OUTPUT_FILE,
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

    outcomes = Counter(
        row["outcome_group"]
        for row in output_rows
    )

    changed = Counter(
        row["owner_rank_changed"]
        for row in output_rows
    )

    withdrawn = sum(
        int(row["withdrawn_id_count"])
        for row in output_rows
    )

    maverick_obs = sum(
        row["historical_maverick"]
        for row in output_rows
    )

    disagreement_obs = sum(
        row["historical_disagreement"]
        for row in output_rows
    )

    first_species_by = Counter(
        row["first_species_by"] or "NONE"
        for row in output_rows
    )

    print(
        "History rows:",
        len(output_rows)
    )

    print(
        "Outcomes:",
        dict(outcomes)
    )

    print(
        "Owner rank changed:",
        dict(changed)
    )

    print(
        "Withdrawn IDs:",
        withdrawn
    )

    print(
        "Observations with historical maverick:",
        maverick_obs
    )

    print(
        "Observations with historical disagreement:",
        disagreement_obs
    )

    print(
        "First species ID supplied by:",
        dict(first_species_by)
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()