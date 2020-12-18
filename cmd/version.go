package cmd

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/Bnei-Baruch/chronicles/version"
)

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number of chronicles",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("Cross organization personalization events collector version %s\n", version.Version)
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}
