import csv
import requests
import time


SAMPLE_FILE = "research/data/asilidae_pilot_500.csv"

VIEWER_ID = 541014
VIEWER_LOGIN = "myelaphus"

BATCH_SIZE = 100


with open(
    SAMPLE_FILE,
    "r",
    encoding="utf-8"
) as f:
    rows = list(csv.DictReader(f))


sample_ids = [
    row["observation_id"]
    for row in rows
]


reviewed_without_id = set()


for start in range(
    0,
    len(sample_ids),
    BATCH_SIZE
):

    batch = sample_ids[
        start:start + BATCH_SIZE
    ]

    params = {
        "id": ",".join(batch),
        "viewer_id": VIEWER_ID,
        "reviewed": "true",
        "without_ident_user_id": VIEWER_LOGIN,
        "quality_grade": "any",
        "per_page": 200,
    }

    response = requests.get(
        "https://api.inaturalist.org/v1/observations",
        params=params,
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    print(
        f"Batch {start // BATCH_SIZE + 1}:",
        data["total_results"],
        "reviewed without ID"
    )

    for observation in data[
        "results"
    ]:
        reviewed_without_id.add(
            str(observation["id"])
        )

    time.sleep(1)


print()
print(
    "Sample observations:",
    len(sample_ids)
)

print(
    "Reviewed without ID:",
    len(reviewed_without_id)
)

print(
    "Percentage:",
    round(
        100
        * len(reviewed_without_id)
        / len(sample_ids),
        1
    ),
    "%"
)


output_file = (
    "research/data/"
    "asilidae_myelaphus_reviewed_without_id.csv"
)


with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "observation_id"
    ])

    for observation_id in sorted(
        reviewed_without_id,
        key=int
    ):
        writer.writerow([
            observation_id
        ])


print(
    "Output:",
    output_file
)