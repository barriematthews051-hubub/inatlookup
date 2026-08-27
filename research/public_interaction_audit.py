import csv
import json
import os
import random
import statistics
import time

import requests


DATA_DIR = os.path.join(
    "research",
    "data",
)

CACHE_DIR = os.path.join(
    "research",
    "cache",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "public_interaction_audit.csv",
)

CACHE_FILE = os.path.join(
    CACHE_DIR,
    "public_interaction_audit.json",
)

SAMPLE_PER_FAMILY = 25
SEED = 20260827

REQUEST_DELAY = 1.25


FAMILIES = [
    {
        "family": "Asteriidae",
        "common_name": "common sea stars",
        "taxon_id": 47671,
    },
    {
        "family": "Salticidae",
        "common_name": "jumping spiders",
        "taxon_id": 48139,
    },
    {
        "family": "Russulaceae",
        "common_name": "russulas and milkcaps",
        "taxon_id": 48340,
    },
    {
        "family": "Anatidae",
        "common_name": "ducks, geese and swans",
        "taxon_id": 6912,
    },
]


AUDIT_KEYS = [
    "reviewed_by",
    "comments",
    "annotations",
    "quality_metrics",
    "ofvs",
    "faves",
    "identifications",
    "owners_identification_from_vision",
    "oauth_application_id",
    "description",
    "tags",
    "sounds",
]


def slugify(text):
    return (
        text.lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def save_cache(cache):
    os.makedirs(
        CACHE_DIR,
        exist_ok=True,
    )

    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            cache,
            handle,
            indent=2,
            sort_keys=True,
        )


