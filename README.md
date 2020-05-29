# migrate

## What ?

A migration runner, not especially targeting sql databases.

## How ?

    docker run -v $PWD:/usr/src/app -u 1000:1000 docteurklein/migrate

### Add a new migration step

    migrate add 'create_missing_indexes' sh

### Execute migrations

    migrate pg://prod up-to 'some_next_step'
    migrate pg://prod up-to --latest

### Rollback migrations

    migrate pg://prod rollback-to 'some_previous_step'
    migrate pg://prod rollback-to --first
    migrate pg://prod rollback-to --previous


## File structure


You can specify many scripts per step that matches the glob pattern:

    migrations/*/*up*
    migrations/*/*rollback*
    migrations/*/*verify*

Use numeric prefixes to guarantee the order of execution, for example:

 - `migrations/create_missing_indexes/1-up.sh`
 - `migrations/create_missing_indexes/2-up.sh`


## Planning

A local plan file is compared to the target's state and decides which steps are yet to be executed.

Steps are executed sequentially.

After each step execution, the `verify` script is invoked.

If `verify` exits with a status code different than `0`, the rollback script is executed, and the whole migration stops.


## Targets

The target is represented by an URL (containing credentials and configuration).
The target is the thing we want to mutate.
The target stores the name of the last migrated step.

Currently supported targets are:

### postgres target
    
example: `migrate pg://user:password@hostname/db_name status`

#### Environment variables

Those variables take precedence over the values passed in URL.

 - `POSTGRES_DBNAME`
 - `POSTGRES_USER`
 - `POSTGRES_PASSWORD`
 - `POSTGRES_PASSWORD_FILE` (wins over `POSTGRES_PASSWORD`)
 - `POSTGRES_HOST`
 - `POSTGRES_PORT`
 
### sqlite target

example: `migrate sqlite:path/to/some_file.sqlite status`

### SQL scripts

Files ending with `.sql` are treated differently than others if the target supports it:
their contents are passed to the current transaction opened on the target.


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


Each step uses executable files with shebang (except `.sql` files) for a maximum flexibility.


## Contributing

### Running tests

    ./bin/tests
