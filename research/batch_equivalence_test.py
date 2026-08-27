import csv
import json
import os
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

AUDIT_FILE = os.path.join(
    DATA_DIR,
    "public_interaction_audit.csv",
)

SINGLE_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "public_interaction_audit.json",
)

BATCH_CACHE_FILE = os.path.join(
    CACHE_DIR,
    "batch_equivalence_test.json",
)

TEST_SIZE = 100
REQUEST_DELAY = 1.25

FAMILIES = [
    "Asteriidae",
    "Salticidae",
    "Russulaceae",
    "Anatidae",
]


FIELDS = [
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
    "photos",
]


def load_json(filename):
    with open(
        filename,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def save_json(
    filename,
    data,
):
    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True,
    )

    with open(
        filename,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            data,
            handle,
            indent=2,
            sort_keys=True,
        )


def api_get(
    url,
    params,
    max_attempts=8,
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

            wait_seconds = min(
                60,
                5 * (2 ** (attempt - 1)),
            )

            print(
                f"Network error "
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
                f"Rate limited. "
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
                f"Server error "
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


def load_family_lookup():
    result = {}

    with open(
        AUDIT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            result[
                int(row["observation_id"])
            ] = row["family"]

    return result


def as_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def nested_user_id(item):
    if not isinstance(item, dict):
        return None

    user_id = item.get(
        "user_id"
    )

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


def nested_taxon_id(item):
    if not isinstance(item, dict):
        return None

    taxon_id = item.get(
        "taxon_id"
    )

    if taxon_id is not None:
        try:
            return int(taxon_id)
        except (
            TypeError,
            ValueError,
        ):
            pass

    taxon = item.get("taxon")

    if isinstance(taxon, dict):
        taxon_id = taxon.get("id")

        if taxon_id is not None:
            try:
                return int(taxon_id)
            except (
                TypeError,
                ValueError,
            ):
                pass

    return None


def item_id(item):
    if not isinstance(item, dict):
        return None

    value = item.get("id")

    if value is None:
        return None

    try:
        return int(value)
    except (
        TypeError,
        ValueError,
    ):
        return value


def reviewed_signature(
    observation,
):
    values = []

    for value in as_list(
        observation.get(
            "reviewed_by"
        )
    ):
        try:
            values.append(int(value))
        except (
            TypeError,
            ValueError,
        ):
            values.append(str(value))

    return sorted(
        values,
        key=str,
    )


def identification_signature(
    observation,
):
    result = []

    for item in as_list(
        observation.get(
            "identifications"
        )
    ):
        result.append(
            (
                item_id(item),
                nested_user_id(item),
                nested_taxon_id(item),
                item.get("current"),
                item.get("vision"),
                item.get("category"),
            )
        )

    return sorted(
        result,
        key=lambda value:
            str(value),
    )


def comment_signature(
    observation,
):
    result = []

    for item in as_list(
        observation.get(
            "comments"
        )
    ):
        result.append(
            (
                item_id(item),
                nested_user_id(item),
                item.get("created_at"),
            )
        )

    return sorted(
        result,
        key=lambda value:
            str(value),
    )


def annotation_signature(
    observation,
):
    result = []

    for item in as_list(
        observation.get(
            "annotations"
        )
    ):
        result.append(
            (
                item_id(item),
                nested_user_id(item),
                item.get(
                    "controlled_attribute_id"
                ),
                item.get(
                    "controlled_value_id"
                ),
            )
        )

    return sorted(
        result,
        key=lambda value:
            str(value),
    )


def quality_metric_signature(
    observation,
):
    result = []

    for item in as_list(
        observation.get(
            "quality_metrics"
        )
    ):
        result.append(
            (
                item_id(item),
                nested_user_id(item),
                item.get("metric"),
                item.get("agree"),
            )
        )

    return sorted(
        result,
        key=lambda value:
            str(value),
    )



def ofv_signature(
    observation,
):
    result = []

    for item in as_list(
        observation.get("ofvs")
    ):
        updater_id = item.get(
            "updater_id"
        )

        if updater_id is not None:
            try:
                updater_id = int(
                    updater_id
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        result.append(
            (
                item_id(item),
                nested_user_id(item),
                updater_id,
            )
        )

    return sorted(
        result,
        key=lambda value:
            str(value),
    )




def fave_signature(
    observation,
):
    result = []

    for item in as_list(
        observation.get("faves")
    ):
        result.append(
            (
                nested_user_id(item),
                item.get("created_at"),
            )
        )

    return sorted(
        result,
        key=lambda value:
            str(value),
    )


def media_signature(
    observation,
    field,
):
    result = []

    for item in as_list(
        observation.get(field)
    ):
        if isinstance(item, dict):
            result.append(
                item.get("id")
            )
        else:
            result.append(item)

    return sorted(
        result,
        key=lambda value:
            str(value),
    )


def tag_signature(
    observation,
):
    values = as_list(
        observation.get("tags")
    )

    return sorted(
        [
            json.dumps(
                value,
                sort_keys=True,
            )
            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            )
            else str(value)
            for value in values
        ]
    )


def research_signature(
    observation,
):
    return {
        "reviewed_by":
            reviewed_signature(
                observation
            ),

        "identifications":
            identification_signature(
                observation
            ),

        "comments":
            comment_signature(
                observation
            ),

        "annotations":
            annotation_signature(
                observation
            ),

        "quality_metrics":
            quality_metric_signature(
                observation
            ),

        "ofvs":
            ofv_signature(
                observation
            ),

        "faves":
            fave_signature(
                observation
            ),

        "owners_identification_from_vision":
            observation.get(
                "owners_identification_from_vision"
            ),

        "oauth_application_id":
            observation.get(
                "oauth_application_id"
            ),

        "description":
            observation.get(
                "description"
            ),

        "tags":
            tag_signature(
                observation
            ),

        "sounds":
            media_signature(
                observation,
                "sounds",
            ),

        "photos":
            media_signature(
                observation,
                "photos",
            ),
    }


def feature_set(
    observation,
):
    features = set()

    if reviewed_signature(
        observation
    ):
        features.add(
            "reviewed_by"
        )

    if comment_signature(
        observation
    ):
        features.add(
            "comments"
        )

    if annotation_signature(
        observation
    ):
        features.add(
            "annotations"
        )

    if quality_metric_signature(
        observation
    ):
        features.add(
            "quality_metrics"
        )

    if ofv_signature(
        observation
    ):
        features.add(
            "ofvs"
        )

    if fave_signature(
        observation
    ):
        features.add(
            "faves"
        )

    if identification_signature(
        observation
    ):
        features.add(
            "identifications"
        )

    if observation.get(
        "owners_identification_from_vision"
    ) is True:
        features.add(
            "owner_vision"
        )

    if observation.get(
        "oauth_application_id"
    ) is not None:
        features.add(
            "oauth_application_id"
        )

    description = observation.get(
        "description"
    )

    if (
        description
        and str(description).strip()
    ):
        features.add(
            "description"
        )

    if tag_signature(
        observation
    ):
        features.add(
            "tags"
        )

    if media_signature(
        observation,
        "sounds",
    ):
        features.add(
            "sounds"
        )

    for identification in as_list(
        observation.get(
            "identifications"
        )
    ):
        if identification.get(
            "vision"
        ) is True:
            features.add(
                "external_vision"
            )
            break

    return features


def select_test_observations(
    single_cache,
    family_lookup,
):
    candidates = []

    for key, observation in (
        single_cache.items()
    ):
        observation_id = int(key)

        family = family_lookup.get(
            observation_id
        )

        if family not in FAMILIES:
            continue

        candidates.append(
            {
                "id":
                    observation_id,
                "family":
                    family,
                "features":
                    feature_set(
                        observation
                    ),
            }
        )

    selected = []
    selected_ids = set()
    represented_families = set()
    covered_features = set()

    # First ensure every family is represented.
    for family in FAMILIES:
        family_candidates = [
            item
            for item in candidates
            if item["family"] == family
        ]

        family_candidates.sort(
            key=lambda item:
                (
                    -len(
                        item["features"]
                    ),
                    item["id"],
                )
        )

        if not family_candidates:
            raise ValueError(
                f"No cached observations "
                f"for {family}"
            )

        chosen = family_candidates[0]

        selected.append(chosen)
        selected_ids.add(
            chosen["id"]
        )
        represented_families.add(
            family
        )
        covered_features |= (
            chosen["features"]
        )

    # Then greedily add observations that
    # contribute the most new field coverage.
    while len(selected) < TEST_SIZE:
        best = None
        best_score = None

        for item in candidates:
            if item["id"] in selected_ids:
                continue

            new_features = (
                item["features"]
                - covered_features
            )

            score = (
                len(new_features),
                len(item["features"]),
                -item["id"],
            )

            if (
                best is None
                or score > best_score
            ):
                best = item
                best_score = score

        if best is None:
            break

        selected.append(best)
        selected_ids.add(
            best["id"]
        )
        covered_features |= (
            best["features"]
        )

    return (
        selected,
        covered_features,
    )


def compare_observation(
    single,
    batch,
):
    single_signature = (
        research_signature(
            single
        )
    )

    batch_signature = (
        research_signature(
            batch
        )
    )

    mismatches = []

    for field in (
        single_signature
    ):
        if (
            single_signature[field]
            != batch_signature[field]
        ):
            mismatches.append(
                {
                    "field": field,
                    "single":
                        single_signature[
                            field
                        ],
                    "batch":
                        batch_signature[
                            field
                        ],
                }
            )

    return mismatches


def main():
    single_cache = load_json(
        SINGLE_CACHE_FILE
    )

    family_lookup = (
        load_family_lookup()
    )

    (
        selected,
        covered_features,
    ) = select_test_observations(
        single_cache,
        family_lookup,
    )

    selected_ids = [
        item["id"]
        for item in selected
    ]

    print()
    print(
        "BATCH-EQUIVALENCE TEST"
    )
    print(
        "======================"
    )
    print()

    print(
        f"Test observations: "
        f"{len(selected_ids)}"
    )

    print()
    print(
        "SELECTED OBSERVATIONS"
    )
    print(
        "---------------------"
    )

    for item in selected:
        features = ", ".join(
            sorted(
                item["features"]
            )
        )

        print(
            f"  {item['id']}  "
            f"{item['family']}"
        )

        print(
            f"      {features}"
        )

    print()
    print(
        "NON-EMPTY FEATURE COVERAGE"
    )
    print(
        "--------------------------"
    )

    for feature in sorted(
        covered_features
    ):
        print(
            f"  {feature}"
        )

    print()
    print(
        "Fetching all 10 observations "
        "in one batch request..."
    )

    data = api_get(
        (
            "https://api.inaturalist.org/"
            "v1/observations"
        ),
        {
            "id": ",".join(
                str(value)
                for value
                in selected_ids
            ),
            "per_page":
                len(selected_ids),
        },
    )

    batch_results = (
        data.get(
            "results",
            [],
        )
    )

    print(
        f"Batch results returned: "
        f"{len(batch_results)}"
    )

    batch_by_id = {
        int(observation["id"]):
            observation
        for observation
        in batch_results
    }

    save_json(
        BATCH_CACHE_FILE,
        {
            "requested_ids":
                selected_ids,
            "total_results":
                data.get(
                    "total_results"
                ),
            "results":
                batch_results,
        },
    )

    missing_ids = [
        observation_id
        for observation_id
        in selected_ids
        if observation_id
        not in batch_by_id
    ]

    unexpected_ids = [
        observation_id
        for observation_id
        in batch_by_id
        if observation_id
        not in selected_ids
    ]

    print()
    print(
        "BATCH MEMBERSHIP"
    )
    print(
        "----------------"
    )

    print(
        f"  Requested: "
        f"{len(selected_ids)}"
    )

    print(
        f"  Returned: "
        f"{len(batch_by_id)}"
    )

    print(
        f"  Missing requested IDs: "
        f"{len(missing_ids)}"
    )

    if missing_ids:
        for value in missing_ids:
            print(
                f"    {value}"
            )

    print(
        f"  Unexpected IDs: "
        f"{len(unexpected_ids)}"
    )

    if unexpected_ids:
        for value in unexpected_ids:
            print(
                f"    {value}"
            )

    print()
    print(
        "FIELD PRESENCE"
    )
    print(
        "=============="
    )
    print()
    print(
        f"{'Field':38}"
        f"{'Single':>8}"
        f"{'Batch':>8}"
    )

    print(
        f"{'-' * 38}"
        f"{'-' * 8}"
        f"{'-' * 8}"
    )

    for field in FIELDS:
        single_present = 0
        batch_present = 0

        for observation_id in (
            selected_ids
        ):
            single = (
                single_cache[
                    str(observation_id)
                ]
            )

            if field in single:
                single_present += 1

            batch = batch_by_id.get(
                observation_id
            )

            if (
                batch is not None
                and field in batch
            ):
                batch_present += 1

        print(
            f"{field:38}"
            f"{single_present:8}"
            f"{batch_present:8}"
        )

    print()
    print(
        "RESEARCH-SIGNATURE COMPARISON"
    )
    print(
        "============================="
    )

    passed = 0
    failed = 0
    mismatch_fields = {}

    for item in selected:
        observation_id = item["id"]

        single = single_cache[
            str(observation_id)
        ]

        batch = batch_by_id.get(
            observation_id
        )

        if batch is None:
            print()
            print(
                f"FAIL {observation_id} "
                f"{item['family']}: "
                "not returned by batch"
            )

            failed += 1
            continue

        mismatches = (
            compare_observation(
                single,
                batch,
            )
        )

        if not mismatches:
            print(
                f"PASS {observation_id} "
                f"{item['family']}"
            )

            passed += 1
            continue

        failed += 1

        print()
        print(
            f"FAIL {observation_id} "
            f"{item['family']}"
        )

        for mismatch in mismatches:
            field = mismatch[
                "field"
            ]

            mismatch_fields[field] = (
                mismatch_fields.get(
                    field,
                    0,
                )
                + 1
            )

            print(
                f"  FIELD: {field}"
            )

            print(
                "    SINGLE:"
            )

            single_text = repr(
                mismatch["single"]
            )

            if len(single_text) > 500:
                single_text = (
                    single_text[:500]
                    + " ... [truncated]"
                )

            print(
                f"      {single_text}"
            )

            print(
                "    BATCH:"
            )

            batch_text = repr(
                mismatch["batch"]
            )

            if len(batch_text) > 500:
                batch_text = (
                    batch_text[:500]
                    + " ... [truncated]"
                )

            print(
                f"      {batch_text}"
            )

    print()
    print(
        "SUMMARY"
    )
    print(
        "======="
    )

    print(
        f"Research-equivalent: "
        f"{passed}/{len(selected_ids)}"
    )

    print(
        f"Not equivalent: "
        f"{failed}/{len(selected_ids)}"
    )

    if mismatch_fields:
        print()
        print(
            "Mismatch fields:"
        )

        for field, count in sorted(
            mismatch_fields.items(),
            key=lambda item:
                (
                    -item[1],
                    item[0],
                ),
        ):
            print(
                f"  {field:38}"
                f"{count}"
            )

    print()

    if (
        failed == 0
        and not missing_ids
        and not unexpected_ids
    ):
        print(
            "RESULT: BATCH RESPONSES ARE "
            "RESEARCH-EQUIVALENT FOR THIS TEST."
        )

        print(
            "The tested interaction metrics "
            "can be derived from batched "
            "observation responses."
        )

    else:
        print(
            "RESULT: DO NOT SCALE UP YET."
        )

        print(
            "At least one research-relevant "
            "difference needs investigation."
        )

    print()
    print(
        f"Batch response saved to: "
        f"{BATCH_CACHE_FILE}"
    )


if __name__ == "__main__":
    main()