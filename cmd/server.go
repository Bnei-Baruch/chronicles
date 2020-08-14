package cmd

import (
	"database/sql"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	_ "github.com/lib/pq"
	"github.com/rs/zerolog/log"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"github.com/Bnei-Baruch/chronicles/api"
	"github.com/Bnei-Baruch/chronicles/common"
	"github.com/Bnei-Baruch/chronicles/utils"
	"github.com/Bnei-Baruch/chronicles/version"
)

var serverCmd = &cobra.Command{
	Use:   "server",
	Short: "Feed api server",
	Run:   serverFn,
}

var bindAddress string

func init() {
	serverCmd.PersistentFlags().StringVar(&bindAddress, "bind_address", "", "Bind address for server.")
	viper.BindPFlag("server.bind-address", serverCmd.PersistentFlags().Lookup("bind_address"))
	rootCmd.AddCommand(serverCmd)
}

func serverFn(cmd *cobra.Command, args []string) {
	log.Info().Msgf("Starting Chronicles server version %s", version.Version)
	common.Init()
	// defer common.Shutdown()

	// TODO: Setup Rollbar
	// rollbar.Token = viper.GetString("server.rollbar-token")
	// rollbar.Environment = viper.GetString("server.rollbar-environment")
	// rollbar.CodeVersion = version.Version

	log.Info().Msgf("Connecting to %s", common.Config.DBUrl)
	db, err := sql.Open("postgres", common.Config.DBUrl)
	if err != nil {
		log.Fatal().Err(err).Msg("sql.Open")
	}

	// Setup gin
	gin.SetMode(viper.GetString("server.mode"))
	router := gin.New()
	router.Use(
		utils.LoggerMiddleware(),
		utils.DataStoresMiddleware(db),
		utils.ErrorHandlingMiddleware(),
		cors.Default(),
		utils.RecoveryMiddleware())

	api.SetupRoutes(router)

	log.Info().Msg("Running application")
	if cmd != nil {
		router.Run(viper.GetString("server.bind-address"))
	}

	// This would be reasonable once we'll have graceful shutdown implemented
	// if len(rollbar.Token) > 0 {
	// 	rollbar.Wait()
	// }
}
