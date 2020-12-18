package middleware

import (
	"database/sql"

	"github.com/gin-gonic/gin"
)

func ContextMiddleware(db *sql.DB) gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Set("DB", db)
		c.Next()
	}
}
