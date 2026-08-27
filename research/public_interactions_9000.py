import csv
import json
import os
import time

import requests

DATA_DIR = os.path.join("research", "data")
CACHE_DIR = os.path.join("research", "cache")

CACHE_FILE = os.path.join(
    CACHE_DIR,
    "public_interactions_9000.json",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "public_interactions_9000.csv",
)

BATCH_SIZE = 100
REQUEST_DELAY = 1.25


FAMILIES = [
    ("Syrphidae", "hoverflies", 49995),
    ("Asilidae", "robber flies", 47982),
    ("Geometridae", "geometer moths", 49530),
    ("Nymphalidae", "brush-footed butterflies", 47922),
    ("Staphylinidae", "rove beetles", 47951),
    ("Asteraceae", "daisy/sunflower family", 47604),
    ("Formicidae", "ants", 47336),
    ("Libellulidae", "skimmers and perchers", 47819),
    ("Orchidaceae", "orchid family", 47217),
    ("Poaceae", "grass family", 47434),
    ("Russulaceae", "russulas and milkcaps", 48340),
    ("Parmeliaceae", "shield lichens", 54321),
    ("Salticidae", "jumping spiders", 48139),
    ("Lycosidae", "wolf spiders", 47416),
    ("Anatidae", "ducks, geese and swans", 6912),
    ("Colubridae", "colubrid snakes", 26504),
    ("Limacidae", "keeled slugs", 62471),
    ("Asteriidae", "common sea stars", 47671),
]


def slugify(text):
    return (
        text.lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {
            "schema_version": 1,
            "records": {},
        }

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        cache = json.load(handle)

    if (
        not isinstance(cache, dict)
        or "records" not in cache
    ):
        raise ValueError(
            f"Unexpected cache format: "
            f"{CACHE_FILE}"
        )

    return cache


def save_cache(cache):
    os.makedirs(
        CACHE_DIR,
        exist_ok=True,
    )

    temp_file = CACHE_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            cache,
            handle,
            indent=2,
            sort_keys=True,
        )

    os.replace(
        temp_file,
        CACHE_FILE,
    )


