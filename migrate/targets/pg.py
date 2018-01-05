
import psycopg2

def get_current_step(params):
    with psycopg2.connect(
        dbname=params.path[1:],
        user=params.username,
        password=params.password,
        host=params.hostname,
        port=params.port
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute('create table if not exists current_migration (name varchar)')
            cursor.execute('select name from current_migration union all select null fetch first 1 row only')
            return cursor.fetchone()[0]


def put_current_step(step, params):
    with psycopg2.connect(
        dbname=params.path[1:],
        user=params.username,
        password=params.password,
        host=params.hostname,
        port=params.port
    ) as conn:
        with conn.cursor() as cursor:
            cursor.execute('create table if not exists current_migration (name varchar)')
            cursor.execute('delete from current_migration')
            cursor.execute('insert into current_migration values (%s)', [step])

