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
