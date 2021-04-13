package api

import (
	"github.com/volatiletech/null"
)

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
	Id string `json:"id"`
}

type AppendOffsetRequest struct {
	Append AppendRequest `json: "append"`
	Offset int64         `json: "offset"`
}

type AppendsRequest struct {
	AppendRequests []AppendOffsetRequest `json:"append_requests"`
}

type AppendsResponse struct {
	Ids []string `json:"ids"`
}
