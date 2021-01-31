# chronicles
https://bit.ly/bb-chronicles-dd

### Development Environment
In local dev env we use docker-compose to have our dependencies setup for us.

Fire up all services
```shell script
docker-compose up -d
```

CLI access to local dev db
```shell script
docker-compose exec db psql -U user -d chronicles
```

#### Try out the API
To try out authenticated endpoints on your local environment set the `SKIP_AUTH=true` environment variable.
This will allow every request to any endpoint.

However, on production, you must send a valid `Authorization` header.
You can get one by inspecting network traffic in browser after login in. 
Copy paste the value of the `Authorization` header and use that.


### DB Migrations

DB Migrations are managed by [migrate](https://github.com/golang-migrate/migrate)

On mac install with brew. For other platforms see the project homepage.
```shell script
brew install golang-migrate
```

Create a new migration by
```shell script
migrate create -ext .sql -dir migrations -format 20060102150405 <migration_name_goes_here>
```

Run migrations
```shell script
migrate -database "postgres://user:password@localhost/chronicles?sslmode=disable" -path migrations up
```

Regenerate models

```shell script
sqlboiler psql
```

Download instructions for sqlboiler can be found [here](https://github.com/volatiletech/sqlboiler#download).

