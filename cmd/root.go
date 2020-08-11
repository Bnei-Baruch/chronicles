package cmd

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"github.com/subosito/gotenv"

	"github.com/Bnei-Baruch/chronicles/common"
)

var rootCmd = &cobra.Command{
	Use:   "chronicles",
	Short: "Chronicles server.",
	Long:  "Chronicles backend server.",
}

func init() {
	cobra.OnInitialize(initConfig)
}

func Execute() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func initConfig() {
	gotenv.Load()
	common.Init()
}
