-- INSERT DEMO DATA
INSERT INTO topic("topic", "created", "modified")
VALUES('The central dogma of molecular biology', to_char(now(), 
  'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));

INSERT INTO "concept" ("tID", "concept", "created", "modified")
 VALUES (1,'Central dogma of molecular biology: DNA makes RNA makes Protein',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Genes: Hold code for specific functional molecular products (RNA and Protein)',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'RNA: Composed of nucleotides (including uracil, U). Single-stranded',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Transcription: RNA polymerase unwinds DNA double helix. Synthesizes complementary RNA strand',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'RNA splicing: Removes introns. Retains exons',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Translation: Occurs in ribosomes. Deciphers mRNA to assemble protein',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Amino acids: Building blocks of proteins. Linked by peptide bonds',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,'Protein folding: Adopts specific three-dimensional structure',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));
