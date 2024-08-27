
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

SELECT check_overwrite(:overWrite, 'accorns');

-- Drop and create the database
DROP DATABASE IF EXISTS accorns;
CREATE DATABASE accorns;

\c accorns;

CREATE TABLE "user" (
	"uID" SERIAL PRIMARY KEY,
	"username" TEXT UNIQUE,
  "password" TEXT, 
  "adminLevel" INTEGER DEFAULT 0,
  "fName" TEXT,
  "lName" TEXT,
  "email" TEXT,
  "created" TEXT,
  "modified" TEXT
);

CREATE TABLE "session" (
	"sID" SERIAL PRIMARY KEY,
  "uID" INTEGER,
  "appID" INTEGER,
  "start" TEXT,
  "end" TEXT,
  "shinyToken" TEXT,
  "error" TEXT,
	FOREIGN KEY("uID") REFERENCES "user"("uID") 
		ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "topic" (
	"tID" SERIAL PRIMARY KEY,
  "sID" INTEGER,
	"topic" TEXT,
  "status" INTEGER DEFAULT 1,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT
);

CREATE TABLE "group" (
  "gID" SERIAL PRIMARY KEY,
  "sID" INTEGER,
  "group" TEXT,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT,
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE group_member(
  "gmID" SERIAL PRIMARY KEY,
  "uID" INTEGER,
  "gID" INTEGER,
  "added" TEXT,
  "adminLevel" INTEGER DEFAULT 0,
  FOREIGN KEY("uID") REFERENCES "user"("uID") 
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("gID") REFERENCES "group"("gID") 
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE group_topic(
  "gtID" SERIAL PRIMARY KEY,
  "gID" INTEGER,
  "tID" INTEGER,
  "uID" INTEGER,
  "added" TEXT,
  FOREIGN KEY("uID") REFERENCES "user"("uID") 
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("gID") REFERENCES "group"("gID") 
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("tID") REFERENCES "topic"("tID") 
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "accessCode" (
	"aID" SERIAL PRIMARY KEY,
  "code" TEXT,
  "codeType" INTEGER, 
	"uID_creator" INTEGER, 
  "uID_user" INTEGER,
  "gID" INTEGER, 
  "adminLevel" INTEGER DEFAULT 0,
  "created" TEXT,
  "used" TEXT,
  "note" TEXT,
  FOREIGN KEY("uID_creator") REFERENCES "user"("uID")
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("uID_user") REFERENCES "user"("uID")
    ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("gID") REFERENCES "group"("gID")
    ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "concept" (
	"cID" SERIAL PRIMARY KEY,
  "sID" INTEGER,
	"tID" INTEGER,
  "order" INTEGER,
  "concept" TEXT,  
  "status" INTEGER DEFAULT 0,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT,
  FOREIGN KEY("tID") REFERENCES "topic"("tID") 
		ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "discussion" (
	"dID" SERIAL PRIMARY KEY,
	"tID" INTEGER,
  "sID" INTEGER,
  "start" TEXT,
  "end" TEXT,
  FOREIGN KEY("tID") REFERENCES "topic"("tID") 
	  ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "message" (
	"mID" SERIAL PRIMARY KEY,
	"dID" INTEGER,
  "cID" INTEGER,
  "isBot" INTEGER,
  "timestamp" TEXT,
  "message" TEXT,
  "progressCode" INTEGER,
  "progressMessage" TEXT,
  FOREIGN KEY("dID") REFERENCES "discussion"("dID") 
	  ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("cID") REFERENCES "concept"("cID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "question" (
	"qID" SERIAL PRIMARY KEY,
  "sID" INTEGER,
  "tID" INTEGER,
  "cID" INTEGER,
  "question" TEXT,
  "answer" TEXT,
  "status" INTEGER,
	"created" TEXT,
  "modified" TEXT,
  "optionA" TEXT,
  "explanationA" TEXT,
  "optionB" TEXT,
  "explanationB" TEXT,
  "optionC" TEXT,
  "explanationC" TEXT,
  "optionD" TEXT,
  "explanationD" TEXT,
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
	  ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("tID") REFERENCES "topic"("tID") 
	  ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("cID") REFERENCES "concept"("cID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "response" (
	"rID" SERIAL PRIMARY KEY,
  "sID" INTEGER NOT NULL,
  "qID" INTEGER NOT NULL,  
  "response" TEXT,
  "correct" INTEGER,
  "start" TEXT,
  "check" TEXT,
  "end" TEXT,
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
	  ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY("qID") REFERENCES "question"("qID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "backup" (
	"bID" SERIAL PRIMARY KEY,
  "sID" INTEGER NOT NULL,
  "modified" TEXT NOT NULL,
  "table" TEXT NOT NULL,
  "rowID" INTEGER NOT NULL,
  "attribute" TEXT NOT NULL,
	"created" TEXT,
  "isBot" INTEGER,
  "tValue" TEXT,
  "iValue" INTEGER,
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "feedback_general" (
	"fgID" SERIAL PRIMARY KEY,
  "sID" INTEGER NOT NULL,
  "code" INTEGER NOT NULL,
  "status" INTEGER DEFAULT 0,
  "created" TEXT NOT NULL,
  "email" TEXT NOT NULL,  
  "details" TEXT,
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "feedback_chat" (
	"fcID" SERIAL PRIMARY KEY,
  "dID" INTEGER NOT NULL,
  "code" INTEGER NOT NULL,
  "created" TEXT NOT NULL,  
  "details" TEXT,
  FOREIGN KEY("dID") REFERENCES "discussion"("dID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

-- We can't add a mID foreign key because the first time 
-- the value is inserted it's a placeholder which gets updated 
CREATE TABLE "feedback_chat_msg" (
	"fcmID" SERIAL PRIMARY KEY,
  "fcID" INTEGER NOT NULL,
  "mID" INTEGER NOT NULL, 
  FOREIGN KEY("fcID") REFERENCES "feedback_chat"("fcID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

-- INSERT BASE USER AND ADMIN
INSERT INTO "user" ("username", "password", "adminLevel", "created", "modified") 
VALUES ('anonymous', NULL, 0, to_char(now(), 'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS')), 
('admin', '$2b$12$RIcoDnGHaNbuYUGzm0Ijdejw68fEpqyyAFWrS/8uteQLhtDBUI4KW', 3, 
to_char(now(), 'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));

\c accorns;

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

GRANT CONNECT ON DATABASE accorns TO scuirrel;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scuirrel;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scuirrel;

GRANT CONNECT ON DATABASE accorns TO accorns;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO accorns;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO accorns;
