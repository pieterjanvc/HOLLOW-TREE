# SCUIRREL - Science Concept Understanding with Interactive Research RAG Educational LLM 

## About
This is the main application through which student will interact with the LLM. 
Configuring and monitoring is done through the additional [ACCORNS](../ACCORNS/) app

* Students can select a topic to check their knowledge on
* Interact with the LLM in conversation led by the topic and concepts set by the instructor
* The LLM should adapt the conversation to the student's answers and keep them engaged and on topic

## Installation and Setup

* See the main [README](../README.md) file for details on setting up the environment
* Make sure to set all paths and specific ACCORNS settings in the [config.toml](config.toml) file

## Files and Folders

* [app.py](app.py): Main app file
* [app_shared.py](app_shared.py): Shared variables and functions across different session 
* [config.toml](config.toml): App wide settings
