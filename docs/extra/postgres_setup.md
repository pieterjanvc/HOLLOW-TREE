# PostgreSQL Setup Guide

To use PostgeSQL databases set `remoteAppDB = "True"` in the
[shared/shared_config.py](../../shared/shared_config.toml) file and update relevant
configuration settings in accordance with your setup.

## Local PostgreSQL server _(local development only)_

- Create the following environment variables:
  - POSTGRES_PASS_SCUIRREL - Password for the SCUIRREL app to access the database
  - POSTGRES_PASS_ACCORNS - Password for the ACCORNS app to access the database
  - The value of these variables will be used during setup
- [Install PostgreSQL](https://www.postgresql.org/) on your machine
- Install the [pgvector](https://github.com/pgvector/pgvector) extension. This is needed
  for retrieval augmented generation (RAG)
- Initialize the databases by running the init scripts on the command line:
  - If the `psql` command is not in your PATH or the default PostgreSQL superuser
    account is not `postgres`, you need to edit the variables at the top of the init
    scripts before running them
  - Windows: Run the
    [appDB_postgres_init.bat](../../ACCORNS/appDB/appDB_postgres_init.bat) script
  - Linux / MacOS: [appDB_postgres_init.sh](../../ACCORNS/appDB/appDB_postgres_init.sh)
    script

## Remote PostgreSQL server _(production / deployment)_

- Make sure you gave access to a PostgreSQL server instance (e.g. self-hosted or via
  services like Amazon Web Services)
- Install the [pgvector](https://github.com/pgvector/pgvector) extension on your remote
  machine (many cloud services have this pre-installed). This is needed for retrieval
  augmented generation (RAG)
- Create the following environment variables on your remote system:
  - POSTGRES_PASS_SCUIRREL - Password for the SCUIRREL app to access the database
  - POSTGRES_PASS_ACCORNS - Password for the ACCORNS app to access the database
  - The value of these variables will be used during setup
- Initialize the databases by running the init scripts on the command line:
  - If the `psql` command is not in your PATH or the default PostgreSQL superuser
    account is not `postgres`, you need to edit the variables at the top of the init
    scripts before running them
  - Windows: Run the
    [appDB_postgres_init.bat](../../ACCORNS/appDB/appDB_postgres_init.bat) script
  - Linux / MacOS: [appDB_postgres_init.sh](../../ACCORNS/appDB/appDB_postgres_init.sh)
    script on
- Test if the server is accessible from your local machine
- Update the connection details in the
  [shared/shared_config.py](../../shared/shared_config.toml) file or provide them as
  arguments when generating the production apps (details in
  [ITadmin guide](../ITadmin.md))
- Make sure the POSTGRES_PASS_SCUIRREL and POSTGRES_PASS_ACCORNS environment variables
  are accessible to the Shiny app (details in [ITadmin guide](../ITadmin.md))

## Troubleshooting

In case you are not able to run the init scripts, you can manually create the databases
by copying the SQL commands from the following scripts:

- [appDB_postgres_accorns.sql](../../ACCORNS/appDB/appDB_postgres_accorns.sql)
- [appDB_postgres_vectordb.sql](../../ACCORNS/appDB/appDB_postgres_vectordb.sql)
- Note that you will have to replace the following SQL variables with actual values:
  - :'scuirrelPass' -> the password for the SCUIRREL user
  - :'accornsPass' -> the password for the ACCORNS user
  - :overWrite -> 'true' if you want to overwrite the existing database
