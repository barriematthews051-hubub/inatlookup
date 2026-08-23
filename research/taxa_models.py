import csv
import os
import warnings
from collections import Counter

import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import (
    StratifiedKFold,
    cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)


DATA_DIR = "research/data"

TAXA = [
    "Syrphidae",
    "Asilidae",
    "Geometridae",
    "Nymphalidae",
    "Staphylinidae",
    "Asteraceae",
]


def slugify(text):
    return text.strip().lower()


def load_all_analysis():
    rows = []

    for taxon in TAXA:
        filename = os.path.join(
            DATA_DIR,
            f"{slugify(taxon)}_pilot_500_analysis.csv",
        )

        if not os.path.exists(filename):
            raise RuntimeError(
                f"Missing analysis file: {filename}"
            )

        with open(
            filename,
            "r",
            encoding="utf-8",
        ) as f:
            reader = csv.DictReader(f)

            for row in reader:
                row["family"] = taxon
                rows.append(row)

    return rows


def to_int(value, default=0):
    if value in (
        None,
        "",
    ):
        return default

    return int(value)


def to_float(value):
    if value in (
        None,
        "",
    ):
        return np.nan

    return float(value)


def photo_group(value):
    count = to_int(value)

    if count <= 1:
        return "1_or_less"

    if count == 2:
        return "2"

    if count == 3:
        return "3"

    return "4_plus"


def owner_rank_group(rank):
    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    if not rank:
        return "none"

    return "higher"


def first_external_rank_group(rank):
    if rank == "species":
        return "species"

    if rank == "genus":
        return "genus"

    if not rank:
        return "none"

    return "higher"


def make_dataframe(rows):
    records = []

    for row in rows:
        external_count = to_int(
            row["external_history_count"]
        )

        first_experience = to_float(
            row[
                "first_external_prior_taxon_ids"
            ]
        )

        first_hours = to_float(
            row[
                "hours_post_to_first_external"
            ]
        )

        records.append(
            {
                "family":
                    row["family"],

                "external_id":
                    int(
                        external_count > 0
                    ),

                "species_ct":
                    int(
                        row[
                            "outcome_group"
                        ] == "species"
                    ),

                "photo_group":
                    photo_group(
                        row["photo_count"]
                    ),

                "project":
                    int(
                        to_int(
                            row[
                                "project_count"
                            ]
                        ) > 0
                    ),

                "owner_initial_rank":
                    owner_rank_group(
                        row[
                            "first_owner_rank"
                        ]
                    ),

                "first_external_rank":
                    first_external_rank_group(
                        row[
                            "first_external_rank"
                        ]
                    ),

                "first_external_hours":
                    first_hours,

                "first_external_experience":
                    first_experience,

                "log_first_external_experience":
                    (
                        np.log10(
                            first_experience + 1
                        )
                        if not np.isnan(
                            first_experience
                        )
                        else np.nan
                    ),
            }
        )

    return pd.DataFrame(
        records
    )


def print_category_diagnostics(
    title,
    df,
    columns,
):
    print()
    print(title)
    print(
        "=" * len(title)
    )

    for column in columns:
        print()
        print(
            f"{column}:"
        )

        counts = (
            df[column]
            .value_counts(
                dropna=False
            )
            .sort_index()
        )

        total = len(df)

        for value, count in (
            counts.items()
        ):
            percentage = (
                100
                * count
                / total
            )

            print(
                f"  {str(value):<20}"
                f"{count:>5}"
                f"  ({percentage:>5.1f}%)"
            )

        categories = sorted(
            str(value)
            for value in
            df[column]
            .dropna()
            .unique()
        )

        if categories:
            print(
                "  Regression reference:"
                f" {categories[0]}"
            )


def build_model(
    categorical_columns,
    numeric_columns,
):
    transformer = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(
                    drop="first",
                    handle_unknown="ignore",
                ),
                categorical_columns,
            ),
            (
                "numeric",
                StandardScaler(),
                numeric_columns,
            ),
        ],
        remainder="drop",
    )

    model = LogisticRegression(
        max_iter=5000,
        solver="lbfgs",
    )

    return Pipeline(
        steps=[
            (
                "preprocess",
                transformer,
            ),
            (
                "model",
                model,
            ),
        ]
    )


