CREATE SEQUENCE seq_fID START 1;
CREATE TABLE file (
  "fID" INTEGER PRIMARY KEY,
  "fileName" TEXT,
  "title" TEXT,
  "subtitle" TEXT,
  "created" TEXT,
  "modified" TEXT
);

CREATE SEQUENCE seq_kID START 1;
CREATE TABLE keyword (
  "kID" INTEGER PRIMARY KEY,
  "fID" INTEGER,
  "keyword" TEXT,
  FOREIGN KEY("fID") REFERENCES "file"("fID") 
);
