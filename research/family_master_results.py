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

CACHE_FILE = os.path.join(
    "research",
    "cache",
    "public_interactions_9000.json",
)

STAGE1_FILE = os.path.join(
    DATA_DIR,
    "family_stage1_decomposition.csv",
)

MODEL_A_FILE = os.path.join(
    DATA_DIR,
    "family_model_a_dataset.csv",
)

OUTPUT_FILE = os.path.join(
    DATA_DIR,
    "family_master_results.csv",
)


FAMILIES = [
    ("Syrphidae", "hoverflies"),
    ("Asilidae", "robber flies"),
    ("Geometridae", "geometer moths"),
    ("Nymphalidae", "brush-footed butterflies"),
    ("Staphylinidae", "rove beetles"),
    ("Asteraceae", "daisy/sunflower family"),
    ("Formicidae", "ants"),
    ("Libellulidae", "skimmers and perchers"),
    ("Orchidaceae", "orchid family"),
    ("Poaceae", "grass family"),
    ("Russulaceae", "russulas and milkcaps"),
    ("Parmeliaceae", "shield lichens"),
    ("Salticidae", "jumping spiders"),
    ("Lycosidae", "wolf spiders"),
    ("Anatidae", "ducks, geese and swans"),
    ("Colubridae", "colubrid snakes"),
    ("Limacidae", "keeled slugs"),
    ("Asteriidae", "common sea stars"),
]


def normalize(text):
    return "".join(
        char.lower()
        for char in str(text)
        if char.isalnum()
    )


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


def read_csv_rows(filename):
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
    result = {}

    for row in rows:
        family = row.get(
            "family"
        )

        if family:
            result[family] = row

    return result


def numeric_or_blank(value):
    if value is None:
        return ""

    text = str(value).strip()

    if not text:
        return ""

    try:
        number = float(text)

        if number.is_integer():
            return int(number)

        return number

    except ValueError:
        return text


def prefixed_row(
    row,
    prefix,
    exclude=None,
):
    exclude = set(
        exclude or []
    )

    result = {}

    for key, value in row.items():
        if key in exclude:
            continue

        result[
            prefix + key
        ] = numeric_or_blank(
            value
        )

    return result


def load_stage1():
    rows = read_csv_rows(
        STAGE1_FILE
    )

    if len(rows) != 18:
        raise ValueError(
            "Expected 18 rows in "
            f"{STAGE1_FILE}, "
            f"found {len(rows)}"
        )

    return (
        rows,
        index_by_family(rows),
    )


def load_model_a():
    rows = read_csv_rows(
        MODEL_A_FILE
    )

    if len(rows) != 18:
        raise ValueError(
            "Expected 18 rows in "
            f"{MODEL_A_FILE}, "
            f"found {len(rows)}"
        )

    return index_by_family(
        rows
    )


def load_capacity_structure():
    (
        filename,
        capacity_column,
        capacity_values,
    ) = find_external_capacity()

    rows = read_csv_rows(
        filename
    )

    indexed = index_by_family(
        rows
    )

    missing = [
        family
        for family, common_name
        in FAMILIES
        if family not in indexed
    ]

    if missing:
        raise ValueError(
            "External identifier "
            "structure file is missing: "
            + ", ".join(missing)
        )

    return (
        filename,
        capacity_column,
        indexed,
    )


