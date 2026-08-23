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
    "syrphidae_pilot_500_identifications.csv"
)

OUTPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_sequence.csv"
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


def outcome_group(rank):
    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    if not rank:
        return "none"

    return "other"


def analyse_sequence(
    observation,
    identifications
):
    ids = sorted(
        [
            x
            for x in identifications
            if x["current"] == "True"
        ],
        key=lambda x:
            parse_datetime(x["created_at"])
    )

    external = [
        x
        for x in ids
        if x["own_observation"] != "True"
    ]

    created = parse_datetime(
        observation["created_at"]
    )

    first_id = (
        ids[0]
        if ids
        else None
    )

    first_external = (
        external[0]
        if external
        else None
    )

    second_external = (
        external[1]
        if len(external) >= 2
        else None
    )

    last_external = (
        external[-1]
        if external
        else None
    )

    first_external_time = (
        parse_datetime(
            first_external["created_at"]
        )
        if first_external
        else None
    )

    last_external_time = (
        parse_datetime(
            last_external["created_at"]
        )
        if last_external
        else None
    )

    return {
        "observation_id":
            observation["observation_id"],

        "outcome_group":
            outcome_group(
                observation[
                    "community_taxon_rank"
                ]
            ),

        "community_taxon_rank":
            observation[
                "community_taxon_rank"
            ],

        "photo_count":
            observation["photo_count"],

        "project_count":
            observation["project_count"],

        "total_id_count":
            len(ids),

        "external_id_count":
            len(external),

        "first_id_owner": (
            first_id[
                "own_observation"
            ]
            if first_id
            else ""
        ),

        "first_id_rank": (
            first_id["taxon_rank"]
            if first_id
            else ""
        ),

        "first_id_category": (
            first_id["category"]
            if first_id
            else ""
        ),

        "first_id_vision": (
            first_id["vision"]
            if first_id
            else ""
        ),

        "first_external_user_id": (
            first_external[
                "identifier_user_id"
            ]
            if first_external
            else ""
        ),

        "first_external_rank": (
            first_external[
                "taxon_rank"
            ]
            if first_external
            else ""
        ),

        "first_external_category": (
            first_external[
                "category"
            ]
            if first_external
            else ""
        ),

        "first_external_vision": (
            first_external[
                "vision"
            ]
            if first_external
            else ""
        ),

        "first_external_disagreement": (
            first_external[
                "disagreement"
            ]
            if first_external
            else ""
        ),

        "second_external_rank": (
            second_external[
                "taxon_rank"
            ]
            if second_external
            else ""
        ),

        "second_external_category": (
            second_external[
                "category"
            ]
            if second_external
            else ""
        ),

        "second_external_disagreement": (
            second_external[
                "disagreement"
            ]
            if second_external
            else ""
        ),

        "hours_to_first_external":
            hours_between(
                created,
                first_external_time
            ),

        "hours_first_to_last_external":
            hours_between(
                first_external_time,
                last_external_time
            ),

        "any_external_disagreement":
            any(
                x["disagreement"] == "True"
                for x in external
            ),

        "any_external_vision":
            any(
                x["vision"] == "True"
                for x in external
            ),
    }


def median_hours(rows, field):
    values = [
        float(row[field])
        for row in rows
        if row[field] != ""
    ]

    if not values:
        return None

    return round(
        statistics.median(values),
        1
    )


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
        rows.append(
            analyse_sequence(
                observation,
                by_observation[
                    observation[
                        "observation_id"
                    ]
                ]
            )
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
                rows[0].keys()
            )
        )

        writer.writeheader()
        writer.writerows(rows)

    print(
        "Sequence rows:",
        len(rows)
    )

    print()

    print(
        "FIRST EXTERNAL ID RANK"
    )

    for outcome in (
        "species",
        "genus",
        "none",
        "other",
    ):
        subset = [
            row
            for row in rows
            if row["outcome_group"]
            == outcome
        ]

        ranks = Counter(
            row["first_external_rank"]
            or "NONE"
            for row in subset
        )

        print(
            outcome,
            len(subset),
            dict(ranks)
        )

    print()

    print(
        "FIRST EXTERNAL ID CATEGORY"
    )

    for outcome in (
        "species",
        "genus",
        "none",
        "other",
    ):
        subset = [
            row
            for row in rows
            if row["outcome_group"]
            == outcome
        ]

        categories = Counter(
            row[
                "first_external_category"
            ]
            or "NONE"
            for row in subset
        )

        print(
            outcome,
            dict(categories)
        )

    print()

    print(
        "MEDIAN HOURS TO "
        "FIRST EXTERNAL ID"
    )

    for outcome in (
        "species",
        "genus",
        "none",
        "other",
    ):
        subset = [
            row
            for row in rows
            if row["outcome_group"]
            == outcome
        ]

        print(
            outcome,
            median_hours(
                subset,
                "hours_to_first_external"
            )
        )

    print()

    print(
        "MEDIAN HOURS FIRST TO "
        "LAST EXTERNAL ID"
    )

    for outcome in (
        "species",
        "genus",
        "none",
        "other",
    ):
        subset = [
            row
            for row in rows
            if row["outcome_group"]
            == outcome
        ]

        print(
            outcome,
            median_hours(
                subset,
                "hours_first_to_last_external"
            )
        )

    print()

    print(
        "EXTERNAL ID COUNT"
    )

    for outcome in (
        "species",
        "genus",
        "none",
        "other",
    ):
        subset = [
            row
            for row in rows
            if row["outcome_group"]
            == outcome
        ]

        counts = Counter(
            int(
                row[
                    "external_id_count"
                ]
            )
            for row in subset
        )

        print(
            outcome,
            dict(
                sorted(
                    counts.items()
                )
            )
        )

    print()

    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()