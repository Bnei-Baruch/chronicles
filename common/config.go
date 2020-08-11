package common

import (
	"os"
)

type config struct {
	DBUrl string
}

func newConfig() *config {
	return &config{
		DBUrl: "postgres://user:password@localhost/chronicles?sslmode=disable",
	}
}

var Config *config

func Init() {
	Config = newConfig()

	if val := os.Getenv("DB_URL"); val != "" {
		Config.DBUrl = val
	}
}
