package api

import (
	"github.com/gin-gonic/gin"
)

func SetupRoutes(router *gin.Engine) {
	router.POST("/append", AppendHandler)
	router.POST("/appends", AppendsHandler)
	router.GET("/health_check", HealthCheckHandler)
	router.POST("/scan", ScanHandler)
}
