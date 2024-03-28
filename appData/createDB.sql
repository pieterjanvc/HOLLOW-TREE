DROP TABLE IF EXISTS "user";
CREATE TABLE IF NOT EXISTS "user" (
	"uID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"username" TEXT UNIQUE,
  "email" TEXT,
  "created" TEXT
);

DROP TABLE IF EXISTS "session";
CREATE TABLE IF NOT EXISTS "session" (
	"sID" INTEGER PRIMARY KEY AUTOINCREMENT,
  "uID" INTEGER,
  "start" TEXT,
  "end" TEXT,
  "shinyToken" TEXT,
	FOREIGN KEY("uID") REFERENCES "user"("uID") 
		ON DELETE CASCADE ON UPDATE CASCADE
);

DROP TABLE IF EXISTS "topic";
CREATE TABLE IF NOT EXISTS "topic" (
	"tID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"topic" TEXT,
  "archived" TEXT DEFAULT 0,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT
);

DROP TABLE IF EXISTS "concept";
CREATE TABLE IF NOT EXISTS "concept" (
	"cID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"tID" TEXT,
  "concept" TEXT,
  "archived" TEXT DEFAULT 0,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT,
  FOREIGN KEY("tID") REFERENCES "topic"("tID") 
		ON DELETE CASCADE ON UPDATE CASCADE
);

DROP TABLE IF EXISTS "discussion";
CREATE TABLE IF NOT EXISTS "discussion" (
	"dID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"tID" INTEGER,
  "sID" INTEGER,
  "start" TEXT,
  "end" TEXT,
  FOREIGN KEY("tID") REFERENCES "topic"("tID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
  FOREIGN KEY("sID") REFERENCES "session"("sID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);

DROP TABLE IF EXISTS "message";
CREATE TABLE IF NOT EXISTS "message" (
	"mID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"dID" INTEGER,
  "isBot" INTEGER,
  "timestamp" TEXT,
  "message" TEXT,
  FOREIGN KEY("dID") REFERENCES "discussion"("dID") 
	  ON DELETE CASCADE ON UPDATE CASCADE
);
