# iNatLookup

Fast reverse lookup for iNaturalist photos.

Given an iNaturalist photo ID or photo URL, iNatLookup finds the parent observation using a locally-built index of the iNaturalist Open Data photos table.

It can also optionally enrich batch results with observation details from the iNaturalist API.

## Why this exists

iNaturalist photo URLs contain a photo ID, but not directly the observation ID.

iNatLookup bridges that gap by using a local binary index of the iNaturalist Open Data photos table.

This makes photo-to-observation lookups extremely fast without repeatedly searching the iNaturalist website or downloading the entire photos table for each lookup.

## Features

- Look up a single iNaturalist photo ID.
- Look up a photo from an iNaturalist photo URL.
- Batch-process a text file containing photo IDs or photo URLs.
- Binary-search a local index containing hundreds of millions of photo records.
- Cache duplicate photo IDs during batch processing.
- Recover the parent observation UUID from the local index.
- Optionally query the iNaturalist API for observation ID and observation URL.
- Cache API results for duplicate observations during batch processing.
- Write batch results to CSV.
- Display lookup and API statistics.
- Validate the index format and record structure.
- Include automated tests.

## Requirements

- Python 3
- A locally-built `inatlookup.bin` index.
- `requests` for API enrichment.

Install the Python dependency with:

```text
pip install requests
```

## Basic usage

### Single photo ID

```text
python inatlookup.py 455606536
```

### Single photo URL

```text
python inatlookup.py https://static.inaturalist.org/photos/455606536/original.jpeg
```

The program reports the photo ID, observation UUID, observation ID and observation URL when the photo is found and the iNaturalist API can return the observation.

### Interactive mode

Run without an argument:

```text
python inatlookup.py
```

Then enter photo IDs or photo URLs interactively.

Press Enter on a blank line to quit.

## Batch lookup

Create a text file containing one photo ID or photo URL per line.

For example:

```text
455606536
999999999999
banana
455606536
```

Run:

```text
python inatlookup.py test_batch.txt
```

Blank lines are ignored.

Invalid inputs are reported as `invalid input`.

Valid photo IDs that are absent from the local index are reported as `not found`.

Duplicate photo IDs are cached, so the binary index is searched only once for each unique photo ID.

The default output file is:

```text
inatlookup_results.csv
```

A different output file can be specified with:

```text
python inatlookup.py test_batch.txt --output results.csv
```

or:

```text
python inatlookup.py test_batch.txt -o results.csv
```

## API enrichment

Batch results can optionally be enriched using the iNaturalist API.

Use:

```text
python inatlookup.py --api test_batch.txt
```

With API enrichment enabled, each photo found in the local index is associated with its observation ID and observation URL.

Duplicate observations are cached, so multiple photos belonging to the same observation require only one API request.

For example, if two input records resolve to the same observation:

```text
API lookups        : 1
API successes      : 1
API failures       : 0
```

The API is not queried for:

- invalid input
- photos not found in the local index

### API batch CSV

Without `--api`, the CSV contains:

```text
input
photo_id
observation_uuid
status
```

With `--api`, two additional fields are included:

```text
observation_id
observation_url
```

The full API-enriched CSV therefore contains:

```text
input
photo_id
observation_uuid
status
observation_id
observation_url
```

API failures do not stop the batch. The corresponding API fields remain blank and the failure is included in the summary.

## Index information

Display information about the local index with:

```text
python inatlookup.py --info
```

Example:

```text
iNatLookup 0.3.0
Index format v1
Records : 475,206,174
```

The index currently contains:

```text
475,206,174
```

records.

## Command-line options

```text
python inatlookup.py [photo] [options]
```

### `--index`

Specify an alternative index file:

```text
python inatlookup.py --index tests/test_index.bin 455606536
```

### `--output`, `-o`

Specify the output CSV file for batch mode:

```text
python inatlookup.py test_batch.txt -o results.csv
```

### `--api`

Enable iNaturalist API enrichment in batch mode:

```text
python inatlookup.py --api test_batch.txt
```

### `--info`

Display information about the index and exit:

```text
python inatlookup.py --info
```

### `--version`

Display the program version:

```text
python inatlookup.py --version
```

## Index format

The local index uses a fixed binary format.

### Header

The index header is 128 bytes.

Important fields include:

- Magic signature
- Format version
- Record count
- Record size
- Header size
- Build timestamp

### Records

Each record is 24 bytes:

```text
8 bytes   iNaturalist photo ID
16 bytes  observation UUID
```

Records are sorted by photo ID, allowing binary search.

The current format is:

```text
Index format v1
Record size: 24 bytes
Header size: 128 bytes
```

## Tests

Run the complete test suite with:

```text
python tests/test_lookup.py
```

The test suite covers:

- known photo lookup
- missing photo lookup
- photo ID parsing
- photo URL parsing
- invalid input
- batch lookup
- duplicate photo caching
- API lookup success
- API lookup failure
- batch API enrichment
- API CSV output
- lookup context manager
- invalid index format version
- invalid record size
- invalid header size

The tests use a small test index where appropriate and mock API requests, so the automated test suite does not depend on the live iNaturalist API.

## Project structure

```text
inatlookup/
│
├── inatlookup.py
├── lookup.py
├── header.py
├── constants.py
├── version.py
│
├── data/
│   └── inatlookup.bin
│
└── tests/
    ├── create_test_index.py
    ├── test_index.bin
    └── test_lookup.py
```

## Current version

```text
iNatLookup 0.3.0
```

## Licence

This project is intended as a practical utility for working with iNaturalist Open Data.

Check the iNaturalist terms and Open Data documentation for applicable data-use conditions.