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
	ID string `json:"id"`
}
