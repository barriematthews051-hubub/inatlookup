import csv
from collections import Counter, defaultdict
from datetime import datetime


OBSERVATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_enriched.csv"
)

IDENTIFICATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_identifications.csv"
)

OUTPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_analysis.csv"
)


def parse_datetime(text):
    if not text:
        return None

    return datetime.fromisoformat(
        text.replace("Z", "+00:00")
    )


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:

        return list(
            csv.DictReader(f)
        )


def outcome_group(rank):
    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    if not rank:
        return "none"

    return "other"


def analyse_observation(
    observation,
    identifications
):
    current_ids = [
        x
        for x in identifications
        if x["current"] == "True"
    ]

    identifier_ids = {
        x["identifier_user_id"]
        for x in current_ids
        if x["identifier_user_id"]
    }

    categories = Counter(
        x["category"]
        for x in current_ids
    )

    ranks = Counter(
        x["taxon_rank"]
        for x in current_ids
    )

    owner_count = sum(
        x["own_observation"] == "True"
        for x in current_ids
    )

    external_count = sum(
        x["own_observation"] != "True"
        for x in current_ids
    )

    disagreement_count = sum(
        x["disagreement"] == "True"
        for x in current_ids
    )

    vision_count = sum(
        x["vision"] == "True"
        for x in current_ids
    )

    id_times = sorted(
        t
        for t in (
            parse_datetime(
                x["created_at"]
            )
            for x in current_ids
        )
        if t is not None
    )

    observation_created = (
        parse_datetime(
            observation["created_at"]
        )
    )

    first_id_at = (
        id_times[0]
        if id_times
        else None
    )

    last_id_at = (
        id_times[-1]
        if id_times
        else None
    )

    hours_to_first_id = ""

    if (
        observation_created is not None
        and first_id_at is not None
    ):
        delta = (
            first_id_at
            - observation_created
        )

        hours_to_first_id = round(
            delta.total_seconds()
            / 3600,
            2
        )

    hours_first_to_last_id = ""

    if (
        first_id_at is not None
        and last_id_at is not None
    ):
        delta = (
            last_id_at
            - first_id_at
        )

        hours_first_to_last_id = round(
            delta.total_seconds()
            / 3600,
            2
        )

    return {
        **observation,

        "outcome_group": outcome_group(
            observation[
                "community_taxon_rank"
            ]
        ),

        "current_id_count":
            len(current_ids),

        "unique_identifier_count":
            len(identifier_ids),

        "owner_id_count":
            owner_count,

        "external_id_count":
            external_count,

        "improving_count":
            categories["improving"],

        "supporting_count":
            categories["supporting"],

        "leading_count":
            categories["leading"],

        "maverick_count":
            categories["maverick"],

        "disagreement_id_count":
            disagreement_count,

        "vision_id_count":
            vision_count,

        "species_id_count":
            ranks["species"],

        "genus_id_count":
            ranks["genus"],

        "family_id_count":
            ranks["family"],

        "first_id_at": (
            first_id_at.isoformat()
            if first_id_at
            else ""
        ),

        "last_id_at": (
            last_id_at.isoformat()
            if last_id_at
            else ""
        ),

        "hours_to_first_id":
            hours_to_first_id,

        "hours_first_to_last_id":
            hours_first_to_last_id,
    }


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
            identification[
                "observation_id"
            ]
        ].append(
            identification
        )

    rows = []

    for observation in observations:

        observation_id = (
            observation[
                "observation_id"
            ]
        )

        rows.append(
            analyse_observation(
                observation,
                by_observation[
                    observation_id
                ]
            )
        )

    fieldnames = list(
        rows[0].keys()
    )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    outcomes = Counter(
        row["outcome_group"]
        for row in rows
    )

    id_counts = Counter(
        int(row["current_id_count"])
        for row in rows
    )

    print(
        "Analysis rows:",
        len(rows)
    )

    print(
        "Outcome groups:",
        dict(outcomes)
    )

    print(
        "Current ID counts:",
        dict(
            sorted(
                id_counts.items()
            )
        )
    )

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()