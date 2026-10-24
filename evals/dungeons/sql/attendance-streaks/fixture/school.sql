CREATE TABLE attendance (student_id INTEGER NOT NULL, day TEXT NOT NULL, present INTEGER NOT NULL,
                         PRIMARY KEY (student_id, day));
INSERT INTO attendance VALUES (1,'2026-10-04',1),(1,'2026-10-05',1),(1,'2026-10-06',0),(2,'2026-10-04',1);
