import csv
from collections import Counter, defaultdict


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


def hemisphere(latitude):
    if latitude == "":
        return "unknown"

    value = float(latitude)

    if value > 0:
        return "north"

    if value < 0:
        return "south"

    return "equator"


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


def percent(part, total):
    if total == 0:
        return 0.0

    return round(
        100 * part / total,
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

    confirmed = []
    unconfirmed = []

    for obs in observations:

        obs_id = obs["observation_id"]

        ids = [
            x
            for x in by_observation[obs_id]
            if x["current"] == "True"
        ]

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

        if not owner_ids:
            continue

        owner_rank = owner_ids[0]["taxon_rank"]

        if owner_rank != "species":
            continue

        community_rank = (
            obs["community_taxon_rank"]
        )

        if (
            community_rank == "species"
            and len(external_ids) >= 1
        ):
            confirmed.append(obs)

        elif (
            not community_rank
            and len(external_ids) == 0
        ):
            unconfirmed.append(obs)

    print(
        "Confirmed species:",
        len(confirmed)
    )

    print(
        "Unconfirmed species:",
        len(unconfirmed)
    )

    print()

    for label, rows in (
        ("CONFIRMED", confirmed),
        ("UNCONFIRMED", unconfirmed),
    ):

        print(label)

        photos = Counter(
            photo_group(
                row["photo_count"]
            )
            for row in rows
        )

        projects = sum(
            int(
                row["project_count"]
            ) > 0
            for row in rows
        )

        hemispheres = Counter(
            hemisphere(
                row["latitude"]
            )
            for row in rows
        )

        months = Counter(
            row["sampling_month"]
            for row in rows
        )

        taxa = Counter(
            (
                row["taxon_name"],
                row["taxon_rank"]
            )
            for row in rows
        )

        print(
            "  Photo groups:",
            dict(
                sorted(
                    photos.items()
                )
            )
        )

        print(
            "  Project:",
            projects,
            f"({percent(projects,len(rows))}%)"
        )

        print(
            "  Hemisphere:",
            dict(hemispheres)
        )

        print(
            "  Months:",
            dict(
                sorted(
                    months.items()
                )
            )
        )

        print(
            "  Top current taxa:"
        )

        for (
            taxon_name,
            taxon_rank
        ), count in taxa.most_common(15):

            print(
                f"    {count:3d}  "
                f"{taxon_name} "
                f"({taxon_rank})"
            )

        print()

    print("PHOTO GROUP SUCCESS RATE")

    all_species_owner = (
        confirmed + unconfirmed
    )

    by_photo = defaultdict(
        lambda: {
            "confirmed": 0,
            "unconfirmed": 0,
        }
    )

    for row in confirmed:
        by_photo[
            photo_group(
                row["photo_count"]
            )
        ]["confirmed"] += 1

    for row in unconfirmed:
        by_photo[
            photo_group(
                row["photo_count"]
            )
        ]["unconfirmed"] += 1

    for group in (
        "1",
        "2",
        "3",
        "4+",
        "0",
    ):
        counts = by_photo[group]

        total = (
            counts["confirmed"]
            + counts["unconfirmed"]
        )

        if total == 0:
            continue

        print(
            f"  Photos {group}: "
            f"{counts['confirmed']}/"
            f"{total} confirmed "
            f"({percent(counts['confirmed'],total)}%)"
        )


if __name__ == "__main__":
    main()