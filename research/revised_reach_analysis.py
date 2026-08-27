import json
import os


CACHE_FILE = os.path.join(
    "research",
    "cache",
    "public_interactions_9000.json",
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


def load_records():
    with open(
        CACHE_FILE,
        "r",
        encoding="utf-8",
    ) as handle:
        data = json.load(handle)

    return [
        record
        for record
        in data["records"].values()
        if record.get("status") == "ok"
    ]


def user_set(
    row,
    field,
):
    return {
        int(value)
        for value
        in row.get(
            field,
            [],
        )
    }


def measures(row):
    external = bool(
        row[
            "external_id_present"
        ]
    )

    reviewers = user_set(
        row,
        "reviewer_no_id_user_ids",
    )

    commenters = user_set(
        row,
        "commenter_no_id_user_ids",
    )

    annotators = user_set(
        row,
        "annotator_no_id_user_ids",
    )

    dqa = user_set(
        row,
        "dqa_no_id_user_ids",
    )

    fields = user_set(
        row,
        "field_no_id_user_ids",
    )

    faves = user_set(
        row,
        "fave_no_id_user_ids",
    )

    review_reach = (
        external
        or bool(reviewers)
    )

    conservative_reach = (
        external
        or bool(
            reviewers
            | commenters
        )
    )

    broad_reach = (
        external
        or bool(
            reviewers
            | commenters
            | annotators
            | dqa
            | fields
            | faves
        )
    )

    metadata_only = (
        not conservative_reach
        and bool(
            annotators
            | dqa
            | fields
            | faves
        )
    )

    comment_only_new = (
        not external
        and not reviewers
        and bool(commenters)
    )

    return {
        "external":
            external,

        "review_reach":
            review_reach,

        "conservative_reach":
            conservative_reach,

        "broad_reach":
            broad_reach,

        "metadata_only":
            metadata_only,

        "comment_only_new":
            comment_only_new,
    }


def summarize(
    family,
    common_name,
    rows,
):
    results = [
        measures(row)
        for row in rows
    ]

    n = len(results)

    external = sum(
        item["external"]
        for item in results
    )

    review_reach = sum(
        item["review_reach"]
        for item in results
    )

    conservative = sum(
        item[
            "conservative_reach"
        ]
        for item in results
    )

    broad = sum(
        item["broad_reach"]
        for item in results
    )

    metadata_only = sum(
        item["metadata_only"]
        for item in results
    )

    comment_only = sum(
        item["comment_only_new"]
        for item in results
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

    print(
        f"  External ID: "
        f"{external}/{n} "
        f"({percent(external, n):.1f}%)"
    )

    print(
        f"  Review-based reach: "
        f"{review_reach}/{n} "
        f"({percent(review_reach, n):.1f}%)"
    )

    print(
        f"  Conservative reach "
        f"(ID/review/comment): "
        f"{conservative}/{n} "
        f"({percent(conservative, n):.1f}%)"
    )

    print(
        f"  Old broad reach: "
        f"{broad}/{n} "
        f"({percent(broad, n):.1f}%)"
    )

    print(
        f"  Metadata-only uplift: "
        f"{metadata_only}/{n} "
        f"({percent(metadata_only, n):.1f} pp)"
    )

    print(
        f"  Comment-only additions "
        f"beyond ID/review: "
        f"{comment_only}/{n}"
    )

    if conservative:
        print(
            f"  ID conversion among "
            f"conservatively reached: "
            f"{external}/{conservative} "
            f"({percent(
                external,
                conservative
            ):.1f}%)"
        )


def main():
    records = load_records()

    print()
    print(
        "REVISED IDENTIFICATION-REACH "
        "ANALYSIS"
    )
    print(
        "================================"
    )

    print()
    print(
        "Primary conservative reach = "
        "external ID OR reviewed-without-ID "
        "OR comment-without-ID."
    )

    print()
    print(
        "Annotations, DQA, observation "
        "fields and favourites are treated "
        "as metadata/curation engagement, "
        "not primary ID-oriented reach."
    )

    for family, common_name in FAMILIES:
        rows = [
            row
            for row in records
            if row["family"] == family
        ]

        summarize(
            family,
            common_name,
            rows,
        )

    print()
    print(
        "ALL 18 FAMILIES"
    )
    print(
        "==============="
    )

    summarize(
        "ALL",
        "18 families",
        records,
    )


if __name__ == "__main__":
    main()