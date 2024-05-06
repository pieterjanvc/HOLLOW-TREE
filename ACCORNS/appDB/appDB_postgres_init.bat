@REM These command should be executed only ONCE to setup or reset the postgres database
@REM Make sure POSTGRES_PASS_SCUIRREL is set as an environment variable!

@REM VARIABLES TO SET BEFORE RUNNING
SET "postgresAdmin=postgres"
SET "postgresBin=C:\Program Files\PostgreSQL\16\bin" 
SET "sqlFile=D:\Documents\LocalProjects\SCUIRREL\ACCORNS\appDB\appDB_postgres.sql" 
SET "addDemo=True"
SET "sqlDemo=D:\Documents\LocalProjects\SCUIRREL\ACCORNS\appDB\appDB_postgres_demo.sql" 
SET "dbName=scuirrel"
SET "override=True"

@REM Check if postgres is installed
IF NOT EXIST "%postgresBin%\psql.exe" (
    echo Postgres is not installed.
    exit /b 1
) 

@REM Check if sqlFile exists
IF NOT EXIST "%sqlFile%" (
    echo SQL file does not exist.
    exit /b 1
)

@echo off

IF "%addDemo%"=="True" (
    IF NOT EXIST "%sqlDemo%" (
        echo Demo SQL file does not exist.
        exit /b 1
    )
    "%postgresBin%\psql.exe" -U %postgresAdmin% -f %sqlFile% -f %sqlDemo% -v dbName="%dbName%" -v appPass=%POSTGRES_PASS_SCUIRREL%
) ELSE (
    "%postgresBin%\psql.exe" -U %postgresAdmin% -f %sqlFile% -v dbName="%dbName%" -v appPass=%POSTGRES_PASS_SCUIRREL%
)

@echo on
