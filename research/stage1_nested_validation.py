import csv
import math
import os
from collections import Counter

import numpy as np

from family_stage1_model_comparison import (
    fit_binomial,
    predict,
    standardize,
)


INPUT_FILE = os.path.join(
    "research",
    "data",
    "family_stage1_decomposition.csv",
)


PREDICTORS = {
    "Capacity": [
        "external_capacity",
    ],

    "Identifiability": [
        "identifiability_score",
    ],

    "Workload": [
        "log_workload",
    ],

    "Capacity + Ident": [
        "external_capacity",
        "identifiability_score",
    ],

    "Capacity + Workload": [
        "external_capacity",
        "log_workload",
    ],

    "Ident + Workload": [
        "identifiability_score",
        "log_workload",
    ],

    "All three": [
        "external_capacity",
        "identifiability_score",
        "log_workload",
    ],
}


DIRECT_CANDIDATES = [
    "Capacity",
    "Identifiability",
    "Workload",
    "Capacity + Ident",
    "Capacity + Workload",
    "Ident + Workload",
    "All three",
]


TWO_STAGE_CANDIDATES = [
    (
        "Capacity -> Capacity",
        "Capacity",
        "Capacity",
    ),

    (
        "Capacity -> Capacity+Ident",
        "Capacity",
        "Capacity + Ident",
    ),

    (
        "Cap+Workload -> Capacity",
        "Capacity + Workload",
        "Capacity",
    ),

    (
        "Cap+Workload -> Cap+Ident",
        "Capacity + Workload",
        "Capacity + Ident",
    ),

    (
        "All three -> All three",
        "All three",
        "All three",
    ),
]


def load_rows():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(
            csv.DictReader(handle)
        )

    if len(rows) != 18:
        raise ValueError(
            "Expected 18 families, "
            f"found {len(rows)}"
        )

    return rows


def make_x(
    rows,
    model_name,
):
    fields = PREDICTORS[
        model_name
    ]

    return np.asarray(
        [
            [
                float(
                    row[field]
                )
                for field in fields
            ]
            for row in rows
        ],
        dtype=float,
    )


def external_counts(rows):
    return np.asarray(
        [
            float(
                row[
                    "external_id_count"
                ]
            )
            for row in rows
        ],
        dtype=float,
    )


def reach_counts(rows):
    return np.asarray(
        [
            float(
                row[
                    "raw_reach_count"
                ]
            )
            for row in rows
        ],
        dtype=float,
    )


def fit_predict_one(
    x_train,
    x_test,
    successes,
    trials,
):
    (
        x_train_std,
        mean,
        sd,
    ) = standardize(
        x_train
    )

    x_test_std = (
        x_test
        - mean
    ) / sd

    beta = fit_binomial(
        x_train_std,
        successes,
        trials,
    )

    return predict(
        beta,
        x_test_std,
    )[0]


def direct_inner_predictions(
    rows,
    model_name,
):
    x = make_x(
        rows,
        model_name,
    )

    successes = external_counts(
        rows
    )

    trials = np.full(
        len(rows),
        500.0,
    )

    predictions = np.zeros(
        len(rows)
    )

    for held_out in range(
        len(rows)
    ):
        mask = np.ones(
            len(rows),
            dtype=bool,
        )

        mask[
            held_out
        ] = False

        predictions[
            held_out
        ] = fit_predict_one(
            x[mask],
            x[[held_out]],
            successes[mask],
            trials[mask],
        )

    return predictions


