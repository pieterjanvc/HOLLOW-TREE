-- INSERT DEMO DATA
INSERT INTO "group" ("group", "created", "modified")
VALUES('Demo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO "topic" ("topic", "status", "created", "modified")
VALUES('The central dogma of molecular biology', 0,
  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO "concept" ("tID", "order", "concept", "created", "modified")
 VALUES (1,1,'DNA is the molecule that carries the genetic information in every living organism',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,2,'Genes: Hold code for specific functional molecular products (RNA and Protein)',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,3,'RNA: Composed of nucleotides (including uracil, U). Single-stranded',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,4,'Transcription: RNA polymerase unwinds DNA double helix. Synthesizes complementary RNA strand',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,5,'Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,6,'RNA splicing: Removes introns, Retains exons',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,7,'Translation: Occurs in ribosomes, Deciphers mRNA to assemble protein',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,8,'Amino acids: Building blocks of proteins. Linked by peptide bonds',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,9,'Protein folding: Adopts specific three-dimensional structure',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,10,'In summary: The central dogma states that DNA makes RNA makes Protein',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);

INSERT INTO "group_topic" ("gID", "tID", "added")
VALUES(1, 1, CURRENT_TIMESTAMP);
