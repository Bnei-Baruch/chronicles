package common

import "github.com/volatiletech/sqlboiler/v4/boil"

type DBInterface interface {
	boil.Executor
	boil.Beginner
	Close() error
}
