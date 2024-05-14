## Data storage

Data is stored in two separate databases

- The vector database used for RAG is implemented with DuckDB (note that original files
  uploaded to the app can be stored as well depending on the settings)

- All app data and logs are stored in a custom app database (schema below). This data is
  used for app operation, monitoring and research
- IMPORTANT: Edit the config.toml for SCUIRREL and ACCORNS before running the apps

### Local app database (SQLite)

- This is the default and useful during app development or testing, but would likely not
  scale well once many users need concurrent DB access.
- Given this DB is shared between SCUIRREL and ACCORNS, you need to configure the Shiny
  server or Posit connect to allow file access outside the app directory
- If the databases do not exist when the app is run, they will be created. Note that the
  admin app needs to be run before the student app the first time.

### Remote app database (PostgreSQL)

This is the preferred option when the apps are deployed for production. However, it
requires an additional Postgres server to be hosted somewhere. Once the server has been
setup and a database created, you can use the
[createAppDB.sql](ACCORNS/appDB/createAppDB.sql) file (used for SQLite) with the
following small modification:

Replace all `INTEGER PRIMARY KEY AUTOINCREMENT` with `SERIAL PRIMARY KEY`

Now this SQL can be used to initialise the PostgreSQL app DB. Make sure to edit the

![App DB Schema](https://drive.usercontent.google.com/download?id=1kOzuVdI-p1K5Ej6EaRh4dJZuxyCATCfT)
