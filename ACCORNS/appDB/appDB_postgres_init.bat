@echo off

@REM This script should be executed only once to setup or reset the postgres database

@REM Make sure POSTGRES_PASS_SCUIRREL is set as an environment variable
@REM which will be used as the password for the 'scuirrel' database and is 
@REM also needed by both apps to connect to the database

@REM VARIABLES TO SET BEFORE RUNNING
@REM Note that if postgres bin is not in the PATH to put in the full path
SET "postgresAdmin=postgres"
SET "postgresBin=psql"
SET "appDBFolder=%~dp0"
SET "addDemo=True"
SET "dbName=scuirrel"
SET "overWrite=True"

SET "sqlFile=%appDBFolder%\appDB_postgres.sql" 
SET "sqlDemo=%appDBFolder%\appDB_postgres_demo.sql" 

@REM Check if postgres is installed

where %postgresBin% >nul 2>nul || (
    echo ERROR Postgres is not installed or cannot be found in PATH.
    exit /b 1
) 

@REM Check if sqlFile exists
IF NOT EXIST "%sqlFile%" (
    echo ERROR SQL file does not exist.
    exit /b 1
)

SET "errorFile=%TEMP%\error.txt"

@REM Initialize the database based on settings
IF "%addDemo%"=="True" (
    IF NOT EXIST "%sqlDemo%" (
        echo ERROR Demo SQL file does not exist.
        exit /b 1
    )
    "%postgresBin%" -U %postgresAdmin% -f %sqlFile% -f %sqlDemo% ^
        -v dbName="%dbName%" -v overWrite=%overWrite% ^
        -v appPass=%POSTGRES_PASS_SCUIRREL% > nul 2> "%errorFile%"
) ELSE (
    "%postgresBin%" -U %postgresAdmin% -f %sqlFile% ^
        -v dbName="%dbName%" -v overWrite=%overWrite% ^
        -v appPass=%POSTGRES_PASS_SCUIRREL% > nul 2> "%errorFile%"
)

@REM check if erorr file is empty otherwise print error
FOR %%i IN ("%errorFile%") DO IF %%~zi EQU 0 (
    del "%errorFile%"
) ELSE (
    type "%errorFile%"
    del "%errorFile%"
    echo.
    echo ERROR: An error occurred while creating the database. Check the error log.
    exit /b 1
)

echo.
echo SUCCESS: Database %dbName% was successfully created and the user 'scuirrel' was added
