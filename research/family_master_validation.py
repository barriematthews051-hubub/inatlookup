import csv
import glob
import json
import math
import os
from collections import Counter


from family_stage1_decomposition import (
    find_external_capacity,
)

from stage1_nested_validation import (
    choose_direct_model,
    choose_two_stage_model,
    predict_direct_outer,
    predict_two_stage_outer,
)


DATA_DIR = os.path.join(
    "research",
    "data",
)

MASTER_FILE = os.path.join(
    DATA_DIR,
    "family_master_results.csv",
)

STAGE1_FILE = os.path.join(
    DATA_DIR,
    "family_stage1_decomposition.csv",
)

MODEL_A_FILE = os.path.join(
    DATA_DIR,
    "family_model_a_dataset.csv",
)

CACHE_FILE = os.path.join(
    "research",
    "cache",
    "public_interactions_9000.json",
)


FAMILIES = [
    "Syrphidae",
    "Asilidae",
    "Geometridae",
    "Nymphalidae",
    "Staphylinidae",
    "Asteraceae",
    "Formicidae",
    "Libellulidae",
    "Orchidaceae",
    "Poaceae",
    "Russulaceae",
    "Parmeliaceae",
    "Salticidae",
    "Lycosidae",
    "Anatidae",
    "Colubridae",
    "Limacidae",
    "Asteriidae",
]


ABS_TOLERANCE = 1e-8


class Validator:
    def __init__(self):
        self.checks = 0
        self.failures = []

    def pass_check(self):
        self.checks += 1

    def fail(
        self,
        label,
        expected,
        actual,
    ):
        self.checks += 1

        self.failures.append(
            (
                label,
                expected,
                actual,
            )
        )

    def equal(
        self,
        label,
        expected,
        actual,
    ):
        if expected == actual:
            self.pass_check()
        else:
            self.fail(
                label,
                expected,
                actual,
            )

    def close(
        self,
        label,
        expected,
        actual,
        tolerance=ABS_TOLERANCE,
    ):
        if math.isclose(
            float(expected),
            float(actual),
            rel_tol=0.0,
            abs_tol=tolerance,
        ):
            self.pass_check()
        else:
            self.fail(
                label,
                expected,
                actual,
            )


