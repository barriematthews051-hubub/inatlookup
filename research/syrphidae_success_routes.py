import csv
from collections import Counter, defaultdict


HISTORY_FILE = (
    "research/"
    "syrphidae_pilot_500_history.csv"
)

OBSERVATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_enriched.csv"
)

IDENTIFICATIONS_FILE = (
    "research/"
    "syrphidae_pilot_500_identifications_all.csv"
)


def load_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8"
    ) as f:
        return list(csv.DictReader(f))


def percent(part, total):
    if total == 0:
        return 0.0

    return round(
        100 * part / total,
        1
    )


def photo_group(count):
    count = int(count)

    if count == 0:
        return "0"
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    if count == 3:
        return "3"

    return "4+"


def hemisphere(latitude):
    if not latitude:
        return "unknown"

    value = float(latitude)

    if value > 0:
        return "north"

    if value < 0:
        return "south"

    return "equator"


def main():
    history_rows = load_csv(
        HISTORY_FILE
    )

    observations = {
        row["observation_id"]: row
        for row in load_csv(
            OBSERVATIONS_FILE
        )
    }

    identifications = load_csv(
        IDENTIFICATIONS_FILE
    )

    by_observation = defaultdict(list)

    for identification in identifications:
        by_observation[
            identification["observation_id"]
        ].append(identification)

    route_a = []
    route_b = []
    unconfirmed_initial_species = []

    for hist in history_rows:

        obs_id = hist["observation_id"]
        obs = observations[obs_id]

        ids = by_observation[obs_id]

        external_ids = [
            x
            for x in ids
            if x["own_observation"] != "True"
        ]

        first_owner_rank = (
            hist["first_owner_rank"]
        )

        outcome = hist["outcome_group"]

        if (
            first_owner_rank == "species"
            and outcome == "species"
            and external_ids
        ):
            route_a.append(
                (hist, obs)
            )

        elif (
            first_owner_rank != "species"
            and hist["first_species_by"] == "external"
            and outcome == "species"
        ):
            route_b.append(
                (hist, obs)
            )

        elif (
            first_owner_rank == "species"
            and outcome == "none"
            and not external_ids
        ):
            unconfirmed_initial_species.append(
                (hist, obs)
            )

    groups = [
        (
            "ROUTE A - owner starts species, external confirmation, species CT",
            route_a,
        ),
        (
            "ROUTE B - owner starts above species, external supplies species, species CT",
            route_b,
        ),
        (
            "UNCONFIRMED - owner starts species, no external ID, no CT",
            unconfirmed_initial_species,
        ),
    ]

    for label, group in groups:

        print()
        print(label)
        print("N:", len(group))

        photos = Counter(
            photo_group(
                obs["photo_count"]
            )
            for hist, obs in group
        )

        projects = sum(
            int(
                obs["project_count"]
            ) > 0
            for hist, obs in group
        )

        hemispheres = Counter(
            hemisphere(
                obs["latitude"]
            )
            for hist, obs in group
        )

        months = Counter(
            obs["sampling_month"]
            for hist, obs in group
        )

        owner_changed = sum(
            hist["owner_rank_changed"]
            == "True"
            for hist, obs in group
        )

        withdrawn = sum(
            int(
                hist["withdrawn_id_count"]
            ) > 0
            for hist, obs in group
        )

        historical_disagreement = sum(
            hist["historical_disagreement"]
            == "True"
            for hist, obs in group
        )

        historical_maverick = sum(
            hist["historical_maverick"]
            == "True"
            for hist, obs in group
        )

        taxa = Counter(
            obs["taxon_name"]
            for hist, obs in group
        )

        print(
            "Photo groups:",
            dict(
                sorted(
                    photos.items()
                )
            )
        )

        print(
            "Project:",
            projects,
            f"({percent(projects,len(group))}%)"
        )

        print(
            "Hemisphere:",
            dict(hemispheres)
        )

        print(
            "Months:",
            dict(
                sorted(
                    months.items()
                )
            )
        )

        print(
            "Owner rank changed:",
            owner_changed,
            f"({percent(owner_changed,len(group))}%)"
        )

        print(
            "Any withdrawn ID:",
            withdrawn,
            f"({percent(withdrawn,len(group))}%)"
        )

        print(
            "Historical disagreement:",
            historical_disagreement,
            f"({percent(historical_disagreement,len(group))}%)"
        )

        print(
            "Historical maverick:",
            historical_maverick,
            f"({percent(historical_maverick,len(group))}%)"
        )

        print(
            "Top taxa:"
        )

        for taxon_name, count in taxa.most_common(
            15
        ):
            print(
                f"  {count:3d}  "
                f"{taxon_name}"
            )


if __name__ == "__main__":
    main()