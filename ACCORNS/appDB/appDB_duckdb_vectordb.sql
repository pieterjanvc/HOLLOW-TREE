DROP TABLE IF EXISTS "documents";
CREATE TABLE "documents" (
  "node_id" VARCHAR, 
  "text" VARCHAR, 
  "embedding" FLOAT[], 
  "metadata_" JSON
  );

DROP SEQUENCE IF EXISTS seq_fID;
DROP TABLE IF EXISTS metadata;
CREATE SEQUENCE seq_fID START 1;
CREATE TABLE file (
  "fID" INTEGER PRIMARY KEY,
  "fileName" TEXT,
  "title" TEXT,
  "subtitle" TEXT,
  "shinyToken" TEXT,
  "created" TEXT,
  "modified" TEXT
);

DROP SEQUENCE IF EXISTS seq_kID;
DROP TABLE IF EXISTS keyword;
CREATE SEQUENCE seq_kID START 1;
CREATE TABLE keyword (
  "kID" INTEGER PRIMARY KEY,
  "fID" INTEGER,
  "keyword" TEXT,
  FOREIGN KEY("fID") REFERENCES "file"("fID") 
);