def read_csv(filename):
    with open(
        filename,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        return list(
            csv.DictReader(handle)
        )


def index_by_family(rows):
    return {
        row["family"]: row
        for row in rows
    }


def as_float(value):
    return float(
        str(value).strip()
    )


def as_int(value):
    return int(
        round(
            as_float(value)
        )
    )


def maybe_number(value):
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    try:
        return float(text)

    except ValueError:
        return text


def compare_source_value(
    validator,
    label,
    source_value,
    master_value,
):
    source = maybe_number(
        source_value
    )

    master = maybe_number(
        master_value
    )

    if (
        isinstance(source, float)
        and isinstance(master, float)
    ):
        validator.close(
            label,
            source,
            master,
        )

    else:
        validator.equal(
            label,
            source,
            master,
        )


def load_cache():
    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(
            handle
        )

    result = {}

    for row in (
        data["records"].values()
    ):
        if row.get(
            "status"
        ) != "ok":
            continue

        family = row[
            "family"
        ]

        result.setdefault(
            family,
            []
        ).append(
            row
        )

    return result



def user_set(
    row,
    field,
):
    return {
        int(value)
        for value in row.get(
            field,
            [],
        )
    }


def positive_cache_value(value):
    if value is None:
        return False

    if isinstance(
        value,
        bool,
    ):
        return value

    if isinstance(
        value,
        (int, float),
    ):
        return value > 0

    if isinstance(
        value,
        (list, tuple, set, dict),
    ):
        return bool(value)

    text = str(
        value
    ).strip().lower()

    if text in {
        "",
        "0",
        "0.0",
        "false",
        "none",
        "null",
        "[]",
        "{}",
    }:
        return False

    try:
        return float(text) > 0

    except ValueError:
        return True


def external_cv_keys(rows):
    return sorted(
        {
            key
            for row in rows
            for key in row.keys()
            if (
                "external"
                in key.lower()
                and (
                    "vision"
                    in key.lower()
                    or "cv"
                    in key.lower()
                )
            )
        }
    )


def has_external_cv(row):
    return any(
        positive_cache_value(
            row.get(key)
        )
        for key in row.keys()
        if (
            "external"
            in key.lower()
            and (
                "vision"
                in key.lower()
                or "cv"
                in key.lower()
            )
        )
    )




def recompute_interactions(rows):
    no_id_rows = [
        row
        for row in rows
        if not row[
            "external_id_present"
        ]
    ]

    reviewer_counter = Counter()

    for row in no_id_rows:
        users = user_set(
            row,
            "reviewer_no_id_user_ids",
        )

        for user_id in users:
            reviewer_counter[
                user_id
            ] += 1

    ranked = (
        reviewer_counter.most_common()
    )

    review_pairs = sum(
        reviewer_counter.values()
    )

    top1_user = (
        ranked[0][0]
        if ranked
        else ""
    )

    top1_count = (
        ranked[0][1]
        if ranked
        else 0
    )

    top5_users = {
        user_id
        for user_id, count
        in ranked[:5]
    }

    top5_pair_count = sum(
        count
        for user_id, count
        in ranked[:5]
    )

    top5_observation_count = 0

    for row in no_id_rows:
        reviewers = user_set(
            row,
            "reviewer_no_id_user_ids",
        )

        if reviewers & top5_users:
            top5_observation_count += 1

    def obs_with_users(field):
        return sum(
            bool(
                user_set(
                    row,
                    field,
                )
            )
            for row in rows
        )

    strict_count = 0

    for row in rows:
        strict_users = set()

        strict_users |= user_set(
            row,
            "commenter_no_id_user_ids",
        )

        strict_users |= user_set(
            row,
            "annotator_no_id_user_ids",
        )

        strict_users |= user_set(
            row,
            "dqa_no_id_user_ids",
        )

        strict_users |= user_set(
            row,
            "field_no_id_user_ids",
        )

        if strict_users:
            strict_count += 1

    reviewed_no_id = sum(
        bool(
            user_set(
                row,
                "reviewer_no_id_user_ids",
            )
        )
        for row in no_id_rows
    )

    owner_cv_known = sum(
        row.get(
            "owner_vision"
        )
        is not None
        for row in rows
    )

    owner_cv_yes = sum(
        row.get(
            "owner_vision"
        )
        is True
        for row in rows
    )



    external_cv = sum(
        has_external_cv(row)
        for row in rows
    )

    no_id_count = len(
        no_id_rows
    )

    return {
        "no_external_id_count":
            no_id_count,

        "reviewed_no_id_count":
            reviewed_no_id,

        "silent_review_pairs":
            review_pairs,

        "unique_silent_reviewers":
            len(
                reviewer_counter
            ),

        "dominant_silent_reviewer":
            top1_user,

        "dominant_silent_reviewer_observations":
            top1_count,

        "dominant_reviewer_share_pairs":
            (
                top1_count
                / review_pairs
                if review_pairs
                else 0.0
            ),

        "top5_reviewer_share_pairs":
            (
                top5_pair_count
                / review_pairs
                if review_pairs
                else 0.0
            ),

        "top5_reviewer_observation_coverage":
            (
                top5_observation_count
                / no_id_count
                if no_id_count
                else 0.0
            ),

        "comment_no_id_action_count":
            obs_with_users(
                "commenter_no_id_user_ids"
            ),

        "annotation_no_id_action_count":
            obs_with_users(
                "annotator_no_id_user_ids"
            ),

        "dqa_no_id_action_count":
            obs_with_users(
                "dqa_no_id_user_ids"
            ),

        "field_no_id_action_count":
            obs_with_users(
                "field_no_id_user_ids"
            ),

        "fave_no_id_action_count":
            obs_with_users(
                "fave_no_id_user_ids"
            ),

        "strict_non_id_action_count":
            strict_count,

        "owner_cv_known_count":
            owner_cv_known,

        "owner_cv_yes_count":
            owner_cv_yes,

        "owner_cv_yes_rate_known":
            (
                owner_cv_yes
                / owner_cv_known
                if owner_cv_known
                else 0.0
            ),

        "external_cv_observation_count":
            external_cv,

        "external_cv_observation_rate":
            external_cv
            / len(rows),
    }


def find_analysis_file(family):
    matches = []

    for filename in glob.glob(
        os.path.join(
            DATA_DIR,
            "*_pilot_500_analysis.csv",
        )
    ):
        basename = os.path.basename(
            filename
        ).lower()

        if basename.startswith(
            family.lower()
        ):
            matches.append(
                filename
            )

    if len(matches) != 1:
        raise ValueError(
            f"{family}: expected "
            "one analysis file, "
            f"found {matches}"
        )

    return matches[0]


def recompute_stage2(family):
    filename = find_analysis_file(
        family
    )

    rows = read_csv(
        filename
    )

    if len(rows) != 500:
        raise ValueError(
            f"{family}: expected "
            "500 analysis rows, "
            f"found {len(rows)}"
        )

    if (
        "community_taxon_rank"
        not in rows[0]
    ):
        raise ValueError(
            f"{family}: "
            "community_taxon_rank "
            "column not found."
        )

    species = 0
    genus = 0
    higher = 0
    no_community = 0

    missing = {
        "",
        "none",
        "null",
        "na",
        "n/a",
        "nan",
        "unknown",
    }

    for row in rows:
        value = row.get(
            "community_taxon_rank"
        )

        rank = (
            str(value).strip().lower()
            if value is not None
            else ""
        )

        if rank in missing:
            no_community += 1

        elif rank == "species":
            species += 1

        elif rank == "genus":
            genus += 1

        else:
            higher += 1

    return {
        "community_species_count":
            species,

        "community_genus_count":
            genus,

        "community_higher_count":
            higher,

        "no_community_taxon_count":
            no_community,
    }


def recompute_nested(stage1_rows):
    direct_predictions = {}
    two_stage_predictions = {}

    direct_models = {}
    two_stage_models = {}

    for held_out in range(
        len(stage1_rows)
    ):
        training_rows = [
            row
            for index, row
            in enumerate(
                stage1_rows
            )
            if index != held_out
        ]

        test_row = stage1_rows[
            held_out
        ]

        (
            direct_inner_mae,
            direct_model,
        ) = choose_direct_model(
            training_rows
        )

        (
            two_inner_mae,
            two_label,
            reach_model,
            conversion_model,
        ) = choose_two_stage_model(
            training_rows
        )

        direct_prediction = (
            predict_direct_outer(
                training_rows,
                test_row,
                direct_model,
            )
        )

        two_prediction = (
            predict_two_stage_outer(
                training_rows,
                test_row,
                reach_model,
                conversion_model,
            )
        )

        family = test_row[
            "family"
        ]

        direct_predictions[
            family
        ] = direct_prediction

        two_stage_predictions[
            family
        ] = two_prediction

        direct_models[
            family
        ] = direct_model

        two_stage_models[
            family
        ] = two_label

    return {
        "direct_predictions":
            direct_predictions,

        "two_stage_predictions":
            two_stage_predictions,

        "direct_models":
            direct_models,

        "two_stage_models":
            two_stage_models,
    }


def validate_core(
    validator,
    master,
    stage1,
):
    print()
    print(
        "1. CORE STAGE-1 VALUES"
    )
    print(
        "----------------------"
    )

    fields = [
        (
            "external_id_count",
            "external_id_count",
        ),
        (
            "stage1a_raw_reach_count",
            "raw_reach_count",
        ),
        (
            "stage1a_top1_reach_count",
            "top1_reach_count",
        ),
        (
            "stage1a_top5_reach_count",
            "top5_reach_count",
        ),
    ]

    before = validator.checks

    for family in FAMILIES:
        for (
            master_field,
            source_field,
        ) in fields:
            validator.equal(
                family
                + " "
                + master_field,
                as_int(
                    stage1[
                        family
                    ][
                        source_field
                    ]
                ),
                as_int(
                    master[
                        family
                    ][
                        master_field
                    ]
                ),
            )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_predictors(
    validator,
    master,
    model_a,
):
    print()
    print(
        "2. MODEL-A PREDICTOR FIELDS"
    )
    print(
        "---------------------------"
    )

    source_fields = [
        field
        for field
        in next(
            iter(
                model_a.values()
            )
        ).keys()
        if field != "family"
    ]

    before = validator.checks

    for family in FAMILIES:
        for field in source_fields:
            master_field = (
                "predictor_"
                + field
            )

            if (
                master_field
                not in master[
                    family
                ]
            ):
                validator.fail(
                    family
                    + " "
                    + master_field,
                    "column present",
                    "missing",
                )
                continue

            compare_source_value(
                validator,
                family
                + " "
                + master_field,
                model_a[
                    family
                ][field],
                master[
                    family
                ][
                    master_field
                ],
            )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_pre2024(
    validator,
    master,
):
    print()
    print(
        "3. PRE-2025 IDENTIFIER STRUCTURE"
    )
    print(
        "--------------------------------"
    )

    (
        filename,
        capacity_column,
        capacity_values,
    ) = find_external_capacity()

    rows = index_by_family(
        read_csv(filename)
    )

    source_fields = [
        field
        for field
        in next(
            iter(
                rows.values()
            )
        ).keys()
        if field != "family"
    ]

    before = validator.checks

    for family in FAMILIES:
        validator.close(
            family
            + " external_capacity",
            capacity_values[
                family
            ],
            as_float(
                master[
                    family
                ][
                    "external_capacity"
                ]
            ),
        )

        for field in source_fields:
            master_field = (
                "pre2024_"
                + field
            )

            if (
                master_field
                not in master[
                    family
                ]
            ):
                validator.fail(
                    family
                    + " "
                    + master_field,
                    "column present",
                    "missing",
                )
                continue

            compare_source_value(
                validator,
                family
                + " "
                + master_field,
                rows[
                    family
                ][field],
                master[
                    family
                ][
                    master_field
                ],
            )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Source: "
        f"{os.path.basename(filename)}"
    )

    print(
        f"  Capacity column: "
        f"{capacity_column}"
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_interactions(
    validator,
    master,
    cache,
):
    print()


    print(
        "4. INTERACTION / REVIEW FIELDS"
    )
    print(
        "------------------------------"
    )

    detected_cv_keys = sorted(
        {
            key
            for family in FAMILIES
            for key in external_cv_keys(
                cache[family]
            )
        }
    )

    print(
        "  External-CV cache keys "
        "detected:"
    )

    for key in detected_cv_keys:
        print(
            f"    {key}"
        )


    integer_fields = [
        "no_external_id_count",
        "reviewed_no_id_count",
        "silent_review_pairs",
        "unique_silent_reviewers",
        "dominant_silent_reviewer_observations",
        "comment_no_id_action_count",
        "annotation_no_id_action_count",
        "dqa_no_id_action_count",
        "field_no_id_action_count",
        "fave_no_id_action_count",
        "strict_non_id_action_count",
        "owner_cv_known_count",
        "owner_cv_yes_count",
        "external_cv_observation_count",
    ]

    float_fields = [
        "dominant_reviewer_share_pairs",
        "top5_reviewer_share_pairs",
        "top5_reviewer_observation_coverage",
        "owner_cv_yes_rate_known",
        "external_cv_observation_rate",
    ]

    before = validator.checks

    for family in FAMILIES:
        recomputed = (
            recompute_interactions(
                cache[
                    family
                ]
            )
        )

        expected_user = (
            recomputed[
                "dominant_silent_reviewer"
            ]
        )

        actual_user = master[
            family
        ][
            "dominant_silent_reviewer"
        ]

        if expected_user == "":
            validator.equal(
                family
                + " dominant reviewer",
                "",
                actual_user,
            )
        else:
            validator.equal(
                family
                + " dominant reviewer",
                int(
                    expected_user
                ),
                as_int(
                    actual_user
                ),
            )

        for field in integer_fields:
            validator.equal(
                family
                + " "
                + field,
                int(
                    recomputed[
                        field
                    ]
                ),
                as_int(
                    master[
                        family
                    ][field]
                ),
            )

        for field in float_fields:
            validator.close(
                family
                + " "
                + field,
                recomputed[
                    field
                ],
                as_float(
                    master[
                        family
                    ][field]
                ),
            )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_stage2(
    validator,
    master,
):
    print()
    print(
        "5. STAGE-2 COMMUNITY TAXON"
    )
    print(
        "--------------------------"
    )

    before = validator.checks

    count_fields = [
        "community_species_count",
        "community_genus_count",
        "community_higher_count",
        "no_community_taxon_count",
    ]

    for family in FAMILIES:
        expected = (
            recompute_stage2(
                family
            )
        )

        for field in count_fields:
            validator.equal(
                family
                + " "
                + field,
                expected[
                    field
                ],
                as_int(
                    master[
                        family
                    ][field]
                ),
            )

        total = sum(
            expected[
                field
            ]
            for field in count_fields
        )

        validator.equal(
            family
            + " Stage2 total",
            500,
            total,
        )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_nested(
    validator,
    master,
    stage1_rows,
):
    print()
    print(
        "6. NESTED MODEL RESULTS"
    )
    print(
        "-----------------------"
    )

    nested = recompute_nested(
        stage1_rows
    )

    before = validator.checks

    for family in FAMILIES:
        validator.equal(
            family
            + " nested direct model",
            nested[
                "direct_models"
            ][family],
            master[
                family
            ][
                "nested_direct_model"
            ],
        )

        validator.equal(
            family
            + " nested two-stage model",
            nested[
                "two_stage_models"
            ][family],
            master[
                family
            ][
                "nested_two_stage_model"
            ],
        )

        direct_prediction = nested[
            "direct_predictions"
        ][family]

        two_prediction = nested[
            "two_stage_predictions"
        ][family]

        actual = as_float(
            master[
                family
            ][
                "external_id_rate"
            ]
        )

        validator.close(
            family
            + " direct prediction",
            direct_prediction,
            as_float(
                master[
                    family
                ][
                    "nested_direct_prediction"
                ]
            ),
        )

        validator.close(
            family
            + " two-stage prediction",
            two_prediction,
            as_float(
                master[
                    family
                ][
                    "nested_two_stage_prediction"
                ]
            ),
        )

        validator.close(
            family
            + " direct residual",
            actual
            - direct_prediction,
            as_float(
                master[
                    family
                ][
                    "nested_direct_residual"
                ]
            ),
        )

        validator.close(
            family
            + " two-stage residual",
            actual
            - two_prediction,
            as_float(
                master[
                    family
                ][
                    "nested_two_stage_residual"
                ]
            ),
        )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_benchmarks(
    validator,
    master,
):
    print()
    print(
        "7. KNOWN BENCHMARK SPOT CHECKS"
    )
    print(
        "------------------------------"
    )

    before = validator.checks

    # Limacidae (keeled slugs):
    # the extreme reviewer-concentration
    # example discovered during the audit.
    validator.equal(
        "Limacidae dominant reviewer",
        6053932,
        as_int(
            master[
                "Limacidae"
            ][
                "dominant_silent_reviewer"
            ]
        ),
    )

    validator.equal(
        "Limacidae dominant reviewer observations",
        189,
        as_int(
            master[
                "Limacidae"
            ][
                "dominant_silent_reviewer_observations"
            ]
        ),
    )

    validator.equal(
        "Limacidae raw reach",
        496,
        as_int(
            master[
                "Limacidae"
            ][
                "stage1a_raw_reach_count"
            ]
        ),
    )

    validator.equal(
        "Limacidae Top5 reach",
        345,
        as_int(
            master[
                "Limacidae"
            ][
                "stage1a_top5_reach_count"
            ]
        ),
    )

    validator.equal(
        "Limacidae silent-review pairs",
        266,
        as_int(
            master[
                "Limacidae"
            ][
                "silent_review_pairs"
            ]
        ),
    )

    validator.equal(
        "Limacidae unique silent reviewers",
        32,
        as_int(
            master[
                "Limacidae"
            ][
                "unique_silent_reviewers"
            ]
        ),
    )

    # Annotation-heavy families.
    validator.equal(
        "Syrphidae annotation count",
        148,
        as_int(
            master[
                "Syrphidae"
            ][
                "annotation_no_id_action_count"
            ]
        ),
    )

    validator.equal(
        "Geometridae annotation count",
        181,
        as_int(
            master[
                "Geometridae"
            ][
                "annotation_no_id_action_count"
            ]
        ),
    )

    validator.equal(
        "Nymphalidae annotation count",
        158,
        as_int(
            master[
                "Nymphalidae"
            ][
                "annotation_no_id_action_count"
            ]
        ),
    )

    # Owner CV benchmarks.
    validator.equal(
        "Syrphidae owner CV yes",
        287,
        as_int(
            master[
                "Syrphidae"
            ][
                "owner_cv_yes_count"
            ]
        ),
    )

    validator.equal(
        "Syrphidae owner CV known",
        486,
        as_int(
            master[
                "Syrphidae"
            ][
                "owner_cv_known_count"
            ]
        ),
    )

    validator.equal(
        "Geometridae owner CV yes",
        319,
        as_int(
            master[
                "Geometridae"
            ][
                "owner_cv_yes_count"
            ]
        ),
    )

    validator.equal(
        "Geometridae owner CV known",
        490,
        as_int(
            master[
                "Geometridae"
            ][
                "owner_cv_known_count"
            ]
        ),
    )

    # External-CV benchmarks.
    validator.equal(
        "Syrphidae external CV",
        44,
        as_int(
            master[
                "Syrphidae"
            ][
                "external_cv_observation_count"
            ]
        ),
    )

    validator.equal(
        "Limacidae external CV",
        57,
        as_int(
            master[
                "Limacidae"
            ][
                "external_cv_observation_count"
            ]
        ),
    )

    # Stage-2 benchmarks.
    validator.equal(
        "Syrphidae species CT",
        282,
        as_int(
            master[
                "Syrphidae"
            ][
                "community_species_count"
            ]
        ),
    )

    validator.equal(
        "Russulaceae species CT",
        81,
        as_int(
            master[
                "Russulaceae"
            ][
                "community_species_count"
            ]
        ),
    )

    validator.equal(
        "Asteriidae species CT",
        441,
        as_int(
            master[
                "Asteriidae"
            ][
                "community_species_count"
            ]
        ),
    )

    validator.equal(
        "Asteriidae no community taxon",
        20,
        as_int(
            master[
                "Asteriidae"
            ][
                "no_community_taxon_count"
            ]
        ),
    )

    count = (
        validator.checks
        - before
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def validate_totals(
    validator,
    master,
):
    print()
    print(
        "8. MASTER TOTALS"
    )
    print(
        "----------------"
    )

    before = validator.checks

    total_external = sum(
        as_int(
            master[
                family
            ][
                "external_id_count"
            ]
        )
        for family in FAMILIES
    )

    total_raw_reach = sum(
        as_int(
            master[
                family
            ][
                "stage1a_raw_reach_count"
            ]
        )
        for family in FAMILIES
    )

    total_top5_reach = sum(
        as_int(
            master[
                family
            ][
                "stage1a_top5_reach_count"
            ]
        )
        for family in FAMILIES
    )

    validator.equal(
        "Total external IDs",
        6550,
        total_external,
    )

    validator.equal(
        "Total raw review reach",
        7651,
        total_raw_reach,
    )

    validator.equal(
        "Total Top5 sensitivity reach",
        7124,
        total_top5_reach,
    )

    validator.equal(
        "Master family count",
        18,
        len(master),
    )

    count = (
        validator.checks
        - before
    )

    print(
        f"  External IDs: "
        f"{total_external}/9000"
    )

    print(
        f"  Raw reach: "
        f"{total_raw_reach}/9000"
    )

    print(
        f"  Top-5 reach: "
        f"{total_top5_reach}/9000"
    )

    print(
        f"  Checks completed: "
        f"{count}"
    )


def main():
    validator = Validator()

    master_rows = read_csv(
        MASTER_FILE
    )

    stage1_rows = read_csv(
        STAGE1_FILE
    )

    model_a_rows = read_csv(
        MODEL_A_FILE
    )

    master = index_by_family(
        master_rows
    )

    stage1 = index_by_family(
        stage1_rows
    )

    model_a = index_by_family(
        model_a_rows
    )

    cache = load_cache()

    print()
    print(
        "MASTER RESULTS SPOT VALIDATION"
    )
    print(
        "=============================="
    )

    print()
    print(
        f"Master rows: "
        f"{len(master_rows)}"
    )

    if master_rows:
        print(
            f"Master columns: "
            f"{len(master_rows[0])}"
        )

    validate_core(
        validator,
        master,
        stage1,
    )

    validate_predictors(
        validator,
        master,
        model_a,
    )

    validate_pre2024(
        validator,
        master,
    )

    validate_interactions(
        validator,
        master,
        cache,
    )

    validate_stage2(
        validator,
        master,
    )

    validate_nested(
        validator,
        master,
        stage1_rows,
    )

    validate_benchmarks(
        validator,
        master,
    )

    validate_totals(
        validator,
        master,
    )

    print()
    print(
        "FINAL RESULT"
    )
    print(
        "============"
    )

    print()
    print(
        f"Checks performed: "
        f"{validator.checks}"
    )

    print(
        f"Failures: "
        f"{len(validator.failures)}"
    )

    if not validator.failures:
        print()
        print(
            "PASS: Master results table "
            "validated successfully."
        )

        print()
        print(
            "family_master_results.csv "
            "can now be treated as "
            "Master Results v1."
        )

        return

    print()
    print(
        "FAILURES"
    )
    print(
        "--------"
    )

    for (
        label,
        expected,
        actual,
    ) in validator.failures:
        print()
        print(
            label
        )

        print(
            f"  Expected: "
            f"{expected}"
        )

        print(
            f"  Actual:   "
            f"{actual}"
        )

    raise SystemExit(
        1
    )


if __name__ == "__main__":
    main()