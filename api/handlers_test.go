package api

import (
	"testing"

	"github.com/stretchr/testify/suite"
)

type HandlersSuite struct {
	suite.Suite
}

// In order for 'go test' to run this suite, we need to create
// a normal test function and pass our suite to suite.Run
func TestHandlers(t *testing.T) {
	suite.Run(t, new(HandlersSuite))
}

func (suite *HandlersSuite) TestHandleSearch() {
	suite.Nil(nil)
}
