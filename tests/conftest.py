import os
import pytest
from datetime import datetime
import pandas as pd
import warnings
import sqlite3
import psycopg2
from contextlib import contextmanager
from shutil import copyfile

curDir = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
appDB = os.path.join(curDir, "..", "appData", "accorns.db")
vectorDB = os.path.join(curDir, "..", "appData", "vectordb.duckdb")
testDB = os.path.join(curDir, "..", "appData", "accorns-test.db")
scuirrelOnlyDB = os.path.join(curDir, "..", "appData", "scuirrelOnly-test.db")

# Add a command line option to save the database after the test
def pytest_addoption(parser):
    parser.addoption(
        "--save", action="store_true", default=False, help="Save the database after the test with unique name"
    )
    parser.addoption(
        "--newVectorDB", action="store_true", default=False, help="Test vector database file insertion"
    )
    parser.addoption(
        "--scuirrelOnly", action="store_true", default=False, help="Test SCUIRREL only (test database must be present)"
    )
    parser.addoption(
        "--accornsOnly", action="store_true", default=False, help="Test ACCORNS only"
    )

@pytest.fixture
def cmdopt(request):
    return {
        "save": request.config.getoption("--save"),
        "newVectorDB": request.config.getoption("--newVectorDB"),
        "scuirrelOnly": request.config.getoption("--scuirrelOnly"),
        "accornsOnly": request.config.getoption("--accornsOnly")
        }

# Code to run before and after the test session
def pytest_sessionstart(session):

    if session.config.getoption("--scuirrelOnly"):
        if not os.path.exists(testDB):
            raise ConnectionError(
                "Existing test database was not found. Please run ACCORNS test first"
            )
        copyfile(testDB, appDB)
        return
    
    # Backup existing databases
    if os.path.exists(appDB):
            os.rename(appDB, appDB + ".bak")
    if os.path.exists(vectorDB):
            copyfile(vectorDB, vectorDB + ".bak")
    
    

def pytest_sessionfinish(session, exitstatus):
    
    if session.config.getoption("--scuirrelOnly"):
        if os.path.exists(scuirrelOnlyDB):
            os.remove(scuirrelOnlyDB)
        os.rename(appDB, scuirrelOnlyDB)

        return  
    
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
    
    # Restore the original vector database
    if os.path.exists(vectorDB + ".bak"):
        os.remove(vectorDB)
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
        conn =  sqlite3.connect(appDB)
    
    try:
        yield conn
    finally:
        conn.close()

def dbQuery(conn, query, params=(),insert = False, remoteAppDB=False):
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


