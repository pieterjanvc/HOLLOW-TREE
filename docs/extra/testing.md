# Testing apps & Generating tutorials

## About and Installation

The playwright library provides a way to test the Shiny apps by running them in a
(headless) browser following a predefined set of instructions to interact with the apps.
This workflow allows us to both test the most common features of the apps and generate
tutorials by recording the steps

In order to use playwright, you need to have all developer dependencies installed. Then,
install playwright by running the following command:

```bash
playwright install
```

## Running tests

To run the [test_apps.py](../../tests/test_apps.py) file, you need to have the virtual
environment activated

Assuming you are in the tests folder, you can run the following command:

```bash
pytest test_apps.py --slowmo 200
```

Optional arguments

- --headed (browser is visible)
- --slowmo 200 (slows down every action by x ms to better see what's happening)
- --save (save timestamped database, otherwise overwrite previous test database)
- --newVectorDB (don't use a backup vector database. More time and LLM tokens required)
- --excludeLLMTest (exclude test functions that use LLM apart from chat itself)
- --scuirrelOnly (test SCUIRREL only, requires existing test database)
- --accornsOnly (test ACCORNS only)
- --publishPostgres (generate publishing directories and test with the postgres
  database)

_Note that failing to add `--slowmo 200` to a test might cause it to error out not
because of an actual error but because of lag during the session when writing text
resulting in incomplete values_

During testing, existing database files in the appData folder are backed up and restored
once the tests are done. Testing databases are stored in the
[testData](../../tests/testData) folder
