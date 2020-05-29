pragma foreign_keys=off;

create table test_tmp(id int);
insert into test_tmp(id)
select id
from test;

drop table test;
alter table test_tmp rename to test;

pragma foreign_keys=on;
