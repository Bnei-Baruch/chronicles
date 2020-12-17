package common

import (
	"os"
)

type config struct {
	ListenAddress string
	GinServerMode string
	DBUrl         string
}

func newConfig() *config {
	return &config{
		ListenAddress: ":8080",
		GinServerMode: "debug",
		DBUrl:         "postgres://user:password@localhost/chronicles?sslmode=disable",
	}
}

var Config *config

func Init() {
	Config = newConfig()

	if val := os.Getenv("LISTEN_ADDRESS"); val != "" {
		Config.ListenAddress = val
	}
	if val := os.Getenv("GIN_SERVER_MODE"); val != "" {
		Config.GinServerMode = val
	}
	if val := os.Getenv("DB_URL"); val != "" {
		Config.DBUrl = val
	}
}
