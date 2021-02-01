package api

import (
	"github.com/gin-gonic/gin"
)

func SetupRoutes(router *gin.Engine) {
	router.POST("/append", AppendHandler)
	router.GET("/health_check", HealthCheckHandler)
}
