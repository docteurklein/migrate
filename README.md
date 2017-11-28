# migrate

## What ?

A migration runner, not especially targeting sql databases.

## How ?

### Add a new migration step

    migrate add 'create_missing_indexes'

### Execute migrations

    migrate up-to 'some_next_step'
    migrate up-to --all

### Rollback migrations

    migrate rollback-to 'some_previous_step'


## File structure


You can specify many scripts per step that matches the glob pattern:

    migrations/*/*up*
    migrations/*/*rollback*
    migrations/*/*verify*

Use numeric prefixes to guarantee the order of execution, for example:

 - `migrations/create_missing_indexes/1-up.sql`
 - `migrations/create_missing_indexes/2-up.sql`


## Planning

A local plan file is compared to the target's state and decides which steps are yet to be executed.

Steps are executed sequentially.

After each step execution, the `verify` script is invoked.

If `verify` exits with a status code different than `0`, the rollback script is executed, and the whole migration stops.


## Examples

 - `migrations/create_missing_indexes/up`

```sh
#!/usr/bin/env sh

curl -X POST http://elasticsearch.local:9200/_reindex -d@- <<JSON
    {
      "source": {
        "index": "twitter"
      },
      "dest": {
        "index": "new_twitter"
      }
    }
JSON
```

 - `migrations/create_missing_indexes/rollback`

```sh
#!/usr/bin/env sh

curl -X POST http://elasticsearch.local:9200/_reindex -d@- <<JSON
    {
      "source": {
        "index": "new_twitter"
      },
      "dest": {
        "index": "twitter"
      }
    }
JSON
```

 - `migrations/create_missing_indexes/verify`

```sh
#!/usr/bin/env sh

curl -f -X GET http://elasticsearch.local:9200/twitter
```


### shebang


Each step uses executable files with shebang for a maximum flexibility.  
It means you could use any script that works with a shebang:

 - `#!/usr/bin/env sql --shebang pg://scott:tiger@pg.example.com/pgdb`
 - `#!/usr/bin/env psql -f "$0"
 - `#!/usr/bin/env sh
 - `#!/usr/bin/env python

Shebangs are however very limited (for passing credential f.e), so you might want to define your own binaries, for example:

 - `bin/custom-shebang-bin`:

```sh
#!/usr/bin/env sh
psql -u $DB_USER -p $DB_PASS -f "$0"
```

and then using it as a shebang for your scripts. This requires adding `./bin` to your `$PATH`.

