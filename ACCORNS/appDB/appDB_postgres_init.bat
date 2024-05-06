@echo off
@REM These command should be executed only ONCE to setup or reset the postgres database
@REM Make sure POSTGRES_PASS_SCUIRREL is set as an environment variable!

@REM VARIABLES TO SET BEFORE RUNNING
@REM Note that if postgres bin is not in the PATH to put in the full path
SET "postgresAdmin=postgres"
SET "postgresBin=psql"
SET "appDBFolder=%~dp0"
SET "addDemo=True"
SET "dbName=scuirrel"
SET "override=True"

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



IF "%addDemo%"=="True" (
    IF NOT EXIST "%sqlDemo%" (
        echo ERROR Demo SQL file does not exist.
        exit /b 1
    )
    "%postgresBin%" -U %postgresAdmin% -f %sqlFile% -f %sqlDemo% ^
        -v admin="%postgresAdmin%" -v dbName="%dbName%" ^
        -v appPass=%POSTGRES_PASS_SCUIRREL% > nul
) ELSE (
    "%postgresBin%" -U %postgresAdmin% -f %sqlFile% ^
        -v admin="%postgresAdmin%" -v dbName="%dbName%" ^
        -v appPass=%POSTGRES_PASS_SCUIRREL% > nul
)

echo SUCCESS: Database %dbName% succesfully created and user 'scuirrel' added
