# ACCORNS - Admin Control Center Overseeing RAG Needed for SCUIRREL

## About
In this application instructors can set-up, manage and monitor [SCUIRREL](../SCUIRREL/)

* Create / edit topics to be discussed
* Create / edit specific concepts (facts) for each topic to help guide the conversation
* Upload new files to the vector database for retrieval augmented generation (RAG)

## Installation and Setup

* See the main [README](../README.md) file for details on setting up the environment
* Make sure to set all paths and specific ACCORNS settings in the [config.toml](config.toml) file

## Files and Folders

* [app.py](app.py): Main app file
* [app_shared.py](app_shared.py): Shared variables and functions across different session 
* [config.toml](config.toml): App wide settings
* [appDB/createDB.sql](appDB/createDB.sql): SQL file used to generate the app database
* [www/](www/): Contains files needed to render the app properly 
(Don't add sensitive data as this folder is accessible by the client!)
