package api

import (
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"math/rand"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/oklog/ulid"
	"github.com/rs/zerolog/log"
	"github.com/volatiletech/null"
	"github.com/volatiletech/sqlboiler/boil"
	"golang.org/x/net/context"

	"github.com/Bnei-Baruch/chronicles/models"
	"github.com/Bnei-Baruch/chronicles/pkg/sqlutil"
)

func init() {
	// boil.DebugMode = true
}

func ValueOrEmpty(s null.String) string {
	if p := s.Ptr(); p != nil {
		return *p
	}
	return ""
}

// Responds with JSON of given response or aborts the request with the given error.
func concludeRequest(c *gin.Context, resp interface{}, err *HttpError) {
	if err == nil {
		c.JSON(http.StatusOK, resp)
	} else {
		err.Abort(c)
	}
}

// Append
type AppendRequest struct {
	KeycloakId      null.String `json:"keycloak_id"`
	Namespace       string      `json:"namespace"`
	ClientId        null.String `json:"client_id"`
	ClientEventID   null.String `json:"client_event_id,omitempty"`
	ClientEventType string      `json:"client_event_type"`
	ClientFlowID    null.String `json:"client_flow_id,omitempty"`
	ClientFlowType  null.String `json:"client_flow_type,omitempty"`
	ClientSessionID null.String `json:"client_session_id,omitempty"`
	Data            null.JSON   `json:"data,omitempty"`
}

type AppendResponse struct {
	ID string `json:"id"`
}

func AppendHandler(c *gin.Context) {
	r := AppendRequest{}
	if c.Bind(&r) != nil {
		return
	}

	resp, err := handleAppend(c.MustGet("MDB_DB").(*sql.DB), r, c.ClientIP(), c.Request.UserAgent())
	concludeRequest(c, resp, err)
}

func handleAppend(db *sql.DB, r AppendRequest, clientIP string, userAgent string) (*AppendResponse, *HttpError) {
	if ValueOrEmpty(r.KeycloakId) == "" && ValueOrEmpty(r.ClientId) == "" {
		return nil, NewBadRequestError(errors.New("Expected either keycloak_id or client_id to be set."))
	}
	if ValueOrEmpty(r.KeycloakId) != "" && ValueOrEmpty(r.ClientId) != "" {
		return nil, NewBadRequestError(errors.New("Expected only one of keycloak_id or client_id to be set."))
	}
	if r.Namespace == "" {
		return nil, NewBadRequestError(errors.New("Expected namespace to not be empty."))
	}
	if r.ClientEventType == "" {
		return nil, NewBadRequestError(errors.New("Expected client_event_type to not be empty."))
	}

	var entry models.Entry
	now := time.Now()
	if id, err := ulid.New(ulid.Timestamp(now), ulid.Monotonic(rand.New(rand.NewSource(now.UnixNano())), 0)); err != nil {
		return nil, NewInternalError(err)
	} else {
		entry.ID = id.String()
	}
	if ValueOrEmpty(r.KeycloakId) != "" {
		entry.UserID = ValueOrEmpty(r.KeycloakId)
	} else {
		entry.UserID = fmt.Sprintf("client:%s", ValueOrEmpty(r.ClientId))
	}
	entry.CreatedAt = time.Now()
	entry.IPAddr = clientIP
	entry.UserAgent = userAgent
	entry.Namespace = r.Namespace
	entry.ClientEventID = r.ClientEventID
	entry.ClientEventType = r.ClientEventType
	entry.ClientFlowID = r.ClientFlowID
	entry.ClientFlowType = r.ClientFlowType
	entry.ClientSessionID = r.ClientSessionID
	entry.Data = r.Data

	if data, err := json.Marshal(entry.Data); err == nil {
		log.Info().Msgf("Namespace: %+v\nEvent: %+v %+v\nFlow: %+v %+v\nData: %s\nSession: %+v",
			r.Namespace, entry.ClientEventType, entry.ClientEventID, entry.ClientFlowType, entry.ClientFlowID, data, entry.ClientSessionID)
	} else {
		log.Warn().Msgf("Error marshling data: %+v", err)
	}

	err := sqlutil.InTx(context.TODO(), db, func(tx *sql.Tx) error {
		return entry.Insert(tx, boil.Infer())
	})
	if err != nil {
		return nil, NewInternalError(err)
	}

	return &AppendResponse{entry.ID}, nil
}
