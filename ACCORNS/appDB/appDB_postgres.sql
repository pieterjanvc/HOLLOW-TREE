DROP DATABASE IF EXISTS :dbName;
CREATE DATABASE :dbName;

DO
$$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'scuirrel') THEN
        DROP OWNED BY scuirrel;
        DROP ROLE scuirrel;
    END IF;
END
$$;

CREATE ROLE scuirrel WITH LOGIN PASSWORD :'appPass';
GRANT CONNECT ON DATABASE :dbName TO scuirrel;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO scuirrel;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO scuirrel;

\c :dbName;

CREATE TABLE "user" (
	"uID" SERIAL PRIMARY KEY,
	"username" TEXT UNIQUE,
  "isAdmin" INTEGER DEFAULT 0,
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
	FOREIGN KEY("uID") REFERENCES "user"("uID") 
		ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE "topic" (
	"tID" SERIAL PRIMARY KEY,
	"topic" TEXT,
  "archived" INTEGER DEFAULT 0,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT
);

CREATE TABLE "concept" (
	"cID" SERIAL PRIMARY KEY,
	"tID" INTEGER,
  "concept" TEXT,
  "archived" INTEGER DEFAULT 0,
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
  "archived" INTEGER,
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
INSERT INTO "user" ("username", "isAdmin", "created", "modified") 
VALUES ('anonymous', 0, to_char(now(), 'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS')), 
('admin', 1, to_char(now(), 'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));
