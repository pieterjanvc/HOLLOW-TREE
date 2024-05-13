
\set ON_ERROR_STOP on

-- Check if the databases already exist if overWrite is set to false
CREATE OR REPLACE FUNCTION check_overwrite(overWrite boolean, db TEXT)
RETURNS void AS $$
BEGIN
  IF NOT overWrite THEN
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = db) THEN
        RAISE EXCEPTION 'Database % already exists and overWrite is set to false', db;
    END IF;
  END IF;
END;
$$ LANGUAGE plpgsql;

SELECT check_overwrite(:overWrite, 'vector_db');

-- Drop and create the database
DROP DATABASE IF EXISTS vector_db;
CREATE DATABASE vector_db;

\c vector_db;

CREATE EXTENSION vector;

CREATE SEQUENCE seq_fID START 1;
CREATE TABLE file (
  "fID" SERIAL PRIMARY KEY,
  "fileName" TEXT,
  "title" TEXT,
  "subtitle" TEXT,
  "created" TEXT,
  "modified" TEXT
);

CREATE SEQUENCE seq_kID START 1;
CREATE TABLE keyword (
  "kID" SERIAL PRIMARY KEY,
  "fID" INTEGER,
  "keyword" TEXT,
  FOREIGN KEY("fID") REFERENCES "file"("fID") 
);

-- CREATE scuirrel and accorns USERS

\c vector_db;

CREATE OR REPLACE FUNCTION add_user(uName TEXT, uPass TEXT)
RETURNS void AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = uName) THEN
        EXECUTE format('CREATE ROLE %I WITH LOGIN PASSWORD %L', uName, uPass);
    END IF;
END;
$$ LANGUAGE plpgsql;

SELECT add_user('scuirrel', :'scuirrelPass');
SELECT add_user('accorns', :'accornsPass');

GRANT CONNECT ON DATABASE vector_db TO scuirrel;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO scuirrel;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scuirrel;

GRANT CONNECT ON DATABASE vector_db TO accorns;
GRANT all privileges ON DATABASE vector_db to accorns;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO accorns;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO accorns;
GRANT CREATE ON SCHEMA public TO accorns;
