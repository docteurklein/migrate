
import os
import sys
import stat
import glob
import subprocess
import sqlite3
import contextlib


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

    plan_file = '%s/plan.db' % (base_dir)
    with contextlib.closing(sqlite3.connect(plan_file)) as conn:
        with conn as plan:
            plan.execute('create table if not exists steps (id integer primary key autoincrement, created_at datetime, name string unique)')
            plan.execute('insert into steps(name, created_at) values (?, datetime(?))', [step, 'now'])
            print('Added %s to %s' % (step, plan_file), file=sys.stderr)


def up_to_latest(base_dir, target, verbose=False):
    current = get_current_step(target)
    plan_file = '%s/plan.db' % (base_dir)
    with contextlib.closing(sqlite3.connect(plan_file)) as conn:
        with conn as plan:
            missing = plan.execute('select name from steps where id > (select id from steps where name = ?)', [current])
            for step in missing:
                try:
                    execute_step(base_dir, step[0], 'up', verbose)
                    execute_step(base_dir, step[0], 'verify', verbose)
                except Exception as e:
                    execute_step(base_dir, step[0], 'rollback', verbose)
                    raise e


def execute_step(base_dir, step, type, verbose=False):
    pattern = '%s/scripts/%s/*%s*' % (base_dir, step, type)
    scripts = glob.glob(pattern)
    if not scripts:
        raise Exception('missing scripts for step "%s", was searching for "%s"' % (step, pattern))

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


def get_current_step(target):
    return 'test3'


def up_to():
    pass


def rollback_to(name: str):
    pass


def rollback_to_first():
    pass
