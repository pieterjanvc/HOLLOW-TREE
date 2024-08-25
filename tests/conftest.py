import os
import pytest
from datetime import datetime
import pandas as pd
import warnings
import sqlite3
import duckdb
import psycopg2
from contextlib import contextmanager
from shutil import copyfile
from pathlib import Path, PurePath
from shiny.run._run import shiny_app_gen
from shiny.run import ShinyAppProc
from playwright.sync_api import Playwright, Browser, BrowserContext

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
appDB = os.path.join(curDir, "..", "appData", "accorns.db")
vectorDB = os.path.join(curDir, "..", "appData", "vectordb.duckdb")


# Add a command line option to save the database after the test
def pytest_addoption(parser):
    parser.addoption(
        "--save",
        action="store_true",
        default=False,
        help="Save the database after the test with unique name",
    )
    parser.addoption(
        "--newVectorDB",
        action="store_true",
        default=False,
        help="Don't use the existing vector database. More time and LLM tokens required",
    )
    parser.addoption(
        "--excludeLLMTest",
        action="store_true",
        default=False,
        help="Dont test LLM based actions, apart from the chat itself",
    )
    parser.addoption(
        "--scuirrelOnly",
        action="store_true",
        default=False,
        help="Test SCUIRREL only (test database must be present)",
    )
    parser.addoption(
        "--accornsOnly", action="store_true", default=False, help="Test ACCORNS only"
    )
    parser.addoption(
        "--publishPostgres",
        action="store_true",
        default=False,
        help="Generate publishing directories and test with the postgres database",
    )
    parser.addoption(
        "--record",
        action="store_true",
        default=False,
        help="Record the test session",
    )


@pytest.fixture
def cmdopt(request):
    return {
        "save": request.config.getoption("--save"),
        "newVectorDB": request.config.getoption("--newVectorDB"),
        "excludeLLMTest": request.config.getoption("--excludeLLMTest"),
        "scuirrelOnly": request.config.getoption("--scuirrelOnly"),
        "accornsOnly": request.config.getoption("--accornsOnly"),
        "publishPostgres": request.config.getoption("--publishPostgres"),
    }


@pytest.fixture
def appFiles(request):
    if request.config.getoption("--publishPostgres"):
        return {
            "ACCORNS": os.path.join(curDir, "..", "publish", "ACCORNS", "app.py"),
            "SCUIRREL": os.path.join(curDir, "..", "publish", "SCUIRREL", "app.py"),
        }
    else:
        return {
            "ACCORNS": os.path.join(curDir, "..", "accorns_app.py"),
            "SCUIRREL": os.path.join(curDir, "..", "scuirrel_app.py"),
        }


# Code to run before and after the test session
def pytest_sessionstart(session):
    if session.config.getoption("--publishPostgres"):
        if session.config.getoption("--scuirrelOnly") or session.config.getoption(
            "--accornsOnly"
        ):
            NotImplementedError(
                "Cannot run SCUIRREL or ACCORNS only with --publishPostgres"
            )

        # Generate the publishing directories
        script = (
            os.path.join(curDir, "..", "publish", "generate_publishing_dir.py")
            + " --addDemo"
        )
        os.system("python " + script)

        # Reset the Postgres database
        script = os.path.join(
            curDir,
            "..",
            "ACCORNS",
            "appDB",
            f"appDB_postgres_init.{'bat' if os.name == 'nt' else 'sh'}",
        )
        os.system(script)

        return

    # Backup existing databases
    if os.path.exists(appDB):
        os.rename(appDB, appDB + ".bak")
    if os.path.exists(vectorDB):
        os.rename(vectorDB, vectorDB + ".bak")

    return


def pytest_sessionfinish(session, exitstatus):
    if session.config.getoption("--publishPostgres"):
        return

    # Delete the vector database used in testing
    if os.path.exists(appDB):
        os.remove(appDB)

    if os.path.exists(vectorDB):
        os.remove(vectorDB)

    # Restore any previous databases
    if os.path.exists(appDB + ".bak"):
        os.rename(appDB + ".bak", appDB)

    if os.path.exists(vectorDB + ".bak"):
        os.rename(vectorDB + ".bak", vectorDB)


@contextmanager
def appDBConn(remoteAppDB=False, postgresHost="localhost"):
    if remoteAppDB:
        conn = psycopg2.connect(
            host=postgresHost,
            user="accorns",
            password=os.environ.get("POSTGRES_PASS_ACCORNS"),
            database="accorns",
        )

    else:
        if not os.path.exists(appDB):
            raise ConnectionError(
                "The app database was not found. Please run ACCORNS first"
            )
        conn = sqlite3.connect(appDB)

    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def vectorDBConn(remoteAppDB=False, postgresHost="localhost"):
    return
    # if remoteAppDB:
    #     conn = psycopg2.connect(
    #         host=postgresHost,
    #         user="accorns",
    #         password=os.environ.get("POSTGRES_PASS_ACCORNS"),
    #         database="vector_db",
    #     )

    # else:
    #     if not os.path.exists(vectorDB):
    #         raise ConnectionError(
    #             "The vector database was not found. Please run ACCORNS first"
    #         )
    #     conn = duckdb.connect(vectorDB, read_only=True)

    # try:
    #     yield conn
    # finally:
    #     conn.close()


