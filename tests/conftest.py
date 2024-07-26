import os
import pytest
from datetime import datetime
import pandas as pd
import warnings
import sqlite3
import psycopg2
from contextlib import contextmanager

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
appDB = os.path.join(curDir, "..", "appData", "accorns.db")
testDB = os.path.join(curDir, "..", "appData", "accorns-test.db")

# Add a command line option to save the database after the test
def pytest_addoption(parser):
    parser.addoption(
        "--save", action="store_true", default=False, help="Save the database after the test with unique name"
    )

@pytest.fixture
def save(request):
    return request.config.getoption("--save")

# Code to run before and after the test session
def pytest_sessionstart(session):
    print("pytest_sessionstart")
    if os.path.exists(appDB):
            os.rename(appDB, appDB + ".bak")

def pytest_sessionfinish(session, exitstatus):
    # Rename the test database to accorns-test.db and the original database back to accorns.db
    #overwrite last test database if needed
    if os.path.exists(testDB):
        os.remove(testDB)
    
    if session.config.getoption("--save"):
        os.rename(appDB, f"appData/accorns-test_{int(datetime.now().timestamp())}.db")
    else:
        os.rename(appDB, testDB)

    if os.path.exists(appDB + ".bak"):
        os.rename(appDB + ".bak", appDB)

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
        conn =  sqlite3.connect(appDB)
    
    try:
        yield conn
    finally:
        conn.close()

def dbQuery(conn, query, params=(),remoteAppDB=False):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
    
        query = query.replace("?", "%s") if remoteAppDB else query
        q = pd.read_sql_query(sql=query, con=conn, params=params)
    
    return q


