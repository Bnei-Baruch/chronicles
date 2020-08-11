package common

import "github.com/volatiletech/sqlboiler/boil"

type DBInterface interface {
	boil.Executor
	boil.Beginner
	Close() error
}