def load_interactions():
    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(
            handle
        )

    result = {}

    for record in (
        data["records"].values()
    ):
        if (
            record.get("status")
            != "ok"
        ):
            continue

        family = record[
            "family"
        ]

        result.setdefault(
            family,
            []
        ).append(
            record
        )

    for family, common_name in FAMILIES:
        count = len(
            result.get(
                family,
                [],
            )
        )

        if count != 500:
            raise ValueError(
                f"{family}: expected "
                f"500 interaction records, "
                f"found {count}"
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


def has_external_cv(row):
    matching_keys = [
        key
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
    ]

    return any(
        positive_cache_value(
            row.get(key)
        )
        for key in matching_keys
    )



def interaction_summary(rows):
    no_id_rows = [
        row
        for row in rows
        if not row[
            "external_id_present"
        ]
    ]

    review_counter = Counter()

    for row in no_id_rows:
        for user_id in user_set(
            row,
            "reviewer_no_id_user_ids",
        ):
            review_counter[
                user_id
            ] += 1

    ranked = (
        review_counter.most_common()
    )

    total_review_pairs = sum(
        review_counter.values()
    )

    top1_count = (
        ranked[0][1]
        if ranked
        else 0
    )

    top5_count = sum(
        count
        for user_id, count
        in ranked[:5]
    )

    top5_users = {
        user_id
        for user_id, count
        in ranked[:5]
    }

    top5_observations = set()

    for row in no_id_rows:
        reviewers = user_set(
            row,
            "reviewer_no_id_user_ids",
        )

        if reviewers & top5_users:
            top5_observations.add(
                int(
                    row[
                        "observation_id"
                    ]
                )
            )

    def observation_count(field):
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

        for field in [
            "commenter_no_id_user_ids",
            "annotator_no_id_user_ids",
            "dqa_no_id_user_ids",
            "field_no_id_user_ids",
        ]:
            strict_users |= user_set(
                row,
                field,
            )

        if strict_users:
            strict_count += 1

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


    reviewed_no_id_observations = sum(
        bool(
            user_set(
                row,
                "reviewer_no_id_user_ids",
            )
        )
        for row in no_id_rows
    )

    return {
        "no_external_id_count":
            len(no_id_rows),

        "reviewed_no_id_count":
            reviewed_no_id_observations,

        "silent_review_pairs":
            total_review_pairs,

        "unique_silent_reviewers":
            len(
                review_counter
            ),

        "dominant_silent_reviewer":
            (
                ranked[0][0]
                if ranked
                else ""
            ),

        "dominant_silent_reviewer_observations":
            top1_count,

        "dominant_reviewer_share_pairs":
            (
                top1_count
                / total_review_pairs
                if total_review_pairs
                else 0.0
            ),

        "top5_reviewer_share_pairs":
            (
                top5_count
                / total_review_pairs
                if total_review_pairs
                else 0.0
            ),

        "top5_reviewer_observation_coverage":
            (
                len(
                    top5_observations
                )
                / len(no_id_rows)
                if no_id_rows
                else 0.0
            ),

        "comment_no_id_action_count":
            observation_count(
                "commenter_no_id_user_ids"
            ),

        "annotation_no_id_action_count":
            observation_count(
                "annotator_no_id_user_ids"
            ),

        "dqa_no_id_action_count":
            observation_count(
                "dqa_no_id_user_ids"
            ),

        "field_no_id_action_count":
            observation_count(
                "field_no_id_user_ids"
            ),

        "fave_no_id_action_count":
            observation_count(
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


def find_analysis_file(
    family,
):
    target_start = (
        family.lower()
    )

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
            target_start
        ):
            matches.append(
                filename
            )

    if not matches:
        # Try a looser match in case the
        # filenames use another slug style.
        for filename in glob.glob(
            os.path.join(
                DATA_DIR,
                "*analysis.csv",
            )
        ):
            basename = normalize(
                os.path.basename(
                    filename
                )
            )

            if normalize(
                family
            ) in basename:
                matches.append(
                    filename
                )

    if len(matches) != 1:
        raise ValueError(
            f"{family}: expected exactly "
            "one pilot analysis CSV, "
            f"found {len(matches)}: "
            f"{matches}"
        )

    return matches[0]


def find_community_rank_column(
    fieldnames,
):
    normalized = {
        normalize(field):
            field
        for field in fieldnames
    }

    preferred = [
        "communitytaxonrank",
        "communityrank",
        "communitytaxonrankname",
        "communitytaxonranklabel",
    ]

    for candidate in preferred:
        if candidate in normalized:
            return normalized[
                candidate
            ]

    matches = [
        field
        for field in fieldnames
        if (
            "community"
            in normalize(field)
            and "rank"
            in normalize(field)
        )
    ]

    if len(matches) == 1:
        return matches[0]

    raise ValueError(
        "Could not uniquely identify "
        "community-taxon rank column.\n"
        "Columns were:\n  "
        + "\n  ".join(
            fieldnames
        )
    )


def stage2_summary(
    family,
    external_id_count,
):
    filename = find_analysis_file(
        family
    )

    rows = read_csv_rows(
        filename
    )

    if len(rows) != 500:
        raise ValueError(
            f"{family}: expected 500 "
            "analysis rows in "
            f"{filename}, "
            f"found {len(rows)}"
        )

    fieldnames = list(
        rows[0].keys()
    )

    rank_field = (
        find_community_rank_column(
            fieldnames
        )
    )

    species = 0
    genus = 0
    no_community = 0
    higher = 0

    rank_counter = Counter()

    missing_tokens = {
        "",
        "none",
        "null",
        "na",
        "n/a",
        "nan",
        "unknown",
    }

    for row in rows:
        raw_rank = row.get(
            rank_field
        )

        rank = (
            str(raw_rank).strip().lower()
            if raw_rank is not None
            else ""
        )

        rank_counter[
            rank
        ] += 1

        if rank in missing_tokens:
            no_community += 1

        elif rank == "species":
            species += 1

        elif rank == "genus":
            genus += 1

        else:
            higher += 1

    return {
        "stage2_source_file":
            os.path.basename(
                filename
            ),

        "stage2_rank_column":
            rank_field,

        "community_species_count":
            species,

        "community_species_rate":
            species / 500,

        "community_genus_count":
            genus,

        "community_genus_rate":
            genus / 500,

        "community_higher_count":
            higher,

        "community_higher_rate":
            higher / 500,

        "no_community_taxon_count":
            no_community,

        "no_community_taxon_rate":
            no_community / 500,

        "species_given_external_id":
            (
                species
                / external_id_count
                if external_id_count
                else 0.0
            ),
    }


def nested_predictions(
    stage1_rows,
):
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


def ordered_fieldnames(rows):
    preferred = [
        "family",
        "common_name",

        "external_id_count",
        "external_id_rate",

        "stage1a_raw_reach_count",
        "stage1a_raw_reach_rate",
        "stage1a_top1_reach_count",
        "stage1a_top1_reach_rate",
        "stage1a_top5_reach_count",
        "stage1a_top5_reach_rate",

        "stage1b_raw_conversion_rate",
        "stage1b_top1_conversion_rate",
        "stage1b_top5_conversion_rate",

        "community_species_count",
        "community_species_rate",
        "community_genus_count",
        "community_genus_rate",
        "community_higher_count",
        "community_higher_rate",
        "no_community_taxon_count",
        "no_community_taxon_rate",
        "species_given_external_id",

        "external_capacity",

        "nested_direct_model",
        "nested_direct_prediction",
        "nested_direct_residual",

        "nested_two_stage_model",
        "nested_two_stage_prediction",
        "nested_two_stage_residual",

        "no_external_id_count",
        "reviewed_no_id_count",
        "silent_review_pairs",
        "unique_silent_reviewers",

        "dominant_silent_reviewer",
        "dominant_silent_reviewer_observations",
        "dominant_reviewer_share_pairs",
        "top5_reviewer_share_pairs",
        "top5_reviewer_observation_coverage",

        "strict_non_id_action_count",
        "comment_no_id_action_count",
        "annotation_no_id_action_count",
        "dqa_no_id_action_count",
        "field_no_id_action_count",
        "fave_no_id_action_count",

        "owner_cv_known_count",
        "owner_cv_yes_count",
        "owner_cv_yes_rate_known",

        "external_cv_observation_count",
        "external_cv_observation_rate",

        "stage2_source_file",
        "stage2_rank_column",
    ]

    all_fields = set()

    for row in rows:
        all_fields.update(
            row.keys()
        )

    result = []

    for field in preferred:
        if field in all_fields:
            result.append(
                field
            )

            all_fields.remove(
                field
            )

    # Keep automatically merged predictor
    # and pre-2025 structure columns grouped.
    for prefix in [
        "predictor_",
        "pre2024_",
    ]:
        matching = sorted(
            field
            for field in all_fields
            if field.startswith(
                prefix
            )
        )

        result.extend(
            matching
        )

        for field in matching:
            all_fields.remove(
                field
            )

    result.extend(
        sorted(
            all_fields
        )
    )

    return result


def main():
    (
        stage1_rows,
        stage1_by_family,
    ) = load_stage1()

    model_a = load_model_a()

    (
        capacity_file,
        capacity_column,
        capacity_structure,
    ) = load_capacity_structure()

    interactions = (
        load_interactions()
    )

    nested = nested_predictions(
        stage1_rows
    )

    print()
    print(
        "FAMILY MASTER RESULTS TABLE"
    )
    print(
        "==========================="
    )

    print()
    print(
        "External identifier "
        "structure source:"
    )

    print(
        f"  {capacity_file}"
    )

    print(
        "External capacity column:"
    )

    print(
        f"  {capacity_column}"
    )

    master_rows = []

    for family, common_name in FAMILIES:
        if family not in stage1_by_family:
            raise ValueError(
                f"{family} missing "
                "from Stage 1 file."
            )

        if family not in model_a:
            raise ValueError(
                f"{family} missing "
                "from Model A file."
            )

        stage1 = stage1_by_family[
            family
        ]

        external_count = int(
            float(
                stage1[
                    "external_id_count"
                ]
            )
        )

        raw_reach = int(
            float(
                stage1[
                    "raw_reach_count"
                ]
            )
        )

        top1_reach = int(
            float(
                stage1[
                    "top1_reach_count"
                ]
            )
        )

        top5_reach = int(
            float(
                stage1[
                    "top5_reach_count"
                ]
            )
        )

        interaction = (
            interaction_summary(
                interactions[
                    family
                ]
            )
        )

        stage2 = stage2_summary(
            family,
            external_count,
        )

        actual_external_rate = (
            external_count
            / 500
        )

        direct_prediction = (
            nested[
                "direct_predictions"
            ][family]
        )

        two_prediction = (
            nested[
                "two_stage_predictions"
            ][family]
        )

        row = {
            "family":
                family,

            "common_name":
                common_name,

            "external_id_count":
                external_count,

            "external_id_rate":
                actual_external_rate,

            "stage1a_raw_reach_count":
                raw_reach,

            "stage1a_raw_reach_rate":
                raw_reach / 500,

            "stage1a_top1_reach_count":
                top1_reach,

            "stage1a_top1_reach_rate":
                top1_reach / 500,

            "stage1a_top5_reach_count":
                top5_reach,

            "stage1a_top5_reach_rate":
                top5_reach / 500,

            "stage1b_raw_conversion_rate":
                (
                    external_count
                    / raw_reach
                ),

            "stage1b_top1_conversion_rate":
                (
                    external_count
                    / top1_reach
                ),

            "stage1b_top5_conversion_rate":
                (
                    external_count
                    / top5_reach
                ),

            "external_capacity":
                float(
                    stage1[
                        "external_capacity"
                    ]
                ),

            "nested_direct_model":
                nested[
                    "direct_models"
                ][family],

            "nested_direct_prediction":
                direct_prediction,

            "nested_direct_residual":
                (
                    actual_external_rate
                    - direct_prediction
                ),

            "nested_two_stage_model":
                nested[
                    "two_stage_models"
                ][family],

            "nested_two_stage_prediction":
                two_prediction,

            "nested_two_stage_residual":
                (
                    actual_external_rate
                    - two_prediction
                ),
        }

        row.update(
            stage2
        )

        row.update(
            interaction
        )

        # Retain every column from the
        # original Model A family dataset.
        row.update(
            prefixed_row(
                model_a[
                    family
                ],
                "predictor_",
                exclude={
                    "family",
                },
            )
        )

        # Retain every column from the
        # pre-2025 external identifier
        # structure dataset. This means
        # breadth/concentration variables
        # are preserved even if their
        # exact column names later change.
        row.update(
            prefixed_row(
                capacity_structure[
                    family
                ],
                "pre2024_",
                exclude={
                    "family",
                },
            )
        )

        master_rows.append(
            row
        )

    fieldnames = (
        ordered_fieldnames(
            master_rows
        )
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            master_rows
        )

    print()
    print(
        "MASTER TABLE CREATED"
    )
    print(
        "===================="
    )

    print()
    print(
        f"Rows:    "
        f"{len(master_rows)}"
    )

    print(
        f"Columns: "
        f"{len(fieldnames)}"
    )

    print(
        f"Output:  "
        f"{OUTPUT_FILE}"
    )

    print()
    print(
        "CORE RESULTS"
    )
    print(
        "============"
    )

    print()
    print(
        f"{'Family':15}"
        f"{'Ext ID':>8}"
        f"{'Reach':>8}"
        f"{'Top5':>8}"
        f"{'Conv':>8}"
        f"{'Sp CT':>8}"
        f"{'No CT':>8}"
        f"{'DirRes':>9}"
        f"{'2StRes':>9}"
    )

    print(
        "-" * 81
    )

    for row in master_rows:
        print(
            f"{row['family']:15}"
            f"{row['external_id_rate'] * 100:7.1f}%"
            f"{row['stage1a_raw_reach_rate'] * 100:7.1f}%"
            f"{row['stage1a_top5_reach_rate'] * 100:7.1f}%"
            f"{row['stage1b_raw_conversion_rate'] * 100:7.1f}%"
            f"{row['community_species_rate'] * 100:7.1f}%"
            f"{row['no_community_taxon_rate'] * 100:7.1f}%"
            f"{row['nested_direct_residual'] * 100:+8.1f}"
            f"{row['nested_two_stage_residual'] * 100:+8.1f}"
        )

    print()
    print(
        "VALIDATION CHECKS"
    )
    print(
        "================="
    )

    total_external = sum(
        row[
            "external_id_count"
        ]
        for row in master_rows
    )

    total_raw_reach = sum(
        row[
            "stage1a_raw_reach_count"
        ]
        for row in master_rows
    )

    total_top5_reach = sum(
        row[
            "stage1a_top5_reach_count"
        ]
        for row in master_rows
    )

    print()
    print(
        f"External IDs: "
        f"{total_external}/9000 "
        f"({percent(
            total_external,
            9000
        ):.1f}%)"
    )

    print(
        f"Raw review-based reach: "
        f"{total_raw_reach}/9000 "
        f"({percent(
            total_raw_reach,
            9000
        ):.1f}%)"
    )

    print(
        f"Top-5 sensitivity reach: "
        f"{total_top5_reach}/9000 "
        f"({percent(
            total_top5_reach,
            9000
        ):.1f}%)"
    )

    print()
    print(
        "Stage 2 rank columns detected:"
    )

    rank_columns = sorted(
        {
            row[
                "stage2_rank_column"
            ]
            for row in master_rows
        }
    )

    for column in rank_columns:
        print(
            f"  {column}"
        )

    print()
    print(
        "Master table is now the "
        "preferred family-level source "
        "for subsequent analysis."
    )


if __name__ == "__main__":
    main()