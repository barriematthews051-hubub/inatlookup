import csv
import time

import requests


INPUT_FILE = "research/syrphidae_pilot_500.csv"

OUTPUT_FILE = (
    "research/"
    "syrphidae_pilot_500_enriched.csv"
)

TAXA_API_URL = (
    "https://api.inaturalist.org/"
    "v1/taxa"
)

TAXA_PER_BATCH = 100
REQUEST_DELAY = 1.0


def load_rows():
    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        return list(
            csv.DictReader(f)
        )


def api_get(params):
    response = requests.get(
        TAXA_API_URL,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    time.sleep(REQUEST_DELAY)

    return data


def fetch_taxa(taxon_ids):
    taxa = {}

    batches = [
        taxon_ids[
            i:i + TAXA_PER_BATCH
        ]
        for i in range(
            0,
            len(taxon_ids),
            TAXA_PER_BATCH
        )
    ]

    print(
        "Unique community taxa:",
        len(taxon_ids)
    )

    print(
        "Taxon batches:",
        len(batches)
    )

    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        ids_text = ",".join(
            str(x)
            for x in batch
        )

        print(
            f"Fetching taxon batch "
            f"{batch_number}/"
            f"{len(batches)}"
        )

        data = api_get(
            {
                "id": ids_text,
                "per_page": 200,
            }
        )

        print(
            "  Returned:",
            len(data["results"])
        )

        for taxon in data["results"]:

            taxa[
                str(taxon["id"])
            ] = taxon

    return taxa


def main():
    rows = load_rows()

    print(
        "Observations:",
        len(rows)
    )

    community_taxon_ids = sorted(
        {
            int(row["community_taxon_id"])
            for row in rows
            if row["community_taxon_id"]
        }
    )

    taxa = fetch_taxa(
        community_taxon_ids
    )

    unresolved = 0
    no_community_taxon = 0

    enriched_rows = []

    for row in rows:

        community_taxon_id = (
            row["community_taxon_id"]
        )

        if not community_taxon_id:

            no_community_taxon += 1

            row[
                "community_taxon_name"
            ] = ""

            row[
                "community_taxon_rank"
            ] = ""

        else:

            taxon = taxa.get(
                community_taxon_id
            )

            if taxon is None:

                unresolved += 1

                row[
                    "community_taxon_name"
                ] = ""

                row[
                    "community_taxon_rank"
                ] = ""

            else:

                row[
                    "community_taxon_name"
                ] = taxon.get(
                    "name",
                    ""
                )

                row[
                    "community_taxon_rank"
                ] = taxon.get(
                    "rank",
                    ""
                )

        enriched_rows.append(
            row
        )

    fieldnames = list(
        enriched_rows[0].keys()
    )

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(
            enriched_rows
        )

    print()
    print(
        "Enrichment complete"
    )
    print(
        "Rows written:",
        len(enriched_rows)
    )
    print(
        "No community taxon:",
        no_community_taxon
    )
    print(
        "Unresolved taxon IDs:",
        unresolved
    )
    print(
        "Output:",
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()