def evaluate_model(
    title,
    pipeline,
    X,
    y,
):
    pipeline.fit(
        X,
        y
    )

    predictions = (
        pipeline.predict(
            X
        )
    )

    probabilities = (
        pipeline.predict_proba(
            X
        )[:, 1]
    )

    print()
    print(title)
    print(
        "=" * len(title)
    )

    print(
        "Observations:",
        len(y)
    )

    print(
        "Positive outcome:",
        int(y.sum()),
        f"({100 * y.mean():.1f}%)",
    )

    print(
        "Accuracy:",
        round(
            accuracy_score(
                y,
                predictions,
            ),
            3,
        ),
    )

    print(
        "Balanced accuracy:",
        round(
            balanced_accuracy_score(
                y,
                predictions,
            ),
            3,
        ),
    )

    print(
        "ROC AUC:",
        round(
            roc_auc_score(
                y,
                probabilities,
            ),
            3,
        ),
    )

    print(
        "Confusion matrix:"
    )

    print(
        confusion_matrix(
            y,
            predictions,
        )
    )

    return pipeline




def cross_validate_model(
    title,
    pipeline,
    X,
    y,
):
    cv = StratifiedKFold(
        n_splits=5,
        shuffle=True,
        random_state=49995,
    )

    scores = cross_validate(
        pipeline,
        X,
        y,
        cv=cv,
        scoring={
            "accuracy":
                "accuracy",

            "balanced_accuracy":
                "balanced_accuracy",

            "roc_auc":
                "roc_auc",
        },
        n_jobs=None,
    )

    print()
    print(title)
    print(
        "=" * len(title)
    )

    for metric in (
        "accuracy",
        "balanced_accuracy",
        "roc_auc",
    ):
        values = scores[
            f"test_{metric}"
        ]

        print(
            f"{metric:<20}"
            f"mean={values.mean():.3f}  "
            f"sd={values.std():.3f}"
        )




def leave_one_family_out(
    title,
    categorical_columns,
    numeric_columns,
    X,
    y,
    families,
):
    print()
    print(title)
    print(
        "=" * len(title)
    )

    print()

    header = (
        f"{'Held-out family':<18}"
        f"{'N':>7}"
        f"{'Positive':>11}"
        f"{'Bal acc':>11}"
        f"{'ROC AUC':>11}"
    )

    print(header)
    print(
        "-" * len(header)
    )

    results = []

    for family in TAXA:
        test_mask = (
            families
            == family
        )

        train_mask = ~test_mask

        X_train = X.loc[
            train_mask
        ]

        y_train = y.loc[
            train_mask
        ]

        X_test = X.loc[
            test_mask
        ]

        y_test = y.loc[
            test_mask
        ]

        model = build_model(
            categorical_columns,
            numeric_columns,
        )




        model.fit(
            X_train,
            y_train,
        )

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=(
                    "Found unknown categories "
                    "in columns"
                ),
                category=UserWarning,
            )

            predictions = (
                model.predict(
                    X_test
                )
            )

            probabilities = (
                model.predict_proba(
                    X_test
                )[:, 1]
            )






        balanced = (
            balanced_accuracy_score(
                y_test,
                predictions,
            )
        )

        auc = (
            roc_auc_score(
                y_test,
                probabilities,
            )
        )

        positive_rate = (
            100
            * y_test.mean()
        )

        results.append(
            (
                balanced,
                auc,
            )
        )

        print(
            f"{family:<18}"
            f"{len(y_test):>7}"
            f"{positive_rate:>10.1f}%"
            f"{balanced:>11.3f}"
            f"{auc:>11.3f}"
        )

    print(
        "-" * len(header)
    )

    print(
        f"{'Mean':<18}"
        f"{'':>7}"
        f"{'':>11}"
        f"{np.mean([x[0] for x in results]):>11.3f}"
        f"{np.mean([x[1] for x in results]):>11.3f}"
    )





def print_coefficients(
    title,
    pipeline,
):
    preprocess = (
        pipeline.named_steps[
            "preprocess"
        ]
    )

    model = (
        pipeline.named_steps[
            "model"
        ]
    )

    names = (
        preprocess
        .get_feature_names_out()
    )

    coefficients = (
        model.coef_[0]
    )

    rows = []

    for name, coefficient in zip(
        names,
        coefficients,
    ):
        odds_ratio = np.exp(
            coefficient
        )

        clean_name = (
            name
            .replace(
                "categorical__",
                "",
            )
            .replace(
                "numeric__",
                "",
            )
        )

        rows.append(
            (
                clean_name,
                coefficient,
                odds_ratio,
            )
        )

    rows.sort(
        key=lambda item:
            abs(
                item[1]
            ),
        reverse=True,
    )

    print()
    print(title)
    print(
        "=" * len(title)
    )

    print(
        f"{'Predictor':<45}"
        f"{'Coef':>10}"
        f"{'Odds ratio':>14}"
    )

    print(
        "-" * 69
    )

    for (
        name,
        coefficient,
        odds_ratio,
    ) in rows:

        print(
            f"{name:<45}"
            f"{coefficient:>10.3f}"
            f"{odds_ratio:>14.3f}"
        )


