from collections import Counter, defaultdict


def percent(n, total):
    if total == 0:
        return 0.0

    return 100 * n / total


def calculate_identifier_concentration(rows):
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

    ranked = (
        by_identifier.most_common()
    )

    total_external = len(
        external
    )

    unique_identifiers = len(
        by_identifier
    )

    externally_attended = {
        row["observation_id"]
        for row in external
    }

    result = {
        "historical_external_ids":
            total_external,

        "unique_external_identifiers":
            unique_identifiers,

        "mean_external_ids_per_identifier":
            (
                total_external
                / unique_identifiers
                if unique_identifiers
                else 0.0
            ),
    }

    for top_n in (
        1,
        5,
        10,
        20,
    ):
        id_count = sum(
            count
            for _, count
            in ranked[:top_n]
        )

        result[
            f"top_{top_n}_id_share"
        ] = percent(
            id_count,
            total_external,
        )

        covered = set()

        for identifier, _ in ranked[
            :top_n
        ]:
            covered.update(
                observations_by_identifier[
                    identifier
                ]
            )

        result[
            f"top_{top_n}_observation_coverage"
        ] = percent(
            len(covered),
            len(externally_attended),
        )

    result[
        "ranked_identifiers"
    ] = ranked

    result[
        "observations_by_identifier"
    ] = observations_by_identifier

    result[
        "ranks_by_identifier"
    ] = ranks_by_identifier

    result[
        "externally_attended_observations"
    ] = externally_attended

    return result