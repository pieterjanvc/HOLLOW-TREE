DROP TABLE IF EXISTS "user";
CREATE TABLE IF NOT EXISTS "user" (
	"uID" SERIAL PRIMARY KEY,
	"username" TEXT UNIQUE,
  "isAdmin" INTEGER DEFAULT 0,
  "email" TEXT,
  "created" TEXT,
  "modified" TEXT
);

DROP TABLE IF EXISTS "session";
CREATE TABLE IF NOT EXISTS "session" (
	"sID" SERIAL PRIMARY KEY,
  "uID" INTEGER,
  "appID" INTEGER,
  "start" TEXT,
  "end" TEXT,
  "shinyToken" TEXT,
	FOREIGN KEY("uID") REFERENCES "user"("uID") 
		ON DELETE CASCADE ON UPDATE CASCADE
);

DROP TABLE IF EXISTS "topic";
CREATE TABLE IF NOT EXISTS "topic" (
	"tID" SERIAL PRIMARY KEY,
	"topic" TEXT,
  "archived" INTEGER DEFAULT 0,
  "created" TEXT,
  "modified" TEXT,
  "description" TEXT
);

DROP TABLE IF EXISTS "concept";
CREATE TABLE IF NOT EXISTS "concept" (
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

DROP TABLE IF EXISTS "discussion";
CREATE TABLE IF NOT EXISTS "discussion" (
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

DROP TABLE IF EXISTS "message";
CREATE TABLE IF NOT EXISTS "message" (
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

DROP TABLE IF EXISTS "question";
CREATE TABLE IF NOT EXISTS "question" (
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

DROP TABLE IF EXISTS "response";
CREATE TABLE IF NOT EXISTS "response" (
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

DROP TABLE IF EXISTS "backup";
CREATE TABLE IF NOT EXISTS "backup" (
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

DROP TABLE IF EXISTS "feedback_general";
CREATE TABLE IF NOT EXISTS "feedback_general" (
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

DROP TABLE IF EXISTS "feedback_chat";
CREATE TABLE IF NOT EXISTS "feedback_chat" (
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
DROP TABLE IF EXISTS "feedback_chat_msg";
CREATE TABLE IF NOT EXISTS "feedback_chat_msg" (
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

-- INSERT DEMO DATA (OPTIONAL)
INSERT INTO topic("topic", "created", "modified")
VALUES('The central dogma of molecular biology', to_char(now(), 
  'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));

INSERT INTO "concept" ("tID", "concept", "created", "modified")
 VALUES (1,'Central dogma of molecular biology: DNA makes RNA makes Protein',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Genes: Hold code for specific functional molecular products (RNA and Protein)',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'RNA: Composed of nucleotides (including uracil, U); Single-stranded',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Transcription: RNA polymerase unwinds DNA double helix; Synthesizes complementary RNA strand',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'RNA splicing: Removes introns; Retains exons',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Translation: Occurs in ribosomes; Deciphers mRNA to assemble protein',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Amino acids: Building blocks of proteins; Linked by peptide bonds',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Protein folding: Adopts specific three-dimensional structure',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));
  