#!/bin/bash

# This script should be executed only once to setup or reset the postgres database
# You will need to provide your postgres super user password interactively

# Make sure POSTGRES_PASS_SCUIRREL and POSTGRES_PASS_ACCORNS are set as environment variables
# which will be used as the password for the 'scuirrel' and 'accorns' app to access the databases

# ----- VARIABLES TO SET BEFORE RUNNING -----
# Note that if postgres bin is not in the PATH to put in the full path
postgresAdmin="postgres"
postgresBin="psql"
postgresHost="localhost"
postgresPort="5432"
# Create "accorns" or "vector_db" or "both"
toCreate="both"
overWrite="true"
# -------------------------------------------

appDBFolder="$(dirname "$0")"
sqlAccorns="$appDBFolder/appDB_postgres_accorns.sql"
sqlVectordb="$appDBFolder/appDB_postgres_vectordb.sql"

# Check if postgres is installed
$postgresBin --version >/dev/null 2>&1  || {
    echo "ERROR: Postgres is not installed or cannot be found in PATH."
    exit 1
}

# Check if sqlAccorns, sqlVectordb and sqlDemo exist
if [ ! -f "$sqlAccorns" ]; then
    echo "ERROR: $sqlAccorns does not exist."
    exit 1
fi

if [ ! -f "$sqlVectordb" ]; then
    echo "ERROR: $sqlVectordb does not exist."
    exit 1
fi

# Check if POSTGRES_PASS_SCUIRREL and POSTGRES_PASS_ACCORNS are set environment variables
if [ -z "$POSTGRES_PASS_SCUIRREL" ]; then
    echo "ERROR: POSTGRES_PASS_SCUIRREL environment variable is not set."
    exit 1
fi

if [ -z "$POSTGRES_PASS_ACCORNS" ]; then
    echo "ERROR: POSTGRES_PASS_ACCORNS environment variable is not set."
    exit 1
fi

# Check if toCreate is valid
if [ "$toCreate" != "both" ] && [ "$toCreate" != "accorns" ] && [ "$toCreate" != "vector_db" ]; then
    echo "ERROR: Invalid value for toCreate. Must be 'both', 'accorns' or 'vector_db'."
    exit 1
fi

errorFile=$(mktemp)

# variable toRun contains -f flags depending on sqlDemo and toCreate
if [ "$toCreate" == "both" ]; then
    toRun="-f $sqlAccorns -f $sqlVectordb"
elif [ "$toCreate" == "accorns" ]; then
    toRun="-f $sqlAccorns"
else
    toRun="-f $sqlVectordb"
fi

$postgresBin -h "$postgresHost" -p "$postgresPort" -U "$postgresAdmin" postgres $toRun \
    -v overWrite="$overWrite" \
    -v scuirrelPass="$POSTGRES_PASS_SCUIRREL" \
    -v accornsPass="$POSTGRES_PASS_ACCORNS" > /dev/null 2> "$errorFile"

# check if error file is empty otherwise print error
if [ -s "$errorFile" ]; then
    cat "$errorFile"
    rm "$errorFile"
    echo
    echo "ERROR: An error occurred while creating the database. Check the error log."
    exit 1
else
    rm "$errorFile"
fi

# Print success message with database name(s) and users
if [ "$toCreate" == "both" ]; then
    dbName="accorns and vector_db"
else
    dbName="$toCreate"
fi

echo
echo "SUCCESS: $dbName created and the users 'scuirrel' and 'accorns' added"