def api_get(
    url,
    params=None,
    max_attempts=8,
    allow_404=False,
):
    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=90,
                headers={
                    "User-Agent":
                        "inatlookup-research-pilot"
                },
            )

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            if attempt == max_attempts:
                raise

            wait = min(
                60,
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"    Network error "
                f"({type(exc).__name__}); "
                f"retry in {wait}s"
            )

            time.sleep(wait)
            continue

        if (
            response.status_code == 404
            and allow_404
        ):
            time.sleep(
                REQUEST_DELAY
            )
            return None

        if response.status_code == 429:
            if attempt == max_attempts:
                response.raise_for_status()

            try:
                wait = float(
                    response.headers.get(
                        "Retry-After"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                wait = min(
                    60,
                    5 * (
                        2 ** (
                            attempt - 1
                        )
                    ),
                )

            print(
                f"    Rate limited; "
                f"retry in {wait:.0f}s"
            )

            time.sleep(wait)
            continue

        if response.status_code in {
            500,
            502,
            503,
            504,
        }:
            if attempt == max_attempts:
                response.raise_for_status()

            wait = min(
                60,
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"    Server error "
                f"{response.status_code}; "
                f"retry in {wait}s"
            )

            time.sleep(wait)
            continue

        response.raise_for_status()

        data = response.json()

        time.sleep(
            REQUEST_DELAY
        )

        return data

    raise RuntimeError(
        "API request failed after retries"
    )


def load_sample_ids(family):
    filename = os.path.join(
        DATA_DIR,
        f"{slugify(family)}"
        "_pilot_500_analysis.csv",
    )

    observation_ids = []

    with open(
        filename,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(
            handle
        )

        for row in reader:
            observation_ids.append(
                int(
                    row[
                        "observation_id"
                    ]
                )
            )

    observation_ids = sorted(
        set(observation_ids)
    )

    if len(observation_ids) != 500:
        raise ValueError(
            f"{family}: expected 500 "
            f"observations, found "
            f"{len(observation_ids)}"
        )

    return observation_ids


def user_id_from_item(item):
    if not isinstance(
        item,
        dict,
    ):
        return None

    value = item.get(
        "user_id"
    )

    if (
        value is None
        and isinstance(
            item.get("user"),
            dict,
        )
    ):
        value = (
            item["user"].get("id")
        )

    try:
        if value is None:
            return None

        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def user_ids_from_items(
    items,
    include_updater=False,
):
    result = set()

    for item in items or []:
        user_id = (
            user_id_from_item(
                item
            )
        )

        if user_id is not None:
            result.add(user_id)

        if (
            include_updater
            and isinstance(
                item,
                dict,
            )
        ):
            updater_id = item.get(
                "updater_id"
            )

            try:
                if updater_id is not None:
                    result.add(
                        int(updater_id)
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

    return result


def reviewed_user_ids(
    observation,
):
    result = set()

    for value in (
        observation.get(
            "reviewed_by",
            [],
        )
        or []
    ):
        try:
            result.add(
                int(value)
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

    return result


def analyse_observation(
    family,
    common_name,
    taxon_id,
    observation,
):
    observation_id = int(
        observation["id"]
    )

    owner = (
        observation.get("user")
        or {}
    )

    owner_id = owner.get("id")

    if owner_id is not None:
        owner_id = int(owner_id)

    owner_set = (
        {owner_id}
        if owner_id is not None
        else set()
    )

    external_identifiers_ever = set()
    external_identifiers_current = set()

    external_id_count = 0
    external_vision_id_count = 0

    for identification in (
        observation.get(
            "identifications",
            [],
        )
        or []
    ):
        user_id = (
            user_id_from_item(
                identification
            )
        )

        if (
            user_id is None
            or user_id == owner_id
        ):
            continue

        external_identifiers_ever.add(
            user_id
        )

        external_id_count += 1

        if (
            identification.get(
                "current"
            )
            is True
        ):
            external_identifiers_current.add(
                user_id
            )

        if (
            identification.get(
                "vision"
            )
            is True
        ):
            external_vision_id_count += 1

    reviewers = (
        reviewed_user_ids(
            observation
        )
        - owner_set
    )

    commenters = (
        user_ids_from_items(
            observation.get(
                "comments",
                [],
            )
        )
        - owner_set
    )

    annotators = (
        user_ids_from_items(
            observation.get(
                "annotations",
                [],
            )
        )
        - owner_set
    )

    dqa_users = (
        user_ids_from_items(
            observation.get(
                "quality_metrics",
                [],
            )
        )
        - owner_set
    )

    field_users = (
        user_ids_from_items(
            observation.get(
                "ofvs",
                [],
            ),
            include_updater=True,
        )
        - owner_set
    )

    fave_users = (
        user_ids_from_items(
            observation.get(
                "faves",
                [],
            )
        )
        - owner_set
    )

    reviewer_no_id = (
        reviewers
        - external_identifiers_ever
    )

    commenter_no_id = (
        commenters
        - external_identifiers_ever
    )

    annotator_no_id = (
        annotators
        - external_identifiers_ever
    )

    dqa_no_id = (
        dqa_users
        - external_identifiers_ever
    )

    field_no_id = (
        field_users
        - external_identifiers_ever
    )

    fave_no_id = (
        fave_users
        - external_identifiers_ever
    )

    strict_action_users = (
        commenters
        | annotators
        | dqa_users
        | field_users
    )

    strict_non_id_users = (
        strict_action_users
        - external_identifiers_ever
    )

    broad_action_users = (
        strict_action_users
        | fave_users
    )

    detectable_non_id_users = (
        reviewers
        | broad_action_users
    ) - external_identifiers_ever

    reviewed_only_users = (
        reviewers
        - external_identifiers_ever
        - commenters
        - annotators
        - dqa_users
        - field_users
        - fave_users
    )

    action_no_id_not_reviewed = (
        strict_non_id_users
        - reviewers
    )

    description = observation.get(
        "description"
    )

    photos = (
        observation.get(
            "photos",
            [],
        )
        or []
    )

    sounds = (
        observation.get(
            "sounds",
            [],
        )
        or []
    )

    tags = (
        observation.get(
            "tags",
            [],
        )
        or []
    )

    external_id_present = bool(
        external_identifiers_ever
    )

    detectable_reach = (
        external_id_present
        or bool(
            detectable_non_id_users
        )
    )

    return {
        "status":
            "ok",

        "family":
            family,

        "common_name":
            common_name,

        "taxon_id":
            taxon_id,

        "observation_id":
            observation_id,

        "created_at":
            observation.get(
                "created_at"
            ),

        "updated_at":
            observation.get(
                "updated_at"
            ),

        "owner_id":
            owner_id,

        "owner_vision":
            observation.get(
                "owners_identification_from_vision"
            ),

        "oauth_application_id":
            observation.get(
                "oauth_application_id"
            ),

        "description_present":
            bool(
                description
                and str(
                    description
                ).strip()
            ),

        "tag_count":
            len(tags),

        "photo_count":
            len(photos),

        "sound_count":
            len(sounds),

        "external_id_present":
            external_id_present,

        "external_id_count":
            external_id_count,

        "unique_external_identifiers_ever":
            len(
                external_identifiers_ever
            ),

        "unique_external_identifiers_current":
            len(
                external_identifiers_current
            ),

        "external_vision_id_count":
            external_vision_id_count,

        "reviewer_count":
            len(reviewers),

        "reviewer_no_id_count":
            len(
                reviewer_no_id
            ),

        "reviewed_only_count":
            len(
                reviewed_only_users
            ),

        "commenter_no_id_count":
            len(
                commenter_no_id
            ),

        "annotator_no_id_count":
            len(
                annotator_no_id
            ),

        "dqa_no_id_count":
            len(
                dqa_no_id
            ),

        "field_no_id_count":
            len(
                field_no_id
            ),

        "fave_no_id_count":
            len(
                fave_no_id
            ),

        "strict_non_id_action_count":
            len(
                strict_non_id_users
            ),

        "action_no_id_not_reviewed_count":
            len(
                action_no_id_not_reviewed
            ),

        "detectable_non_id_user_count":
            len(
                detectable_non_id_users
            ),

        "detectable_reach":
            detectable_reach,

        # These user-ID lists stay in the
        # compact JSON cache for later
        # targeted experience/rank work.

        "external_identifier_user_ids":
            sorted(
                external_identifiers_ever
            ),

        "reviewer_no_id_user_ids":
            sorted(
                reviewer_no_id
            ),

        "commenter_no_id_user_ids":
            sorted(
                commenter_no_id
            ),

        "annotator_no_id_user_ids":
            sorted(
                annotator_no_id
            ),

        "dqa_no_id_user_ids":
            sorted(
                dqa_no_id
            ),

        "field_no_id_user_ids":
            sorted(
                field_no_id
            ),

        "fave_no_id_user_ids":
            sorted(
                fave_no_id
            ),

        "strict_non_id_user_ids":
            sorted(
                strict_non_id_users
            ),

        "detectable_non_id_user_ids":
            sorted(
                detectable_non_id_users
            ),
    }


def unavailable_record(
    family,
    common_name,
    taxon_id,
    observation_id,
):
    return {
        "status":
            "unavailable",

        "family":
            family,

        "common_name":
            common_name,

        "taxon_id":
            taxon_id,

        "observation_id":
            observation_id,
    }


def fetch_batch(
    observation_ids,
):
    data = api_get(
        (
            "https://api.inaturalist.org/"
            "v1/observations"
        ),
        {
            "id":
                ",".join(
                    str(value)
                    for value
                    in observation_ids
                ),

            "per_page":
                len(
                    observation_ids
                ),
        },
    )

    return {
        int(
            observation["id"]
        ):
            observation

        for observation
        in data.get(
            "results",
            [],
        )
    }


def recover_one(
    observation_id,
):
    data = api_get(
        (
            "https://api.inaturalist.org/"
            f"v1/observations/"
            f"{observation_id}"
        ),
        allow_404=True,
    )

    if data is None:
        return None

    results = data.get(
        "results",
        [],
    )

    if len(results) != 1:
        return None

    return results[0]


def chunks(
    values,
    size,
):
    for start in range(
        0,
        len(values),
        size,
    ):
        yield values[
            start:
            start + size
        ]


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


def print_summary(
    family,
    common_name,
    rows,
):
    available = [
        row
        for row in rows
        if row.get(
            "status"
        ) == "ok"
    ]

    n = len(available)

    print()
    print(
        f"{family} "
        f"({common_name})"
    )

    print(
        "-" * (
            len(family)
            + len(common_name)
            + 3
        )
    )

    print(
        f"  Available: "
        f"{n}/{len(rows)}"
    )

    unavailable = (
        len(rows)
        - n
    )

    if unavailable:
        print(
            f"  Unavailable: "
            f"{unavailable}"
        )

    if not n:
        return

    external = sum(
        bool(
            row[
                "external_id_present"
            ]
        )
        for row in available
    )

    no_external_rows = [
        row
        for row in available
        if not row[
            "external_id_present"
        ]
    ]

    no_external = len(
        no_external_rows
    )

    no_external_reviewed = sum(
        row[
            "reviewer_no_id_count"
        ] > 0

        for row
        in no_external_rows
    )

    no_external_detectable = sum(
        row[
            "detectable_non_id_user_count"
        ] > 0

        for row
        in no_external_rows
    )

    reach = sum(
        bool(
            row[
                "detectable_reach"
            ]
        )
        for row in available
    )

    strict_non_id = sum(
        row[
            "strict_non_id_action_count"
        ] > 0

        for row in available
    )

    owner_vision_known = [
        row[
            "owner_vision"
        ]
        for row in available
        if row[
            "owner_vision"
        ] is not None
    ]

    owner_vision_yes = sum(
        value is True
        for value
        in owner_vision_known
    )

    external_cv = sum(
        row[
            "external_vision_id_count"
        ] > 0

        for row in available
    )

    print(
        f"  External ID: "
        f"{external}/{n} "
        f"({percent(external, n):.1f}%)"
    )

    print(
        f"  Detectable reach: "
        f"{reach}/{n} "
        f"({percent(reach, n):.1f}%)"
    )

    if reach:
        print(
            "  ID conversion among "
            "detectably reached: "
            f"{external}/{reach} "
            f"({percent(external, reach):.1f}%)"
        )

    print(
        f"  No external ID: "
        f"{no_external}/{n}"
    )

    if no_external:
        print(
            "    Reviewer-no-ID: "
            f"{no_external_reviewed}/"
            f"{no_external} "
            f"({percent(
                no_external_reviewed,
                no_external
            ):.1f}%)"
        )

        print(
            "    Any detectable "
            "non-ID interaction: "
            f"{no_external_detectable}/"
            f"{no_external} "
            f"({percent(
                no_external_detectable,
                no_external
            ):.1f}%)"
        )

        unknown = (
            no_external
            - no_external_detectable
        )

        print(
            "    No detectable external "
            "interaction: "
            f"{unknown}/"
            f"{no_external} "
            f"({percent(
                unknown,
                no_external
            ):.1f}%)"
        )

    print(
        f"  Strict non-ID action: "
        f"{strict_non_id}/{n} "
        f"({percent(
            strict_non_id,
            n
        ):.1f}%)"
    )

    print(
        f"  Owner CV flag yes: "
        f"{owner_vision_yes}/"
        f"{len(owner_vision_known)}"
    )

    print(
        f"  Any external CV ID: "
        f"{external_cv}/{n} "
        f"({percent(
            external_cv,
            n
        ):.1f}%)"
    )


