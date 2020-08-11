package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/Bnei-Baruch/chronicles/version"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number of feed-api",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("Feed and recommendations API for new archive site version %s\n", version.Version)
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
