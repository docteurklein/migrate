BEGIN TRANSACTION;
CREATE TABLE steps (
                    id integer primary key autoincrement,
                    created_at datetime,
                    name string unique
                );
INSERT INTO "steps" VALUES(1,'2018-01-14 15:02:39','test1');
INSERT INTO "steps" VALUES(2,'2019-02-13 16:03:40','test2');
COMMIT;
