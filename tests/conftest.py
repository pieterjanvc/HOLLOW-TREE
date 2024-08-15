import os
import pytest
from datetime import datetime
import pandas as pd
import warnings
import sqlite3
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
        help="Test vector database file insertion",
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
        # Generate the publishing directories
        script = (
            os.path.join(curDir, "..", "publish", "generate_publishing_dir.py")
            + " --addDemo"
        )
        os.system(script)

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
        if session.config.getoption("--newVectorDB"):
            os.rename(vectorDB, vectorDB + ".bak")
        else:
            copyfile(vectorDB, vectorDB + ".bak")
    
    if not session.config.getoption("--newVectorDB"):
        testVectorDB = os.path.join(curDir, "testData", "vectordb.duckdb")
        if os.path.exists(testVectorDB):
            os.replace(testVectorDB, vectorDB)

    return


def pytest_sessionfinish(session, exitstatus):

    # Save the test vector database for future use
    testVectorDB = os.path.join(curDir, "testData", "vectordb.duckdb")
    os.replace(vectorDB, testVectorDB)

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
        launch_options['headless'] = False  
    if slowmo:
        launch_options['slow_mo'] = slowmo

    return playwright.chromium.launch(**launch_options)

@pytest.fixture(scope="function")
def context(browser: Browser, request) -> BrowserContext:
    record = request.config.getoption("--record")

    context_options = {
        'viewport': {'width': 1280, 'height': 1000}
    }

    if record:
        context_options['record_video_size'] = {'width': 1280, 'height': 1000}

    if not record:
        yield browser.new_context(**context_options)
        return

    video_dir = os.path.join(os.path.dirname(__file__), "videos")
    os.makedirs(video_dir, exist_ok=True)

    context_options['record_video_dir'] = video_dir

    context = browser.new_context(**context_options)    
    
    yield context

    context.close()

@pytest.fixture
def accornsApp(appFiles, request):
    if request.config.getoption("--scuirrelOnly"):
        pytest.skip("Skipping ACCORNS")

    app = appFiles["ACCORNS"]
    app_purepath_exists = isinstance(app, PurePath) and Path(app).is_file()
    app_path = app if app_purepath_exists else request.path.parent / app
    sa_gen = shiny_app_gen(app_path, timeout_secs=60)

    yield next(sa_gen)

    prefix = "tutorial" if "tutorial" in request.node.name else "test"   

    testDB = os.path.join(curDir, "testData", f"{prefix}_accornsTest.db")
    copyfile(appDB, testDB)

    if request.config.getoption("--save"):
        copyfile(testDB, os.path.join(curDir, "testData", f"{prefix}_accornsTest_{int(datetime.now().timestamp())}.db"))

@pytest.fixture
def scuirrelApp(appFiles, request):
    if request.config.getoption("--accornsOnly"):
        pytest.skip("Skipping SCUIRREL")
    
    prefix = "tutorial" if "tutorial" in request.node.name else "test"
    testDB = os.path.join(curDir, "testData", f"{prefix}_accornsTest.db")

    if request.config.getoption("--scuirrelOnly"):        
        if not os.path.exists(testDB):
            raise ConnectionError(
                "Existing test database was not found. Please run ACCORNS first"
            )
        copyfile(testDB, appDB)
        return

    app = appFiles["SCUIRREL"]
    app_purepath_exists = isinstance(app, PurePath) and Path(app).is_file()
    app_path = app if app_purepath_exists else request.path.parent / app
    sa_gen = shiny_app_gen(app_path, timeout_secs=60)

    yield next(sa_gen)

    testDB = os.path.join(curDir, "testData", f"{prefix}_scuirrelTest.db")
    os.replace(appDB, testDB)

    if request.config.getoption("--save"):
        copyfile(testDB, os.path.join(curDir, "testData", f"{prefix}_scuirrelTest_{int(datetime.now().timestamp())}.db"))

