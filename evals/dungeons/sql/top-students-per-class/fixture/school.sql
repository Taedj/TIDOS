CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT NOT NULL, class TEXT NOT NULL);
CREATE TABLE grades (student_id INTEGER NOT NULL REFERENCES students(id), subject TEXT, grade REAL);
INSERT INTO students VALUES (1,'Lina','L3-A'),(2,'Omar','L3-A'),(3,'Sara','L3-A'),(4,'Yacine','L3-A'),
                            (5,'Amine','L3-B'),(6,'Nour','L3-B');
INSERT INTO grades VALUES (1,'AI',15),(1,'DB',13),(2,'AI',12),(3,'AI',16),(3,'DB',12),
                          (4,'AI',9),(5,'AI',11),(6,'AI',11);
