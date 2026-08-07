import re
import requests

from lookup import InatLookup
from version import VERSION

#BIN_FILE = "inatlookup.bin"
BIN_FILE = r"C:\Users\Barrie\inatlookup\data\inatlookup.bin"

lookup = InatLookup(BIN_FILE)

print(f"inatlookup program v{VERSION}")
print(f"Index format v{lookup.version}")
print(f"Records : {lookup.records:,}")
print()

while True:

    print()

    text = input("Photo URL or Photo ID (blank to quit): ").strip()

    if not text:
        break

    # User entered just a photo ID
    if text.isdigit():
        photo_id = int(text)

    else:
        # Look for /photos/<number>/ anywhere in the text
        m = re.search(r"/photos/(\d+)", text)

        if not m:
            print("Couldn't find a photo ID.")
            continue

        photo_id = int(m.group(1))

    print("Photo ID:", photo_id)

    obs_uuid = lookup.find(photo_id)

    if obs_uuid is None:
        print("Photo not found in index.")
        continue

    print("Observation UUID:", obs_uuid)

    try:

        r = requests.get(
            "https://api.inaturalist.org/v1/observations",
            params={
                "uuid": obs_uuid,
                "per_page": 1
            },
            timeout=30
        )

        r.raise_for_status()

        results = r.json()["results"]

        if results:

            obs = results[0]

            print()
            print("Observation ID :", obs["id"])
            print("Observation URL:", obs["uri"])

        else:

            print("UUID found, but no observation returned.")

    except Exception as e:

        print("API lookup failed.")
        print("Observation UUID:", obs_uuid)

lookup.close()