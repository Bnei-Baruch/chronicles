package api

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog"
	"github.com/segmentio/ksuid"
	"github.com/volatiletech/null"
	"github.com/volatiletech/sqlboiler/boil"

	"github.com/Bnei-Baruch/chronicles/models"
	"github.com/Bnei-Baruch/chronicles/pkg/httputil"
	"github.com/Bnei-Baruch/chronicles/pkg/sqlutil"
)

func AppendHandler(c *gin.Context) {
	r := AppendRequest{}
	if c.Bind(&r) != nil {
		return
	}

	resp, err := handleAppend(c, r)
	concludeRequest(c, resp, err)
}

func handleAppend(c *gin.Context, r AppendRequest) (*AppendResponse, *httputil.HttpError) {
	if valueOrEmpty(r.KeycloakId) == "" && valueOrEmpty(r.ClientId) == "" {
		return nil, httputil.NewBadRequestError(errors.New("expected either keycloak_id or client_id to be set"))
	}
	if valueOrEmpty(r.KeycloakId) != "" && valueOrEmpty(r.ClientId) != "" {
		return nil, httputil.NewBadRequestError(errors.New("expected only one of keycloak_id or client_id to be set"))
	}
	if r.Namespace == "" {
		return nil, httputil.NewBadRequestError(errors.New("expected namespace to not be empty"))
	}
	if r.ClientEventType == "" {
		return nil, httputil.NewBadRequestError(errors.New("expected client_event_type to not be empty"))
	}

	entry := models.Entry{
		ID:              ksuid.New().String(),
		CreatedAt:       time.Now(),
		IPAddr:          c.ClientIP(),
		UserAgent:       c.Request.UserAgent(),
		Namespace:       r.Namespace,
		ClientEventID:   r.ClientEventID,
		ClientEventType: r.ClientEventType,
		ClientFlowID:    r.ClientFlowID,
		ClientFlowType:  r.ClientFlowType,
		ClientSessionID: r.ClientSessionID,
	}

	if valueOrEmpty(r.KeycloakId) != "" {
		entry.UserID = valueOrEmpty(r.KeycloakId)
	} else {
		entry.UserID = fmt.Sprintf("client:%s", valueOrEmpty(r.ClientId))
	}

	log := c.MustGet("LOGGER").(zerolog.Logger)

	entry.Data = r.Data
	if data, err := json.Marshal(entry.Data); err == nil {
		log.Info().Msgf("Namespace: %+v\nEvent: %+v %+v\nFlow: %+v %+v\nData: %s\nSession: %+v",
			r.Namespace, entry.ClientEventType, entry.ClientEventID, entry.ClientFlowType, entry.ClientFlowID, data, entry.ClientSessionID)
	} else {
		log.Warn().Msgf("json.Marshal(data) error: %+v", err)
	}

	db := c.MustGet("DB").(*sql.DB)
	err := sqlutil.InTx(db, log, func(tx *sql.Tx) error {
		return entry.Insert(tx, boil.Infer())
	})
	if err != nil {
		return nil, httputil.NewInternalError(err)
	}

	return &AppendResponse{entry.ID}, nil
}

func valueOrEmpty(s null.String) string {
	if p := s.Ptr(); p != nil {
		return *p
	}
	return ""
}

// Responds with JSON of given response or aborts the request with the given error.
func concludeRequest(c *gin.Context, resp interface{}, err *httputil.HttpError) {
	if err == nil {
		c.JSON(http.StatusOK, resp)
	} else {
		err.Abort(c)
	}
}