def two_stage_inner_predictions(
    rows,
    reach_model,
    conversion_model,
):
    reach_x = make_x(
        rows,
        reach_model,
    )

    conversion_x = make_x(
        rows,
        conversion_model,
    )

    external = external_counts(
        rows
    )

    reach = reach_counts(
        rows
    )

    reach_trials = np.full(
        len(rows),
        500.0,
    )

    predictions = np.zeros(
        len(rows)
    )

    for held_out in range(
        len(rows)
    ):
        mask = np.ones(
            len(rows),
            dtype=bool,
        )

        mask[
            held_out
        ] = False

        predicted_reach = (
            fit_predict_one(
                reach_x[mask],
                reach_x[[held_out]],
                reach[mask],
                reach_trials[mask],
            )
        )

        predicted_conversion = (
            fit_predict_one(
                conversion_x[mask],
                conversion_x[
                    [held_out]
                ],
                external[mask],
                reach[mask],
            )
        )

        predictions[
            held_out
        ] = (
            predicted_reach
            * predicted_conversion
        )

    return predictions


def mae(
    observed,
    predicted,
):
    return np.mean(
        np.abs(
            observed
            - predicted
        )
    )


def choose_direct_model(
    training_rows,
):
    observed = (
        external_counts(
            training_rows
        )
        / 500.0
    )

    results = []

    for model_name in (
        DIRECT_CANDIDATES
    ):
        predicted = (
            direct_inner_predictions(
                training_rows,
                model_name,
            )
        )

        score = mae(
            observed,
            predicted,
        )

        results.append(
            (
                score,
                model_name,
            )
        )

    results.sort(
        key=lambda item: (
            item[0],
            len(
                PREDICTORS[
                    item[1]
                ]
            ),
            item[1],
        )
    )

    return results[0]


def choose_two_stage_model(
    training_rows,
):
    observed = (
        external_counts(
            training_rows
        )
        / 500.0
    )

    results = []

    for (
        label,
        reach_model,
        conversion_model,
    ) in TWO_STAGE_CANDIDATES:
        predicted = (
            two_stage_inner_predictions(
                training_rows,
                reach_model,
                conversion_model,
            )
        )

        score = mae(
            observed,
            predicted,
        )

        results.append(
            (
                score,
                label,
                reach_model,
                conversion_model,
            )
        )

    results.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return results[0]


def predict_direct_outer(
    training_rows,
    test_row,
    model_name,
):
    x_train = make_x(
        training_rows,
        model_name,
    )

    x_test = make_x(
        [test_row],
        model_name,
    )

    successes = external_counts(
        training_rows
    )

    trials = np.full(
        len(training_rows),
        500.0,
    )

    return fit_predict_one(
        x_train,
        x_test,
        successes,
        trials,
    )


def predict_two_stage_outer(
    training_rows,
    test_row,
    reach_model,
    conversion_model,
):
    reach_x_train = make_x(
        training_rows,
        reach_model,
    )

    reach_x_test = make_x(
        [test_row],
        reach_model,
    )

    conversion_x_train = make_x(
        training_rows,
        conversion_model,
    )

    conversion_x_test = make_x(
        [test_row],
        conversion_model,
    )

    external = external_counts(
        training_rows
    )

    reach = reach_counts(
        training_rows
    )

    reach_trials = np.full(
        len(training_rows),
        500.0,
    )

    predicted_reach = (
        fit_predict_one(
            reach_x_train,
            reach_x_test,
            reach,
            reach_trials,
        )
    )

    predicted_conversion = (
        fit_predict_one(
            conversion_x_train,
            conversion_x_test,
            external,
            reach,
        )
    )

    return (
        predicted_reach
        * predicted_conversion
    )


def metrics(
    observed,
    predicted,
):
    errors = (
        observed
        - predicted
    )

    mae_value = np.mean(
        np.abs(errors)
    )

    rmse = math.sqrt(
        np.mean(
            errors ** 2
        )
    )

    denominator = np.sum(
        (
            observed
            - np.mean(
                observed
            )
        ) ** 2
    )

    r2 = (
        1.0
        - np.sum(
            errors ** 2
        )
        / denominator
    )

    bias = np.mean(
        predicted
        - observed
    )

    return (
        mae_value,
        rmse,
        r2,
        bias,
    )