def print_family_raw_rates(df):
    print()
    print(
        "RAW FAMILY RATES"
    )

    print(
        "================"
    )

    print()

    header = (
        f"{'Family':<16}"
        f"{'N':>6}"
        f"{'External ID':>14}"
        f"{'Species CT':>14}"
        f"{'Species | external':>20}"
    )

    print(header)
    print(
        "-" * len(header)
    )

    for family in TAXA:
        group = df[
            df["family"]
            == family
        ]

        attended = group[
            group["external_id"]
            == 1
        ]

        external_rate = (
            100
            * group[
                "external_id"
            ].mean()
        )

        species_rate = (
            100
            * group[
                "species_ct"
            ].mean()
        )

        conditional_species = (
            100
            * attended[
                "species_ct"
            ].mean()
            if len(attended)
            else 0
        )

        print(
            f"{family:<16}"
            f"{len(group):>6}"
            f"{external_rate:>13.1f}%"
            f"{species_rate:>13.1f}%"
            f"{conditional_species:>19.1f}%"
        )




def print_owner_none_diagnostic(
    df
):
    subset = df[
        df["owner_initial_rank"]
        == "none"
    ]

    print()
    print(
        "OWNER INITIAL RANK = NONE"
    )
    print(
        "========================="
    )

    print(
        "Observations:",
        len(subset)
    )

    print(
        "Received external ID:",
        int(
            subset[
                "external_id"
            ].sum()
        ),
        f"({100 * subset['external_id'].mean():.1f}%)",
    )

    print()
    print(
        f"{'Family':<16}"
        f"{'N':>7}"
        f"{'External':>12}"
        f"{'Species CT':>14}"
    )

    print(
        "-" * 49
    )

    for family in TAXA:
        group = subset[
            subset["family"]
            == family
        ]

        if len(group) == 0:
            continue

        print(
            f"{family:<16}"
            f"{len(group):>7}"
            f"{int(group['external_id'].sum()):>12}"
            f"{int(group['species_ct'].sum()):>14}"
        )








def print_first_external_rank_rates(
    df
):
    print()
    print(
        "RAW SPECIES OUTCOME BY "
        "FIRST EXTERNAL RANK"
    )

    print(
        "=================================="
    )

    print()

    grouped = (
        df.groupby(
            "first_external_rank",
            dropna=False,
        )
    )

    rows = []

    for rank, group in grouped:
        n = len(group)

        species_count = int(
            group[
                "species_ct"
            ].sum()
        )

        species_rate = (
            100
            * group[
                "species_ct"
            ].mean()
        )

        rows.append(
            (
                str(rank),
                n,
                species_count,
                species_rate,
            )
        )

    rows.sort(
        key=lambda item:
            item[1],
        reverse=True,
    )

    print(
        f"{'First rank':<18}"
        f"{'N':>7}"
        f"{'Species CT':>14}"
        f"{'Rate':>10}"
    )

    print(
        "-" * 49
    )

    for (
        rank,
        n,
        species_count,
        species_rate,
    ) in rows:

        print(
            f"{rank:<18}"
            f"{n:>7}"
            f"{species_count:>14}"
            f"{species_rate:>9.1f}%"
        )






