# PostgreSQL Setup Guide

Set `remoteAppDB = "True"` in the
[shared/shared_config.py](../../shared/shared_config.toml) file and update any other
necessary configuration settings.

## Local PostgreSQL server _(local development only)_

- Create the following environment variables:
  - POSTGRES_PASS_SCUIRREL
  - POSTGRES_PASS_ACCORNS
  - The value of these variables will be used as the password for the SCUIRREL and
    ACCORNS databases respectively during setup
- [Install PostgreSQL](https://www.postgresql.org/) on your machine
- Install the [pgvector](https://github.com/pgvector/pgvector) extension
- Initialize the databases by running the init scripts in the command line:
  - If the `psql` command is not in your PATH or the default PostgreSQL superuser
    account is not `postgres`, you need to edit the variables at the top of the init
    scripts before running them
  - Windows: Run the [appDB_postgres_init.bat](../../ACCORNS/appDB/appDB_postgres_init.bat)
    script
  - Linux / MacOS: [appDB_postgres_init.sh](../../ACCORNS/appDB/appDB_postgres_init.sh)
    script on

## Remote PostgreSQL server _(production deployment)_

- Create a remote PostgreSQL server (e.g. Amazon Web Services)
- Install the [pgvector](https://github.com/pgvector/pgvector) extension on your remote
  machine (many cloud services have this pre-installed).
- Create the following environment variables on your remote system:
  - POSTGRES_PASS_SCUIRREL
  - POSTGRES_PASS_ACCORNS
  - The value of these variables will be used as the password for the SCUIRREL and
    ACCORNS databases respectively during setup
- Initialize the databases by running the init scripts in the command line:
  - If the `psql` command is not in your PATH or the default PostgreSQL superuser
    account is not `postgres`, you need to edit the variables at the top of the init
    scripts before running them
  - Windows: Run the [appDB_postgres_init.bat](../../ACCORNS/appDB/appDB_postgres_init.bat)
    script
  - Linux / MacOS: [appDB_postgres_init.sh](../../ACCORNS/appDB/appDB_postgres_init.sh)
    script on
- Test if the server is accessible from your local machine
- Update the connection details in the
  [shared/shared_config.py](../../shared/shared_config.toml) file
- Create the following environment variables on your deployment server (or Posit Connect
  app):
  - POSTGRES_PASS_SCUIRREL
  - POSTGRES_PASS_ACCORNS
  - The values should be the same as the ones set on the remote PostgreSQL server

## Troubleshooting

In case you are not able to run the init scripts, you can manually create the databases
by copying the SQL commands from the following scripts:
- [appDB_postgres_accorns.sql](../../ACCORNS/appDB/appDB_postgres_accorns.sql)
- [appDB_postgres_vectordb.sql](../../ACCORNS/appDB/appDB_postgres_vectordb.sql)
- Note that you will have to replace the following SQL variables with actual values:
    - :'scuirrelPass' -> the password for the SCUIRREL user
    - :'accornsPass' -> the password for the ACCORNS user
    - :overWrite -> 'true' if you want to overwrite the existing database
