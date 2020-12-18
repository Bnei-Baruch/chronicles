package cmd

import (
	"context"
	"database/sql"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	_ "github.com/lib/pq"
	"github.com/rs/zerolog/log"
	"github.com/spf13/cobra"

	"github.com/Bnei-Baruch/chronicles/api"
	"github.com/Bnei-Baruch/chronicles/common"
	"github.com/Bnei-Baruch/chronicles/middleware"
	"github.com/Bnei-Baruch/chronicles/version"
)

var serverCmd = &cobra.Command{
	Use:   "server",
	Short: "Chronicles server",
	Run:   serverFn,
}

func init() {
	rootCmd.AddCommand(serverCmd)
}

func serverFn(cmd *cobra.Command, args []string) {
	log.Info().Msgf("Starting Chronicles server version %s", version.Version)

	log.Debug().Msgf("Config\n%v", common.Config)

	db, err := sql.Open("postgres", common.Config.DBUrl)
	if err != nil {
		log.Fatal().Err(err).Msg("sql.Open")
	}
	defer db.Close()
	// boil.DebugMode = true

	// Setup gin
	gin.SetMode(common.Config.GinServerMode)
	router := gin.New()
	router.Use(
		middleware.LoggingMiddleware(),
		middleware.RecoveryMiddleware(),
		middleware.ErrorHandlingMiddleware(),
		cors.Default(),
		middleware.ContextMiddleware(db))

	api.SetupRoutes(router)

	addr := common.Config.ListenAddress
	log.Info().Msgf("Running application %s", addr)
	srv := &http.Server{
		Addr:    addr,
		Handler: router,
	}

	// Initializing the server in a goroutine so that
	// it won't block the graceful shutdown handling below
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal().Err(err).Msg("ListenAndServe")
		}
	}()

	// Wait for interrupt signal to gracefully shutdown the server with a timeout of 5 seconds.
	quit := make(chan os.Signal)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Info().Msg("Shutting down server...")

	// The context is used to inform the server it has 5 seconds to finish
	// the request it is currently handling
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal().Err(err).Msg("Server forced to shutdown")
	}

	log.Info().Msg("Server exiting")
}
