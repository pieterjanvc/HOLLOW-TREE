# Developing ACCORNS and SCUIRREL apps

_For help in setting up the development environment for the ACCORNS and SCUIRREL apps
and tips on debugging read the [Environment setup guide](extra/dev_env_setup.md)_

## Software and Libraries

Both ACCORNS an SCUIRREL are Shiny for Python apps with the following dependencies:

- The [Llamaindex](https://www.llamaindex.ai/) library is a wrapper for working with
  various LLMs (e.g. ChatGPT) and implementing Retrieval Augmented Generation for
  increasing query accuracy
- The [Shiny framework](https://shiny.posit.co/py/) is used for generating the apps' UI
  and Server components (Shiny Core syntax is used)
- For a list of all other app dependencies, see the
  [requirements.txt](../requirements.txt) file
- For a list of additional developer dependencies, see the
  [requirements_dev.txt](../requirements_dev.txt) file

## Accessing Large Language Models (LLM) in Python

The app is currently configured to run with OpenAI's GPT models. This requires your own
active [OPENAI API key](https://openai.com/index/openai-api/). If your are part of an
organization, you will also need the organization ID. Make sure both are accessible in
Python as environment variables with the following names:

- OPENAI_API_KEY
- OPENAI_ORGANIZATION

_If you don't have an organization ID create an empty variable_

The variables will be accessed in python like this:

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

In your local development environment, you have two options for storing an accessing the
data for the apps, a file based database or a (local) PostgreSQL server. Note that once
you deploy apps you need a remote PostgreSQL server.

### OPTION 1: File-based storage

_This is the easiest way to set up the apps as everything is created automatically the
first time you run the ACCORNS app._

- Make sure the `remoteAppDB = False` in the
  [shared/shared_config.py](../shared/shared_config.toml) file
- The databases will be created in the `appDB/` folder by default (location can be
  changed in the [shared/shared_config.py](../shared/shared_config.toml) file
- SQLite is used for storing the ACCORNS / SCUIRREL app data and logs
- DuckDB is used for storing the vectors used for the LLM retrieval augmented generation

### OPTION 2: PostgreSQL server:

_PostgreSQL needs additional setup and configuration before you can use it in the apps_

See the [PostgreSQL setup guide](extra/postgres_setup.md) for more details

Below is an overview of the accorns database schema

![App DB Schema](https://drive.usercontent.google.com/download?id=1kOzuVdI-p1K5Ej6EaRh4dJZuxyCATCfT)

_Alternatively, look for the SQL files in the ACCORNS [appDB folder](../ACCORNS/appDB/)_

## Other settings

The following setting are relevant to check before running the apps for the first time:

- In the [shared_config.toml](../shared/shared_config.toml) file, set `addDemo = False`
  if you want to start without the demo data
- In the [accorns_config.toml](../ACCORNS/accorns_config.toml) file, set
  `saveFileCopy = true` if you would like to keep a copy of each uploaded file. You
  can also change the location where these files are saved

## Repo organization

The file organisation is largely dictated by the Shiny for Python framework and syntax.
For more details visit https://shiny.posit.co/py/docs

The root folder contains the following important files and folders:

- accorns_app.py: The main Python Shiny file for the ACCORNS app
- ACCORNS: The folder containing additional ACCORNS app files and a
  [appDB](../ACCORNS/appDB/) folder containing all SQL files / scripts for setting up
  the databases
- scuirrel_app.py: The main Python Shiny file for the SCUIRREL app
- SCUIRREL: The folder containing additional SCUIRREL app files
- shared: The folder containing shared functions and variables between the two apps
- modules: A folder containing all app modules (tabs). Some modules are app specific and
  others are shared between the apps.
- publish: Folder containing the script to generate publishing directories when ready to
  deploy the apps. The directories will appear in this folder after execution.
- docs: Folder containing the documentation for the project. The main
  [README.md](../README.md) file links to many of these files

The ACCORNS, SCUIRREL, and shared folders all have a similar structure:

- Files in the `shared/` folder are sourced into both apps, files in `ACCORNS` and
  `SCUIRREL` only in their respective apps
- The `accorns_shared.py` / `scuirrel_shared.py` files contain regular Python variables
  and functions that are sourced into the respective apps at runtime. Both apps source
  the `shared/shared.py` file. These files do not contain reactive code.
- .tolm files contain app settings
- \_css and \_js sub-directories contain the custom CSS and JavaScript files for each of
  the apps (due to a bug in the Shiny for Python framework, each of these files
  currently needs a separate subfolder)

Note that this file structure only works for _local development_. When deploying the
apps, separate app folders need to be generated. For more details, see the
[IT admin guide](ITadmin.md)

## Testing the apps & Generating tutorials

See [Testing apps & Generating tutorials](testing.md) for more details

```
pytest tests\test_apps.py --headed --slowmo 200
```

## Notes on specific coding implementations

- When sending a request to the LLM, the reactive function is run asynchronously to
  avoid blocking the Shiny server (single threaded by default). However, the way this is
  implemented in the Shiny for Python framework differs from the standard Python async
  implementation. An example is the `botResponse()` function in the scuirrel.py file.
  For more details on using async functions in Shiny, see the
  [Shiny for Python documentation](https://shiny.posit.co/py/docs/express-in-depth.html#async-functions)
