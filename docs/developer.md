# Developing ACCORNS and SCUIRREL

_For help in setting up the development environment for the ACCORNS and SCUIRREL apps
and tips on debugging read the [Environment setup guide](extra/dev_env_setup.md)_

## Software and Libraries

Both ACCORNS an SCUIRREL are Shiny for Python apps using the following important
libraries:

- The [Llamaindex](https://www.llamaindex.ai/) library is a wrapper for working with
  various LLMs (e.g. ChatGPT) and implement Retrieval Augmented Generation for
  increasing query accuracy
- The [Shiny framework](https://shiny.posit.co/py/) is used for generating the apps' UI
  and Server components (Shiny Express syntax is used)
- For a list of all other dependencies, see the [requirements.txt](./requirements.txt)
  file

## Accessing Large Language Models (LLM) in Python

The app is currently configured to run with OpenAI's GPT models. This requires your own
active [OPENAI API key](https://openai.com/index/openai-api/). If your are part of an
organization, you will also need the organization ID. Make sure both are available to
Python as environment variables with the following names:

- OPENAI_API_KEY
- OPENAI_ORGANIZATION

They will be accessed in the code like this

```
os.environ.get("OPENAI_API_KEY")
```

You can read this
[online guide](https://chlee.co/how-to-setup-environment-variables-for-windows-mac-and-linux/)
for more info on how to set these environment variables on different operating systems

_NOTE: The reason for using environment variables for the API key and organization ID is
because they should be kept secret and not shared with anyone else. Committing them to
the repository or hardcoding them anywhere in the code is a serious security risk_

## App databases

In you local development environment, you have two options for storing an accessing the
data for the apps:

1. **File-based storage**: SQLite / DuckDB databases will be created in the appDB folder
   by default.

- SQLite is used for storing the ACCORNS / SCUIRREL app data and logs
- DuckDB is used for storing the vectors used for the LLM retrieval augmented generation
- Both databases are created via the python scripts and do not require any additional
  setup

2. **PostgreSQL server**: This will be needed once you want to deploy the app to a
   server as it ensures correct handling of concurrent requests and data consistency.
   For local development, you can set up PostgreSQL databases in two ways:

- Local PostgreSQL server: [Install PostgreSQL](https://www.postgresql.org/) on your
  machine and create the necessary databases using the
  [appDB_postgres_init.bat](../ACCORNS/appDB/appDB_postgres_init.bat) script on Windows
  (Linux/Mac users can run the commands in the script manually for now)
- Remote PostgreSQL server: Set up a remote PostgreSQL server and configure the
  connection details in the [shared/shared_config.py](../shared/shared_config.toml) file
- In either case, you will need to set `remoteAppDB = "True"` in the
  [shared/shared_config.py](../shared/shared_config.toml) file and **make sure the
  following environment variables are set**:
  - POSTGRES_PASS_SCUIRREL : The password for the scuirrel user
  - POSTGRES_PASS_ACCORNS : The password for the accorns user

Below is an overview of the accorns database schema

![App DB Schema](https://drive.usercontent.google.com/download?id=1kOzuVdI-p1K5Ej6EaRh4dJZuxyCATCfT)

_Alternatively, look for the SQL files in the ACCORNS [appDB folder](../ACCORNS/appDB/)_

## Repo organization

The file organisation is largely dictated by the Shiny for Python framework and Express
syntax. For more details visit https://shiny.posit.co/py/docs/express-in-depth.html

The root folder contains the following important files and folders:

- accorns_app.py: The main Python Shiny file for the ACCORNS app
- ACCORNS: The folder containing additional ACCORNS app files and a
  [appDB](../ACCORNS/appDB/) folder containing all SQL files / scripts for setting up
  the databases
- scuirrel_app.py: The main Python Shiny file for the SCUIRREL app
- SCUIRREL: The folder containing additional SCUIRREL app files
- shared: The folder containing shared functions and variables between the two apps
- publish: Folder containing the script to generate publishing directories when ready to
  deploy the apps
- docs: Folder containing the documentation for the project. The main
  [README.md](../README.md) file links to these different documentation files

The ACCORNS, SCUIRREL, and shared folders all have a similar structure:

- The ACCORNS*shared.py / SCUIRREL_shared.py files contain variables and functions that
  are shared between app \_sessions* (not apps). To clarify: All code in the main
  accorns_app.py and scuirrel_app.py files is run for each new session (i.e. every time
  a user connects), whereas the shared files are only loaded once when the server starts
- .tolm files contain the settings for each app
- \_css and \_js sub-directories contain the custom CSS and JavaScript files for each of
  the apps (due to a bug in the Shiny for Python framework, each of these files
  currently needs a separate subfolder)
- To avoid duplication of code between ACCORNS and SCUIRREL during development, the
  [shared](../shared) folder contains the all of the above which are sourced into both
  the SCUIRREL and ACCORNS apps (and also only loaded once when the server starts)

Note that this file structure only works for _local development_. When deploying the
apps, separate folders for each app need to be created containing all the necessary
files inside it. For more details, see the [IT admin guide](docs/extra/ITadmin.md)

## Notes on specific coding implementations

- When sending a request to the LLM, the reactive function is run asynchronously to
  avoid blocking the Shiny server (single threaded by default). However, the way this is
  implemented in the Shiny for Python framework differs from the standard Python async
  implementation. An example is the `botResponse()` function in the scuirrel.py file.
  For more details on using async functions in Shiny, see the
  [Shiny for Python documentation](https://shiny.posit.co/py/docs/express-in-depth.html#async-functions)