def dbQuery(conn, query, params=(), insert=False, remoteAppDB=False):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if insert:
            cursor = conn.cursor()
            _ = cursor.execute(query, params)
            conn.commit()
            return
        else:
            query = query.replace("?", "%s") if remoteAppDB else query
            q = pd.read_sql_query(sql=query, con=conn, params=params)

    return q


@pytest.fixture(scope="session")
def browser(playwright: Playwright, request) -> Browser:
    headed = request.config.getoption("--headed")
    slowmo = request.config.getoption("--slowmo")

    launch_options = {}
    if headed:
        launch_options["headless"] = False
    if slowmo:
        launch_options["slow_mo"] = slowmo

    return playwright.chromium.launch(**launch_options)


@pytest.fixture(scope="function")
def context(browser: Browser, request) -> BrowserContext:
    record = request.config.getoption("--record")

    context_options = {"viewport": {"width": 1280, "height": 1000}}

    if record:
        context_options["record_video_size"] = {"width": 1280, "height": 1000}

    if not record:
        yield browser.new_context(**context_options)
        return

    video_dir = os.path.join(os.path.dirname(__file__), "videos")
    os.makedirs(video_dir, exist_ok=True)

    context_options["record_video_dir"] = video_dir

    context = browser.new_context(**context_options)

    yield context

    context.close()


@pytest.fixture
def accornsApp(appFiles, request):
    if request.config.getoption("--scuirrelOnly"):
        pytest.skip("Skipping ACCORNS")

    # Use a clean database backup if it exists and not --newVectorDB
    cleanDB = os.path.join(curDir, "testData", "clean_vectorDB.duckdb")
    if (
        os.path.exists(cleanDB)
        and not request.config.getoption("--newVectorDB")
        and not request.config.getoption("--publishPostgres")
    ):
        copyfile(cleanDB, vectorDB)

    app = appFiles["ACCORNS"]
    app_purepath_exists = isinstance(app, PurePath) and Path(app).is_file()
    app_path = app if app_purepath_exists else request.path.parent / app
    sa_gen = shiny_app_gen(app_path, timeout_secs=60)

    x = next(sa_gen)

    # Save a clean backup of the vector database is not already saved or if --newVectorDB
    if (
        not os.path.exists(cleanDB)
        or request.config.getoption("--newVectorDB")
        and not request.config.getoption("--publishPostgres")
    ):
        copyfile(vectorDB, cleanDB)

    yield x

    prefix = "tutorial" if "tutorial" in request.node.name else "test"

    # Check if the test failed
    suffix = "_failed" if request.node.rep_call.failed else ""

    # Don't save local the databases if --publishPostgres
    if request.config.getoption("--publishPostgres"):
        return

    # Save appDB
    testDB = os.path.join(curDir, "testData", f"{prefix}_accornsAppDB{suffix}.db")
    copyfile(appDB, testDB)

    if request.config.getoption("--save"):
        copyfile(
            testDB,
            os.path.join(
                curDir,
                "testData",
                f"{prefix}_accornsAppDB{suffix}_{int(datetime.now().timestamp())}.db",
            ),
        )

    # Save vector DB (needed if SCUIRREL is run without ACCORNS first)
    #  Only do this when test files have been added to the vector DB
    if not request.config.getoption("--excludeLLMTest"):
        testDB = os.path.join(curDir, "testData", f"{prefix}_vectorDB{suffix}.duckdb")
        copyfile(vectorDB, testDB)

    if request.config.getoption("--save"):
        copyfile(
            testDB,
            os.path.join(
                curDir,
                "testData",
                f"{prefix}_vectorDB{suffix}_{int(datetime.now().timestamp())}.duckdb",
            ),
        )


@pytest.fixture
def scuirrelApp(appFiles, request):
    if request.config.getoption("--accornsOnly"):
        pytest.skip("Skipping SCUIRREL")

    prefix = "tutorial" if "tutorial" in request.node.name else "test"

    # Ignore local DB when the test is run with --publishPostgres
    if not request.config.getoption("--publishPostgres"):
        # Get the appDB from backup
        testDB = os.path.join(curDir, "testData", f"{prefix}_accornsAppDB.db")

        if not os.path.exists(testDB):
            raise ConnectionError(
                "Existing app database was not found. Please run ACCORNS first"
            )
        copyfile(testDB, appDB)

        # Get the vectorDB from backup
        testDB = os.path.join(curDir, "testData", f"{prefix}_vectorDB.duckdb")

        if not os.path.exists(testDB):
            raise ConnectionError(
                "Existing vector database was not found. Please run ACCORNS first"
            )
        copyfile(testDB, vectorDB)

    app = appFiles["SCUIRREL"]
    app_purepath_exists = isinstance(app, PurePath) and Path(app).is_file()
    app_path = app if app_purepath_exists else request.path.parent / app
    sa_gen = shiny_app_gen(app_path, timeout_secs=60)

    yield next(sa_gen)

    # Don't save local the databases if --publishPostgres
    if request.config.getoption("--publishPostgres"):
        return

    testDB = os.path.join(curDir, "testData", f"{prefix}_scuirrelAppDB.db")
    copyfile(appDB, testDB)

    if request.config.getoption("--save"):
        copyfile(
            testDB,
            os.path.join(
                curDir,
                "testData",
                f"{prefix}_scuirrelAppDB_{int(datetime.now().timestamp())}.db",
            ),
        )