def print_metrics(
    label,
    observed,
    predicted,
):
    (
        mae_value,
        rmse,
        r2,
        bias,
    ) = metrics(
        observed,
        predicted,
    )

    print(
        f"{label:25}"
        f"{mae_value * 100:9.2f}"
        f"{rmse * 100:10.2f}"
        f"{r2:10.3f}"
        f"{bias * 100:9.2f}"
    )


def main():
    rows = load_rows()

    observed = (
        external_counts(
            rows
        )
        / 500.0
    )

    direct_predictions = (
        np.zeros(
            len(rows)
        )
    )

    two_stage_predictions = (
        np.zeros(
            len(rows)
        )
    )

    direct_choices = Counter()
    two_stage_choices = Counter()

    selection_rows = []

    print()
    print(
        "NESTED LEAVE-ONE-FAMILY-OUT "
        "VALIDATION"
    )

    print(
        "================================="
        "======"
    )

    print()
    print(
        "For each outer held-out family, "
        "model architecture is selected "
        "using only the other 17 families."
    )

    for held_out in range(
        len(rows)
    ):
        training_rows = [
            row
            for index, row
            in enumerate(rows)
            if index != held_out
        ]

        test_row = rows[
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

        direct_choices[
            direct_model
        ] += 1

        two_stage_choices[
            two_label
        ] += 1

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

        direct_predictions[
            held_out
        ] = direct_prediction

        two_stage_predictions[
            held_out
        ] = two_prediction

        selection_rows.append(
            (
                test_row["family"],
                direct_model,
                direct_inner_mae,
                two_label,
                two_inner_mae,
                observed[
                    held_out
                ],
                direct_prediction,
                two_prediction,
            )
        )

    print()
    print(
        "OUTER VALIDATION PERFORMANCE"
    )

    print(
        "============================"
    )

    print()
    print(
        f"{'Method':25}"
        f"{'MAE pp':>9}"
        f"{'RMSE pp':>10}"
        f"{'LOFO R2':>10}"
        f"{'Bias pp':>9}"
    )

    print(
        "-" * 63
    )

    print_metrics(
        "Nested direct",
        observed,
        direct_predictions,
    )

    print_metrics(
        "Nested two-stage",
        observed,
        two_stage_predictions,
    )

    print()
    print(
        "DIRECT MODEL SELECTIONS"
    )

    print(
        "======================="
    )

    for (
        model_name,
        count,
    ) in direct_choices.most_common():
        print(
            f"  {model_name:23} "
            f"{count}/18"
        )

    print()
    print(
        "TWO-STAGE MODEL SELECTIONS"
    )

    print(
        "=========================="
    )

    for (
        model_name,
        count,
    ) in two_stage_choices.most_common():
        print(
            f"  {model_name:31} "
            f"{count}/18"
        )

    print()
    print(
        "OUTER-FOLD DETAILS"
    )

    print(
        "=================="
    )

    for (
        family,
        direct_model,
        direct_inner_mae,
        two_label,
        two_inner_mae,
        actual,
        direct_prediction,
        two_prediction,
    ) in selection_rows:
        print()
        print(
            family
        )

        print(
            f"  Direct selected: "
            f"{direct_model}"
        )

        print(
            f"    Inner MAE: "
            f"{direct_inner_mae * 100:.2f} pp"
        )

        print(
            f"  Two-stage selected: "
            f"{two_label}"
        )

        print(
            f"    Inner MAE: "
            f"{two_inner_mae * 100:.2f} pp"
        )

        print(
            f"  Actual external-ID rate: "
            f"{actual * 100:.1f}%"
        )

        print(
            f"  Direct prediction: "
            f"{direct_prediction * 100:.1f}% "
            f"(resid "
            f"{(actual - direct_prediction) * 100:+.1f} pp)"
        )

        print(
            f"  Two-stage prediction: "
            f"{two_prediction * 100:.1f}% "
            f"(resid "
            f"{(actual - two_prediction) * 100:+.1f} pp)"
        )


if __name__ == "__main__":
    main()