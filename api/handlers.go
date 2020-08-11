package api

import (
	"database/sql"
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog/log"
)

// Responds with JSON of given response or aborts the request with the given error.
func concludeRequest(c *gin.Context, resp interface{}, err *HttpError) {
	if err == nil {
		c.JSON(http.StatusOK, resp)
	} else {
		err.Abort(c)
	}
}

// More
type Request struct {
}

type Response struct {
	//Feed []core.ContentItem `json:"feed"`
}

func Handler(c *gin.Context) {
	r := Request{}
	if c.Bind(&r) != nil {
		return
	}

	resp, err := handle(c.MustGet("MDB_DB").(*sql.DB), r)
	concludeRequest(c, resp, err)
}

func handle(db *sql.DB, r Request) (*Response, *HttpError) {
	log.Info().Msgf("r: %+v", r)
	/*feed := core.MakeFeed(db)
	if cis, err := feed.More(r); err != nil {
		return nil, NewInternalError(err)
	} else {*/
	return &Response{}, nil
	//}
}