def main():
    rows = load_all_analysis()

    df = make_dataframe(
        rows
    )

    print(
        "Combined observations:",
        len(df)
    )

    print(
        "Families:",
        dict(
            Counter(
                df[
                    "family"
                ]
            )
        )
    )



    print_family_raw_rates(
        df
    )

    print_owner_none_diagnostic(
        df
    )

    print_category_diagnostics(
        "MODEL A CATEGORY DIAGNOSTICS",
        df,
        [
            "family",
            "photo_group",
            "project",
        ],
    )

    #
    # MODEL A    #
    # Question:
    # What predicts whether an observation
    # receives at least one external ID?
    #
    # All predictors are available before
    # the first external identification.
    #

    attention_columns = [
        "family",
        "photo_group",
        "project",
    ]

    attention_X = df[
        attention_columns
    ]

    attention_y = df[
        "external_id"
    ]

    attention_model = build_model(
        categorical_columns=[
            "family",
            "photo_group",
        ],
        numeric_columns=[
            "project",
        ],
    )

    attention_model = evaluate_model(
        "MODEL A - EXTERNAL ID RECEIVED",
        attention_model,
        attention_X,
        attention_y,
    )


    cross_validate_model(
        "MODEL A - 5-FOLD CROSS-VALIDATION",
        attention_model,
        attention_X,
        attention_y,
    )

    leave_one_family_out(
        "MODEL A - LEAVE-ONE-FAMILY-OUT",
        categorical_columns=[
            "family",
            "photo_group",
        ],
        numeric_columns=[
            "project",
        ],
        X=attention_X,
        y=attention_y,
        families=df[
            "family"
        ],
    )


    print_coefficients(
        "MODEL A COEFFICIENTS",
        attention_model,
    )


    #
    # MODEL B1
    #
    # Question:
    # Among observations that eventually
    # receive an external ID, what predicts
    # eventual species Community Taxon using
    # only information known BEFORE the first
    # external identification?
    #

    attended = df[
        df["external_id"]
        == 1
    ].copy()

    b1_columns = [
        "family",
        "photo_group",
        "project",
        "owner_initial_rank",
    ]

    b1_X = attended[
        b1_columns
    ]

    b1_y = attended[
        "species_ct"
    ]

    b1_model = build_model(
        categorical_columns=[
            "family",
            "photo_group",
            "owner_initial_rank",
        ],
        numeric_columns=[
            "project",
        ],
    )

    b1_model = evaluate_model(
        "MODEL B1 - SPECIES CT BEFORE FIRST EXTERNAL ID",
        b1_model,
        b1_X,
        b1_y,
    )

    cross_validate_model(
        "MODEL B1 - 5-FOLD CROSS-VALIDATION",
        b1_model,
        b1_X,
        b1_y,
    )

    leave_one_family_out(
        "MODEL B1 - LEAVE-ONE-FAMILY-OUT",
        categorical_columns=[
            "family",
            "photo_group",
            "owner_initial_rank",
        ],
        numeric_columns=[
            "project",
        ],
        X=b1_X,
        y=b1_y,
        families=attended[
            "family"
        ],
    )

    print_coefficients(
        "MODEL B1 COEFFICIENTS",
        b1_model,
    )

    #
    # MODEL B2
    #
    # Question:
    # Once the first external ID has occurred,
    # how much additional predictive information
    # do first rank, response time and identifier
    # experience provide?


    attended = df[
        df["external_id"]
        == 1
    ].copy()

    print_category_diagnostics(
        "MODEL B2 CATEGORY DIAGNOSTICS",
        attended,
        [
            "family",
            "photo_group",
            "project",
            "owner_initial_rank",
            "first_external_rank",
        ],
    )

    print_first_external_rank_rates(
        attended
    )


    resolution_columns = [
        "family",
        "photo_group",
        "project",
        "owner_initial_rank",
        "first_external_rank",
        "first_external_hours",
        "log_first_external_experience",
    ]

    resolution_df = attended[
        resolution_columns
        + [
            "species_ct",
        ]
    ].dropna()

    resolution_X = (
        resolution_df[
            resolution_columns
        ]
    )

    resolution_y = (
        resolution_df[
            "species_ct"
        ]
    )

    resolution_model = build_model(
        categorical_columns=[
            "family",
            "photo_group",
            "owner_initial_rank",
            "first_external_rank",
        ],
        numeric_columns=[
            "project",
            "first_external_hours",
            "log_first_external_experience",
        ],
    )


    resolution_model = evaluate_model(
        "MODEL B2 - SPECIES CT AFTER FIRST EXTERNAL ID",
        resolution_model,
        resolution_X,
        resolution_y,
    )

    cross_validate_model(
        "MODEL B2 - 5-FOLD CROSS-VALIDATION",
        resolution_model,
        resolution_X,
        resolution_y,
    )

    leave_one_family_out(
        "MODEL B2 - LEAVE-ONE-FAMILY-OUT",
        categorical_columns=[
            "family",
            "photo_group",
            "owner_initial_rank",
            "first_external_rank",
        ],
        numeric_columns=[
            "project",
            "first_external_hours",
            "log_first_external_experience",
        ],
        X=resolution_X,
        y=resolution_y,
        families=attended.loc[
            resolution_df.index,
            "family",
        ],
    )

    print_coefficients(
        "MODEL B2 COEFFICIENTS",
        resolution_model,
    )

if __name__ == "__main__":
    main()