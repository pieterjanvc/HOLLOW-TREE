-- INSERT DEMO DATA
INSERT INTO topic("topic", "created", "modified")
VALUES('The central dogma of molecular biology', 
  CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO "concept" ("tID", "concept", "created", "modified")
 VALUES (1,'Central dogma of molecular biology: DNA makes RNA makes Protein',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'Genes: Hold code for specific functional molecular products (RNA and Protein)',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'RNA: Composed of nucleotides (including uracil, U). Single-stranded',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'Transcription: RNA polymerase unwinds DNA double helix. Synthesizes complementary RNA strand',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'RNA splicing: Removes introns, Retains exons',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'Translation: Occurs in ribosomes, Deciphers mRNA to assemble protein',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'Amino acids: Building blocks of proteins. Linked by peptide bonds',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),
  (1,'Protein folding: Adopts specific three-dimensional structure',
  CURRENT_TIMESTAMP,CURRENT_TIMESTAMP);
