package api

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"reflect"
	"time"

	"github.com/gin-gonic/gin"
	pkgerr "github.com/pkg/errors"
	"github.com/rs/zerolog"
	"github.com/segmentio/ksuid"
	"github.com/volatiletech/null/v8"
	"github.com/volatiletech/sqlboiler/v4/boil"
	"github.com/volatiletech/sqlboiler/v4/queries/qm"

	"github.com/Bnei-Baruch/chronicles/models"
	"github.com/Bnei-Baruch/chronicles/pkg/httputil"
	"github.com/Bnei-Baruch/chronicles/pkg/sqlutil"
)

const (
	DEFAULT_LIMIT         = 500
	CLIENT_USER_ID_PREFIX = "client:"
)

func ToInterfaceSlice(s interface{}) []interface{} {
	slice := reflect.ValueOf(s)
	if slice.Kind() != reflect.Slice {
		panic("Expected slice!")
	}
	c := slice.Len()
	out := make([]interface{}, c)
	for i := 0; i < c; i++ {
		out[i] = slice.Index(i).Interface()
	}
	return out
}

func ScanHandler(c *gin.Context) {
	r := ScanRequest{}
	if c.Bind(&r) != nil {
		return
	}

	db := c.MustGet("DB").(*sql.DB)
	mods := []qm.QueryMod{qm.Where("TRUE")}
	if r.Id != "" {
		mods = append(mods, qm.And("id > ?", r.Id))
	}
	if len(r.Namespaces) > 0 {
		mods = append(mods, qm.AndIn("namespace in ?", ToInterfaceSlice(r.Namespaces)...))
	}
	if len(r.UserIds) > 0 {
		mods = append(mods, qm.AndIn("user_id in ?", ToInterfaceSlice(r.UserIds)...))
	}
	if len(r.EventTypes) > 0 {
		mods = append(mods, qm.AndIn("client_event_type in ?", ToInterfaceSlice(r.EventTypes)...))
	}
	if r.Keycloak.Valid {
		if r.Keycloak.Bool {
			mods = append(mods, qm.And(fmt.Sprintf("user_id not like '%s%%'", CLIENT_USER_ID_PREFIX)))
		} else {
			mods = append(mods, qm.And(fmt.Sprintf("user_id like '%s%%'", CLIENT_USER_ID_PREFIX)))
		}
	}
	limit := DEFAULT_LIMIT
	if r.Limit != 0 {
		limit = r.Limit
	}
	mods = append(mods, qm.OrderBy("id asc"), qm.Limit(limit))
	if entries, err := models.Entries(mods...).All(db); err != nil {
		concludeRequest(c, nil, httputil.NewInternalError(err))
	} else {
		if entries == nil {
			entries = []*models.Entry{}
		}
		concludeRequest(c, ScanResponse{entries}, nil)
	}
}

func HealthCheckHandler(c *gin.Context) {
	ctx, cancel := context.WithTimeout(context.TODO(), time.Second)
	defer cancel()

	db := c.MustGet("DB").(*sql.DB)
	err := db.PingContext(ctx)
	if err == nil {
		err = ctx.Err()
	}

	if err != nil {
		c.AbortWithError(http.StatusFailedDependency, pkgerr.Wrap(err, "DB ping")).SetType(gin.ErrorTypePublic)
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func AppendsHandler(c *gin.Context) {
	r := AppendsRequest{}
	if c.Bind(&r) != nil {
		return
	}

	resp, err := handleAppends(c, r)
	concludeRequest(c, resp, err)
}

func handleAppends(c *gin.Context, r AppendsRequest) (*AppendsResponse, *httputil.HttpError) {
	now := time.Now()
	var resp AppendsResponse
	for _, appendOffsetRequest := range r.AppendRequests {
		then := now.Add(time.Duration(appendOffsetRequest.Offset) * time.Millisecond)
		if appendResponse, err := handleAppend(c, then, appendOffsetRequest.Append); err != nil {
			return nil, err
		} else {
			resp.Ids = append(resp.Ids, appendResponse.Id)
		}
	}
	return &resp, nil
}

func AppendHandler(c *gin.Context) {
	r := AppendRequest{}
	if c.Bind(&r) != nil {
		return
	}

	resp, err := handleAppend(c, time.Now(), r)
	concludeRequest(c, resp, err)
}

func handleAppend(c *gin.Context, now time.Time, r AppendRequest) (*AppendResponse, *httputil.HttpError) {
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
	if r.Data.Valid {
		if _, err := json.Marshal(r.Data); err != nil {
			return nil, httputil.NewBadRequestError(errors.New("expected data to be a valid json"))
		}
	}

	entry := models.Entry{
		ID:              ksuid.New().String(),
		CreatedAt:       now,
		IPAddr:          c.ClientIP(),
		UserAgent:       c.Request.UserAgent(),
		Namespace:       r.Namespace,
		ClientEventID:   r.ClientEventID,
		ClientEventType: r.ClientEventType,
		ClientFlowID:    r.ClientFlowID,
		ClientFlowType:  r.ClientFlowType,
		ClientSessionID: r.ClientSessionID,
		Data:            r.Data,
	}

	if valueOrEmpty(r.KeycloakId) != "" {
		entry.UserID = valueOrEmpty(r.KeycloakId)
	} else {
		entry.UserID = fmt.Sprintf("%s%s", CLIENT_USER_ID_PREFIX, valueOrEmpty(r.ClientId))
	}

	db := c.MustGet("DB").(*sql.DB)
	log := c.MustGet("LOGGER").(zerolog.Logger)
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