def write_csv(
    ordered_ids,
    records,
):
    fields = [
        "status",
        "family",
        "common_name",
        "taxon_id",
        "observation_id",
        "created_at",
        "updated_at",
        "owner_id",
        "owner_vision",
        "oauth_application_id",
        "description_present",
        "tag_count",
        "photo_count",
        "sound_count",
        "external_id_present",
        "external_id_count",
        "unique_external_identifiers_ever",
        "unique_external_identifiers_current",
        "external_vision_id_count",
        "reviewer_count",
        "reviewer_no_id_count",
        "reviewed_only_count",
        "commenter_no_id_count",
        "annotator_no_id_count",
        "dqa_no_id_count",
        "field_no_id_count",
        "fave_no_id_count",
        "strict_non_id_action_count",
        "action_no_id_not_reviewed_count",
        "detectable_non_id_user_count",
        "detectable_reach",
    ]

    os.makedirs(
        DATA_DIR,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()

        for observation_id in ordered_ids:
            record = records[
                str(
                    observation_id
                )
            ]

            writer.writerow(
                {
                    field:
                        record.get(
                            field,
                            "",
                        )

                    for field
                    in fields
                }
            )


def main():
    cache = load_cache()
    records = cache[
        "records"
    ]

    family_samples = {}
    ordered_ids = []
    seen = set()

    for (
        family,
        common_name,
        taxon_id,
    ) in FAMILIES:
        observation_ids = (
            load_sample_ids(
                family
            )
        )

        for observation_id in (
            observation_ids
        ):
            if observation_id in seen:
                raise ValueError(
                    "Duplicate observation "
                    "across family samples: "
                    f"{observation_id}"
                )

            seen.add(
                observation_id
            )

            ordered_ids.append(
                observation_id
            )

        family_samples[
            family
        ] = observation_ids

    print()
    print(
        "PUBLIC INTERACTION COLLECTOR"
    )
    print(
        "============================"
    )
    print()

    print(
        f"Families: "
        f"{len(FAMILIES)}"
    )

    print(
        f"Frozen observations: "
        f"{len(ordered_ids)}"
    )

    print(
        f"Batch size: "
        f"{BATCH_SIZE}"
    )

    print(
        "Already cached: "
        f"{sum(
            str(value) in records
            for value
            in ordered_ids
        )}"
    )

    for (
        family,
        common_name,
        taxon_id,
    ) in FAMILIES:

        observation_ids = (
            family_samples[
                family
            ]
        )

        missing = [
            observation_id

            for observation_id
            in observation_ids

            if str(
                observation_id
            ) not in records
        ]

        print()
        print(
            f"{family} "
            f"({common_name})"
        )

        print(
            f"  Cached: "
            f"{len(observation_ids) - len(missing)}"
            f"/500"
        )

        if not missing:
            continue

        batches = list(
            chunks(
                missing,
                BATCH_SIZE,
            )
        )

        for (
            batch_number,
            batch_ids,
        ) in enumerate(
            batches,
            start=1,
        ):
            print(
                f"  Batch "
                f"{batch_number}/"
                f"{len(batches)}: "
                f"{len(batch_ids)} "
                f"observations"
            )

            batch_results = (
                fetch_batch(
                    batch_ids
                )
            )

            missing_from_batch = [
                observation_id

                for observation_id
                in batch_ids

                if observation_id
                not in batch_results
            ]

            if missing_from_batch:
                print(
                    "    Missing from batch: "
                    f"{len(
                        missing_from_batch
                    )}"
                )

            for observation_id in (
                batch_ids
            ):
                observation = (
                    batch_results.get(
                        observation_id
                    )
                )

                if observation is None:
                    print(
                        f"    Recovering "
                        f"{observation_id} "
                        f"individually..."
                    )

                    observation = (
                        recover_one(
                            observation_id
                        )
                    )

                if observation is None:
                    print(
                        f"    Unavailable: "
                        f"{observation_id}"
                    )

                    records[
                        str(
                            observation_id
                        )
                    ] = unavailable_record(
                        family,
                        common_name,
                        taxon_id,
                        observation_id,
                    )

                else:
                    records[
                        str(
                            observation_id
                        )
                    ] = analyse_observation(
                        family,
                        common_name,
                        taxon_id,
                        observation,
                    )

            save_cache(
                cache
            )

    write_csv(
        ordered_ids,
        records,
    )

    print()
    print(
        "FAMILY SUMMARY"
    )
    print(
        "=============="
    )

    all_rows = []

    for (
        family,
        common_name,
        taxon_id,
    ) in FAMILIES:

        rows = [
            records[
                str(
                    observation_id
                )
            ]

            for observation_id
            in family_samples[
                family
            ]
        ]

        all_rows.extend(
            rows
        )

        print_summary(
            family,
            common_name,
            rows,
        )

    print_summary(
        "ALL",
        "18 families",
        all_rows,
    )

    print()
    print(
        f"Output: "
        f"{OUTPUT_FILE}"
    )

    print(
        f"Compact cache: "
        f"{CACHE_FILE}"
    )


if __name__ == "__main__":
    main()