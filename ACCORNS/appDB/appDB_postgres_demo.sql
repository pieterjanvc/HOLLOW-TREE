-- INSERT DEMO DATA

INSERT INTO "group" ("group", "created", "modified")
VALUES('Demo',  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'), 
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));

INSERT INTO topic("topic", "status", "created", "modified")
VALUES('The central dogma of molecular biology', 0, to_char(now(), 
  'YYYY-MM-DD HH24:MI:SS'), to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));

INSERT INTO "concept" ("tID", "order", "concept", "created", "modified")
 VALUES (1,1,'DNA is the molecule that carries the genetic information in every living organism',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,2,'Genes: Hold code for specific functional molecular products (RNA and Protein)',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,3,'RNA: Composed of nucleotides (including uracil, U). Single-stranded',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,4,'Transcription: RNA polymerase unwinds DNA double helix. Synthesizes complementary RNA strand',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,5,'Messenger RNA (mRNA): Carries genetic code from nucleus to cytoplasm',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,6,'RNA splicing: Removes introns. Retains exons',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,7,'Translation: Occurs in ribosomes. Deciphers mRNA to assemble protein',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,8,'Amino acids: Building blocks of proteins. Linked by peptide bonds',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,9,'Protein folding: Adopts specific three-dimensional structure',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS')),
  (1,10,'In summary: The central dogma states that DNA makes RNA makes Protein',
  to_char(now(), 'YYYY-MM-DD HH24:MI:SS'),to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));

INSERT INTO "group_topic" ("gID", "tID", "added")
VALUES(1, 1, to_char(now(), 'YYYY-MM-DD HH24:MI:SS'));
