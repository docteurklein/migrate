
import os
import sys
import stat
import glob
import subprocess
import sqlite3
import contextlib
from urllib.parse import urlparse
from . import targets


def add(base_dir, step: str):
    files = ['up', 'rollback', 'verify']

    dirname = '%s/scripts/%s' % (base_dir, step)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

    for script in files:
        path = '%s/%s' % (dirname, script)
        if not os.path.exists(path):
            with open(path, 'w+') as file:
                file.write('#!/usr/bin/env sh\n\n')
                file.write('echo TODO\n')
                file.write('exit 1\n')
                os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

            print('Created %s' % (path), file=sys.stderr)

    plan_file = '%s/plan.sql' % (base_dir)
    with persisted_plan(plan_file, read_only=False) as plan:
        plan.execute("""
            insert into steps (name, created_at)
                values (?, datetime(?))
        """, [step, 'now'])

    print('Added %s to %s' % (step, plan_file), file=sys.stderr)


def get_current_step(target):
    params = urlparse(target)
    return getattr(targets, params.scheme).get_current_step(params)


def put_current_step(target, step):
    params = urlparse(target)
    return getattr(targets, params.scheme).put_current_step(step, params)


def up_to_latest(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id > (select id from steps where name = ? union all select 0)
                order by id asc
        """, [current])
        execute_missing(target, base_dir, [row[0] for row in steps], verbose)


def up_to(base_dir, target, step, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id >  (select id from steps where name = ? union all select 0)
                and   id <= (select id from steps where name = ? union all select max(id) from steps)
                order by id asc
        """, [current, step])
        execute_missing(target, base_dir, [row[0] for row in steps], verbose)


def rollback_to(base_dir, target, step: str, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    if not current:
        return
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id >  (select id from steps where name = ? union all select 0)
                and   id <= (select id from steps where name = ? union all select max(id) from steps)
                order by id desc
        """, [step, current])
        for row in steps:
            execute_step(target, base_dir, row[0], 'rollback', verbose)

    put_current_step(target, step)


def rollback_to_first(base_dir, target, verbose=False):
    plan_file = '%s/plan.sql' % (base_dir)
    current = get_current_step(target)
    if not current:
        return
    with persisted_plan(plan_file) as plan:
        steps = plan.execute("""
            select name from steps
                where id <= (select id from steps where name = ? union all select max(id) from steps)
                order by id desc
        """, [current])
        for row in steps:
            execute_step(target, base_dir, row[0], 'rollback', verbose)

    put_current_step(target, '')


def execute_missing(target, base_dir, steps, verbose):
    executed = []
    for step in steps:
        try:
            execute_step(target, base_dir, step, 'up', verbose)
            execute_step(target, base_dir, step, 'verify', verbose)
            executed.append(step)
        except Exception as e:
            execute_step(target, base_dir, step, 'rollback', verbose)
            for to_rollback in reversed(executed):
                execute_step(target, base_dir, to_rollback, 'rollback', verbose)
            raise e


def execute_step(target, base_dir, step, type, verbose=False):
    pattern = '%s/scripts/%s/*%s*' % (base_dir, step, type)
    scripts = glob.glob(pattern)
    if not scripts:
        raise Exception(
            'missing scripts for step "%s", was searching for "%s"'
            % (step, pattern)
        )

    for script in scripts:
        print('running %s' % script, file=sys.stderr)
        process = subprocess.run(
            script,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if verbose:
            print(process.stdout.decode(), file=sys.stderr)

        if process.returncode != 0:
            raise Exception

    if type in ['verify', 'rollback']:
        put_current_step(target, step)


@contextlib.contextmanager
def persisted_plan(plan_file, read_only=True):
    with contextlib.closing(sqlite3.connect(':memory:')) as conn:
        with conn as plan:

            if os.path.exists(plan_file):
                with open(plan_file, 'r') as file:
                    plan.executescript(file.read())

            plan.execute("""
                create table if not exists steps (
                    id integer primary key autoincrement,
                    created_at datetime,
                    name string unique
                )
            """)

            yield plan

            if not read_only:
                with open(plan_file, 'w+') as file:
                    for line in plan.iterdump():
                        if 'sqlite_sequence' not in line:
                            file.write('%s\n' % line)

