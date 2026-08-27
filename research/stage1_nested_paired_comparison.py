import numpy as np

from stage1_nested_validation import (
    load_rows,
    external_counts,
    choose_direct_model,
    choose_two_stage_model,
    predict_direct_outer,
    predict_two_stage_outer,
)


BOOTSTRAP_SAMPLES = 100000
RANDOM_SEED = 20260827


def main():
    rows = load_rows()

    observed = (
        external_counts(rows)
        / 500.0
    )

    direct_predictions = np.zeros(
        len(rows)
    )

    two_stage_predictions = np.zeros(
        len(rows)
    )

    for held_out in range(
        len(rows)
    ):
        training_rows = [
            row
            for index, row in enumerate(rows)
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

        direct_predictions[
            held_out
        ] = predict_direct_outer(
            training_rows,
            test_row,
            direct_model,
        )

        two_stage_predictions[
            held_out
        ] = predict_two_stage_outer(
            training_rows,
            test_row,
            reach_model,
            conversion_model,
        )

    direct_errors = (
        observed
        - direct_predictions
    )

    two_errors = (
        observed
        - two_stage_predictions
    )

    direct_abs = np.abs(
        direct_errors
    )

    two_abs = np.abs(
        two_errors
    )

    paired_abs_difference = (
        two_abs
        - direct_abs
    )

    direct_sq = (
        direct_errors ** 2
    )

    two_sq = (
        two_errors ** 2
    )

    two_wins = np.sum(
        two_abs
        < direct_abs
    )

    direct_wins = np.sum(
        direct_abs
        < two_abs
    )

    ties = np.sum(
        np.isclose(
            direct_abs,
            two_abs,
        )
    )

    print()
    print(
        "NESTED DIRECT VS TWO-STAGE "
        "PAIRED COMPARISON"
    )
    print(
        "=================================="
    )

    print()
    print(
        "Negative paired difference means "
        "the two-stage model has lower "
        "absolute error."
    )

    print()
    print(
        f"Two-stage wins: "
        f"{two_wins}/18"
    )

    print(
        f"Direct wins:    "
        f"{direct_wins}/18"
    )

    print(
        f"Ties:           "
        f"{ties}/18"
    )

    print()
    print(
        "ABSOLUTE ERROR"
    )
    print(
        "--------------"
    )

    print(
        f"Direct mean: "
        f"{np.mean(direct_abs) * 100:.3f} pp"
    )

    print(
        f"Two-stage mean: "
        f"{np.mean(two_abs) * 100:.3f} pp"
    )

    print(
        f"Mean paired difference "
        f"(two - direct): "
        f"{np.mean(paired_abs_difference) * 100:+.3f} pp"
    )

    print(
        f"Median paired difference: "
        f"{np.median(paired_abs_difference) * 100:+.3f} pp"
    )

    print()
    print(
        "LARGE ERRORS"
    )
    print(
        "------------"
    )

    for threshold in [
        0.05,
        0.10,
        0.15,
    ]:
        direct_large = np.sum(
            direct_abs
            >= threshold
        )

        two_large = np.sum(
            two_abs
            >= threshold
        )

        print(
            f">= {threshold * 100:.0f} pp: "
            f"direct={direct_large}, "
            f"two-stage={two_large}"
        )

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    sample_indices = rng.integers(
        0,
        len(rows),
        size=(
            BOOTSTRAP_SAMPLES,
            len(rows),
        ),
    )

    boot_mae_difference = np.mean(
        paired_abs_difference[
            sample_indices
        ],
        axis=1,
    )

    lower, upper = np.percentile(
        boot_mae_difference,
        [
            2.5,
            97.5,
        ],
    )

    print()
    print(
        "PAIRED BOOTSTRAP"
    )
    print(
        "----------------"
    )

    print(
        f"MAE difference 95% CI "
        f"(two - direct): "
        f"{lower * 100:+.3f} to "
        f"{upper * 100:+.3f} pp"
    )

    boot_direct_rmse = np.sqrt(
        np.mean(
            direct_sq[
                sample_indices
            ],
            axis=1,
        )
    )

    boot_two_rmse = np.sqrt(
        np.mean(
            two_sq[
                sample_indices
            ],
            axis=1,
        )
    )

    boot_rmse_difference = (
        boot_two_rmse
        - boot_direct_rmse
    )

    lower_rmse, upper_rmse = (
        np.percentile(
            boot_rmse_difference,
            [
                2.5,
                97.5,
            ],
        )
    )

    print(
        f"RMSE difference 95% CI "
        f"(two - direct): "
        f"{lower_rmse * 100:+.3f} to "
        f"{upper_rmse * 100:+.3f} pp"
    )

    print()
    print(
        "FAMILY-BY-FAMILY"
    )
    print(
        "----------------"
    )

    comparison = []

    for (
        row,
        actual,
        direct_prediction,
        two_prediction,
    ) in zip(
        rows,
        observed,
        direct_predictions,
        two_stage_predictions,
    ):
        direct_error = abs(
            actual
            - direct_prediction
        )

        two_error = abs(
            actual
            - two_prediction
        )

        comparison.append(
            (
                two_error
                - direct_error,
                row["family"],
                actual,
                direct_prediction,
                two_prediction,
                direct_error,
                two_error,
            )
        )

    comparison.sort()

    print()
    print(
        "Most improved by two-stage:"
    )

    for (
        difference,
        family,
        actual,
        direct_prediction,
        two_prediction,
        direct_error,
        two_error,
    ) in comparison[:5]:
        print(
            f"  {family:15} "
            f"direct error="
            f"{direct_error * 100:5.1f} pp  "
            f"two-stage error="
            f"{two_error * 100:5.1f} pp  "
            f"change="
            f"{difference * 100:+5.1f} pp"
        )

    print()
    print(
        "Most worsened by two-stage:"
    )

    for (
        difference,
        family,
        actual,
        direct_prediction,
        two_prediction,
        direct_error,
        two_error,
    ) in comparison[-5:][::-1]:
        print(
            f"  {family:15} "
            f"direct error="
            f"{direct_error * 100:5.1f} pp  "
            f"two-stage error="
            f"{two_error * 100:5.1f} pp  "
            f"change="
            f"{difference * 100:+5.1f} pp"
        )


if __name__ == "__main__":
    main()