def api_get(
    url,
    max_attempts=8,
):
    for attempt in range(
        1,
        max_attempts + 1,
    ):
        try:
            response = requests.get(
                url,
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

            wait_seconds = min(
                60,
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"    Network error "
                f"({type(exc).__name__}). "
                f"Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        if response.status_code == 429:
            if attempt == max_attempts:
                response.raise_for_status()

            retry_after = (
                response.headers.get(
                    "Retry-After"
                )
            )

            try:
                wait_seconds = float(
                    retry_after
                )
            except (
                TypeError,
                ValueError,
            ):
                wait_seconds = min(
                    60,
                    5 * (2 ** (attempt - 1)),
                )

            print(
                f"    Rate limited. "
                f"Retrying in "
                f"{wait_seconds:.0f} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        if response.status_code in {
            500,
            502,
            503,
            504,
        }:
            if attempt == max_attempts:
                response.raise_for_status()

            wait_seconds = min(
                60,
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"    Server error "
                f"{response.status_code}. "
                f"Retrying in "
                f"{wait_seconds} seconds..."
            )

            time.sleep(wait_seconds)
            continue

        response.raise_for_status()

        data = response.json()

        time.sleep(REQUEST_DELAY)

        return data

    raise RuntimeError(
        "API request failed after retries"
    )


def load_sample_ids(
    family,
    taxon_id,
):
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
        reader = csv.DictReader(handle)

        for row in reader:
            observation_ids.append(
                int(row["observation_id"])
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

    rng = random.Random(
        SEED + taxon_id
    )

    selected = rng.sample(
        observation_ids,
        SAMPLE_PER_FAMILY,
    )

    return sorted(selected)


def get_observation(
    observation_id,
    cache,
):
    key = str(observation_id)

    if key in cache:
        return (
            cache[key],
            "cache",
        )

    data = api_get(
        (
            "https://api.inaturalist.org/"
            f"v1/observations/{observation_id}"
        )
    )

    results = data.get(
        "results",
        [],
    )

    if len(results) != 1:
        raise ValueError(
            f"Observation {observation_id}: "
            f"expected one result, "
            f"found {len(results)}"
        )

    observation = results[0]

    cache[key] = observation
    save_cache(cache)

    return (
        observation,
        "API",
    )


def user_id_from_item(item):
    if not isinstance(item, dict):
        return None

    user_id = item.get("user_id")

    if user_id is not None:
        try:
            return int(user_id)
        except (
            TypeError,
            ValueError,
        ):
            pass

    user = item.get("user")

    if isinstance(user, dict):
        user_id = user.get("id")

        if user_id is not None:
            try:
                return int(user_id)
            except (
                TypeError,
                ValueError,
            ):
                pass

    return None


def user_ids_from_items(
    items,
    include_updater=False,
):
    user_ids = set()

    for item in items or []:
        user_id = user_id_from_item(
            item
        )

        if user_id is not None:
            user_ids.add(user_id)

        if (
            include_updater
            and isinstance(item, dict)
        ):
            updater_id = item.get(
                "updater_id"
            )

            if updater_id is not None:
                try:
                    user_ids.add(
                        int(updater_id)
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    pass

    return user_ids


def reviewed_user_ids(observation):
    values = observation.get(
        "reviewed_by",
        [],
    )

    result = set()

    for value in values or []:
        try:
            result.add(int(value))
        except (
            TypeError,
            ValueError,
        ):
            pass

    return result


def analyse_observation(
    family,
    common_name,
    observation,
):
    observation_id = int(
        observation["id"]
    )

    owner = observation.get(
        "user",
        {},
    )

    owner_id = owner.get("id")

    if owner_id is not None:
        owner_id = int(owner_id)

    owner_set = (
        {owner_id}
        if owner_id is not None
        else set()
    )

    identifications = observation.get(
        "identifications",
        [],
    ) or []

    external_identifiers_ever = set()
    external_identifiers_current = set()

    external_id_count = 0
    external_vision_id_count = 0

    for identification in identifications:
        user_id = user_id_from_item(
            identification
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

        if identification.get(
            "current"
        ) is True:
            external_identifiers_current.add(
                user_id
            )

        if identification.get(
            "vision"
        ) is True:
            external_vision_id_count += 1

    reviewers = (
        reviewed_user_ids(observation)
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

    photos = observation.get(
        "photos",
        [],
    ) or []

    sounds = observation.get(
        "sounds",
        [],
    ) or []

    tags = observation.get(
        "tags",
        [],
    ) or []

    description = observation.get(
        "description"
    )

    return {
        "family": family,
        "common_name": common_name,
        "observation_id":
            observation_id,
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
                and str(description).strip()
            ),
        "tag_count":
            len(tags),
        "photo_count":
            len(photos),
        "sound_count":
            len(sounds),
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
            len(reviewer_no_id),
        "reviewed_only_count":
            len(reviewed_only_users),
        "commenter_count":
            len(commenters),
        "commenter_no_id_count":
            len(commenter_no_id),
        "annotator_count":
            len(annotators),
        "annotator_no_id_count":
            len(annotator_no_id),
        "dqa_user_count":
            len(dqa_users),
        "dqa_no_id_count":
            len(dqa_no_id),
        "field_user_count":
            len(field_users),
        "field_no_id_count":
            len(field_no_id),
        "fave_user_count":
            len(fave_users),
        "fave_no_id_count":
            len(fave_no_id),
        "strict_non_id_action_count":
            len(strict_non_id_users),
        "action_no_id_not_reviewed_count":
            len(action_no_id_not_reviewed),
        "detectable_non_id_user_count":
            len(detectable_non_id_users),
    }


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


def print_field_availability(
    observations,
):
    print()
    print(
        "PUBLIC FIELD AVAILABILITY"
    )
    print(
        "========================="
    )
    print()

    for key in AUDIT_KEYS:
        present = sum(
            1
            for observation
            in observations
            if key in observation
        )

        print(
            f"{key:38}"
            f"{present:3}/{len(observations)} "
            f"({percent(present, len(observations)):5.1f}%)"
        )


def print_family_summary(rows):
    print()
    print(
        "PUBLIC INTERACTION AUDIT SUMMARY"
    )
    print(
        "================================"
    )

    for family_row in FAMILIES:
        family = family_row["family"]
        common_name = (
            family_row["common_name"]
        )

        subset = [
            row
            for row in rows
            if row["family"] == family
        ]

        n = len(subset)

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

        owner_vision_known = [
            row["owner_vision"]
            for row in subset
            if row["owner_vision"]
            is not None
        ]

        owner_vision_yes = sum(
            value is True
            for value
            in owner_vision_known
        )

        ext_vision_obs = sum(
            row[
                "external_vision_id_count"
            ] > 0
            for row in subset
        )

        reviewer_no_id_obs = sum(
            row[
                "reviewer_no_id_count"
            ] > 0
            for row in subset
        )

        reviewed_only_obs = sum(
            row[
                "reviewed_only_count"
            ] > 0
            for row in subset
        )

        comment_no_id_obs = sum(
            row[
                "commenter_no_id_count"
            ] > 0
            for row in subset
        )

        annotation_no_id_obs = sum(
            row[
                "annotator_no_id_count"
            ] > 0
            for row in subset
        )

        dqa_no_id_obs = sum(
            row[
                "dqa_no_id_count"
            ] > 0
            for row in subset
        )

        field_no_id_obs = sum(
            row[
                "field_no_id_count"
            ] > 0
            for row in subset
        )

        strict_non_id_obs = sum(
            row[
                "strict_non_id_action_count"
            ] > 0
            for row in subset
        )

        no_id_not_reviewed_obs = sum(
            row[
                "action_no_id_not_reviewed_count"
            ] > 0
            for row in subset
        )

        detectable_non_id_obs = sum(
            row[
                "detectable_non_id_user_count"
            ] > 0
            for row in subset
        )

        description_obs = sum(
            row[
                "description_present"
            ]
            for row in subset
        )

        reviewer_no_id_pairs = sum(
            row[
                "reviewer_no_id_count"
            ]
            for row in subset
        )

        strict_non_id_pairs = sum(
            row[
                "strict_non_id_action_count"
            ]
            for row in subset
        )

        detectable_non_id_pairs = sum(
            row[
                "detectable_non_id_user_count"
            ]
            for row in subset
        )

        reviewer_counts = [
            row["reviewer_count"]
            for row in subset
        ]

        print(
            f"  Owner CV flag yes: "
            f"{owner_vision_yes}/"
            f"{len(owner_vision_known)}"
        )

        print(
            f"  Any external CV ID: "
            f"{ext_vision_obs}/{n}"
        )

        print(
            f"  Description present: "
            f"{description_obs}/{n}"
        )

        print(
            f"  Reviewer-no-ID obs: "
            f"{reviewer_no_id_obs}/{n} "
            f"(user-observation pairs "
            f"{reviewer_no_id_pairs})"
        )

        print(
            f"  Reviewed-only obs: "
            f"{reviewed_only_obs}/{n}"
        )

        print(
            f"  Comment-no-ID obs: "
            f"{comment_no_id_obs}/{n}"
        )

        print(
            f"  Annotation-no-ID obs: "
            f"{annotation_no_id_obs}/{n}"
        )

        print(
            f"  DQA-no-ID obs: "
            f"{dqa_no_id_obs}/{n}"
        )

        print(
            f"  Field-value-no-ID obs: "
            f"{field_no_id_obs}/{n}"
        )

        print(
            f"  Strict non-ID action obs: "
            f"{strict_non_id_obs}/{n} "
            f"(pairs "
            f"{strict_non_id_pairs})"
        )

        print(
            f"  Non-ID action but "
            f"not reviewed: "
            f"{no_id_not_reviewed_obs}/{n}"
        )

        print(
            f"  Any detectable non-ID "
            f"interaction: "
            f"{detectable_non_id_obs}/{n} "
            f"(pairs "
            f"{detectable_non_id_pairs})"
        )

        print(
            f"  Median external reviewers: "
            f"{statistics.median(reviewer_counts):.1f}"
        )


def print_source_apps(rows):
    print()
    print(
        "OAUTH APPLICATION IDS"
    )
    print(
        "====================="
    )
    print()

    counts = {}

    for row in rows:
        app_id = row[
            "oauth_application_id"
        ]

        key = (
            str(app_id)
            if app_id is not None
            else "None"
        )

        counts[key] = (
            counts.get(key, 0)
            + 1
        )

    for key, count in sorted(
        counts.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    ):
        print(
            f"{key:12} {count:3}"
        )


def main():
    cache = load_cache()

    all_observations = []
    output_rows = []

    print()
    print(
        "PUBLIC INTERACTION-FIELD AUDIT"
    )
    print(
        "=============================="
    )
    print()
    print(
        f"Families: {len(FAMILIES)}"
    )
    print(
        f"Observations per family: "
        f"{SAMPLE_PER_FAMILY}"
    )
    print(
        f"Total observations: "
        f"{len(FAMILIES) * SAMPLE_PER_FAMILY}"
    )
    print(
        f"Fixed seed: {SEED}"
    )

    for family_row in FAMILIES:
        family = family_row["family"]
        common_name = (
            family_row["common_name"]
        )
        taxon_id = (
            family_row["taxon_id"]
        )

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

        sample_ids = load_sample_ids(
            family,
            taxon_id,
        )

        for index, observation_id in enumerate(
            sample_ids,
            start=1,
        ):
            (
                observation,
                source,
            ) = get_observation(
                observation_id,
                cache,
            )

            all_observations.append(
                observation
            )

            output_rows.append(
                analyse_observation(
                    family,
                    common_name,
                    observation,
                )
            )

            print(
                f"  {index:2}/{SAMPLE_PER_FAMILY} "
                f"obs {observation_id} "
                f"{source}"
            )

    fields = [
        "family",
        "common_name",
        "observation_id",
        "owner_id",
        "owner_vision",
        "oauth_application_id",
        "description_present",
        "tag_count",
        "photo_count",
        "sound_count",
        "external_id_count",
        "unique_external_identifiers_ever",
        "unique_external_identifiers_current",
        "external_vision_id_count",
        "reviewer_count",
        "reviewer_no_id_count",
        "reviewed_only_count",
        "commenter_count",
        "commenter_no_id_count",
        "annotator_count",
        "annotator_no_id_count",
        "dqa_user_count",
        "dqa_no_id_count",
        "field_user_count",
        "field_no_id_count",
        "fave_user_count",
        "fave_no_id_count",
        "strict_non_id_action_count",
        "action_no_id_not_reviewed_count",
        "detectable_non_id_user_count",
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
        )

        writer.writeheader()

        for row in output_rows:
            writer.writerow(row)

    print_field_availability(
        all_observations
    )

    print_family_summary(
        output_rows
    )

    print_source_apps(
        output_rows
    )

    print()
    print(
        f"Output: {OUTPUT_FILE}"
    )
    print(
        f"Cache: {CACHE_FILE}"
    )


if __name__ == "__main__":
    main()