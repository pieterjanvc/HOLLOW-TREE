@echo off

@REM This script should be executed only once to setup or reset the postgres database
@REM You will need to provide your postgres super user password interactively

@REM Make sure POSTGRES_PASS_SCUIRREL and POSTGRES_PASS_ACCORNS are set as an environment variables
@REM which will be used as the password for the 'scuirrel' and 'accorns' app to access the databases

@REM VARIABLES TO SET BEFORE RUNNING
@REM Note that if postgres bin is not in the PATH to put in the full path
SET "postgresAdmin=postgres"
SET "postgresBin=psql"
@REM Create "accorns" or "vector_db" or "both"
SET "toCreate=both" 
SET "addDemo=True"
SET "overWrite=True"

SET "appDBFolder=%~dp0"
SET "sqlAccorns=%appDBFolder%\appDB_postgres_accorns.sql" 
SET "sqlVectordb=%appDBFolder%\appDB_postgres_vectordb.sql" 
SET "sqlDemo=%appDBFolder%\appDB_postgres_demo.sql" 

@REM Check if postgres is installed

where %postgresBin% >nul 2>nul || (
    echo ERROR Postgres is not installed or cannot be found in PATH.
    exit /b 1
) 

@REM Check if sqlAccorns, sqlVectordb and sqlDemo exist
IF NOT EXIST "%sqlAccorns%" (
    echo ERROR %sqlAccorns% does not exist.
    exit /b 1
)
IF NOT EXIST "%sqlVectordb%" (
    echo ERROR %sqlVectordb% does not exist.
    exit /b 1
)
IF NOT EXIST "%sqlDemo%" (
    echo ERROR %sqlDemo% does not exist.
    exit /b 1
)

@REM check if %POSTGRES_PASS_SCUIRREL% and %POSTGRES_PASS_ACCORNS% are set environment variables
IF "%POSTGRES_PASS_SCUIRREL%"=="" (
    echo ERROR POSTGRES_PASS_SCUIRREL environment variable is not set.
    exit /b 1
)

IF "%POSTGRES_PASS_ACCORNS%"=="" (
    echo ERROR POSTGRES_PASS_ACCORNS environment variable is not set.
    exit /b 1
)

@REM check if toCreate is valid
IF NOT "%toCreate%"=="both" IF NOT "%toCreate%"=="accorns" IF NOT "%toCreate%"=="vector_db" (
    echo ERROR Invalid value for toCreate. Must be 'both', 'accorns' or 'vector_db'.
    exit /b 1
)

SET "errorFile=%TEMP%\error.txt"

@REM variable toRun contains -f flags depending on sqlDemo and toCreate
IF "%toCreate%"=="both" (
    SET "toRun=-f %sqlAccorns% -f %sqlVectordb%"
) ELSE IF "%toCreate%"=="accorns" (
    SET "toRun=-f %sqlAccorns%"
) ELSE (
    SET "toRun=-f %sqlVectordb%"
)

 @REM only add demo to toRun if true and toCreate is not just vector_db
IF "%addDemo%"=="True" IF NOT "%toCreate%"=="vector_db" (
    SET "toRun=%toRun% -f %sqlDemo%"
)

"%postgresBin%" -U %postgresAdmin% %toRun% ^
        -v overWrite=%overWrite% ^
        -v scuirrelPass="%POSTGRES_PASS_SCUIRREL%" ^
        -v accornsPass="%POSTGRES_PASS_ACCORNS%" ^
         > nul 2> "%errorFile%"

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

@REM Print success message with database name(s) and users
IF "%toCreate%"=="both" (
    SET "dbName=accorns and vector_db"
) ELSE (
    SET "dbName=%toCreate%"
)
echo.
echo SUCCESS: %dbName% created and the users 'scuirrel' and 'accorns' added
