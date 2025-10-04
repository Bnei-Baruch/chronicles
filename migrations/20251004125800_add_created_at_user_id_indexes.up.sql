CREATE INDEX user_id_index ON entries (user_id);
CREATE INDEX user_id_created_at_desc_index ON entries (user_id, created_at DESC);
