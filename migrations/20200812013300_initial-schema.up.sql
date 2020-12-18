DROP TABLE IF EXISTS entries;
CREATE TABLE IF NOT EXISTS entries
(
    id                CHAR(27) PRIMARY KEY,                            -- ULID
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,

    user_id           VARCHAR(64)                            NOT NULL, -- accounts service id (keyclock), or any other client side id which will be appended as "client:<local client id>"
    ip_addr           INET                                   NOT NULL,
    user_agent        TEXT                                   NOT NULL,
    namespace         VARCHAR(64)                            NOT NULL, -- Client namespace, nested, e.g., "archive_v1.2.3.search"

    client_event_id   VARCHAR(64)                            NULL,     -- *ONE TO ONE* with id, optional for clients.
    client_event_type VARCHAR(64)                            NOT NULL, -- Click, keypress, play, stop, ...
    client_flow_id    VARCHAR(64)                            NULL,     -- Id for group of events, such as "search" which includes clicks and page views and many events/entries.
    client_flow_type  VARCHAR(64)                            NULL,     -- Type for group of events such as "search", "page visit", "watch content"
    client_session_id VARCHAR(64)                            NULL,     -- Client optional id to identify user task (many entries together).

    data              JSONB                                  NULL      -- Any client data about the event, e.g., element clicked, query searched, video current time position, anything...
);
