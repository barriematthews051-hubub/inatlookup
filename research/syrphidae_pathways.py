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
        return None

    return (
        end - start
    ).total_seconds() / 3600


def outcome(rank):
    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    if not rank:
        return "none"

    return "other"


def median(values):
    values = [
        x for x in values
        if x is not None
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
            identification["observation_id"]
        ].append(identification)

    pathway_counts = Counter()

    timing = defaultdict(
        lambda: {
            "first_external": [],
            "second_external": [],
            "first_to_last_multi": [],
        }
    )

    first_external_vision = defaultdict(
        lambda: Counter()
    )

    first_external_disagreement = defaultdict(
        lambda: Counter()
    )

    for obs in observations:

        obs_id = obs["observation_id"]

        ids = sorted(
            [
                x
                for x in by_observation[obs_id]
                if x["current"] == "True"
            ],
            key=lambda x:
                parse_datetime(x["created_at"])
        )

        owner_ids = [
            x
            for x in ids
            if x["own_observation"] == "True"
        ]

        external_ids = [
            x
            for x in ids
            if x["own_observation"] != "True"
        ]

        result = outcome(
            obs["community_taxon_rank"]
        )

        owner_rank = (
            owner_ids[0]["taxon_rank"]
            if owner_ids
            else "NO_OWNER_ID"
        )

        if external_ids:
            first_external = external_ids[0]

            external_rank = (
                first_external["taxon_rank"]
                or "UNKNOWN"
            )

            external_category = (
                first_external["category"]
                or "UNKNOWN"
            )
        else:
            first_external = None
            external_rank = "NO_EXTERNAL_ID"
            external_category = "NONE"

        pathway = (
            result,
            owner_rank,
            external_rank,
            external_category,
        )

        pathway_counts[pathway] += 1

        created = parse_datetime(
            obs["created_at"]
        )

        if first_external:
            first_time = parse_datetime(
                first_external["created_at"]
            )

            timing[result][
                "first_external"
            ].append(
                hours_between(
                    created,
                    first_time
                )
            )

            first_external_vision[result][
                first_external["vision"]
            ] += 1

            first_external_disagreement[result][
                first_external["disagreement"]
            ] += 1

        if len(external_ids) >= 2:
            first_time = parse_datetime(
                external_ids[0]["created_at"]
            )

            second_time = parse_datetime(
                external_ids[1]["created_at"]
            )

            last_time = parse_datetime(
                external_ids[-1]["created_at"]
            )

            timing[result][
                "second_external"
            ].append(
                hours_between(
                    created,
                    second_time
                )
            )

            timing[result][
                "first_to_last_multi"
            ].append(
                hours_between(
                    first_time,
                    last_time
                )
            )

    print("TOP PATHWAYS")
    print()

    for (
        result,
        owner_rank,
        external_rank,
        category
    ), count in pathway_counts.most_common(25):

        print(
            f"{count:3d}  "
            f"Outcome={result:<7}  "
            f"Owner={owner_rank:<12}  "
            f"First external={external_rank:<12}  "
            f"{category}"
        )

    print()
    print("TIMING BY OUTCOME")

    for result in (
        "species",
        "genus",
        "none",
        "other",
    ):
        print()
        print(result)

        print(
            "  median hours to first external:",
            median(
                timing[result][
                    "first_external"
                ]
            )
        )

        print(
            "  median hours to second external:",
            median(
                timing[result][
                    "second_external"
                ]
            )
        )

        print(
            "  median first-to-last hours "
            "(2+ external IDs):",
            median(
                timing[result][
                    "first_to_last_multi"
                ]
            )
        )

        print(
            "  first external vision:",
            dict(
                first_external_vision[
                    result
                ]
            )
        )

        print(
            "  first external disagreement:",
            dict(
                first_external_disagreement[
                    result
                ]
            )
        )


if __name__ == "__main__":
    main()