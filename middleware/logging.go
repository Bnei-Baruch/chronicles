package middleware

import (
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
	"github.com/rs/zerolog/pkgerrors"
	"github.com/segmentio/ksuid"
)

var requestLog = zerolog.New(os.Stdout).With().Timestamp().Caller().Stack().Logger()

func init() {
	zerolog.SetGlobalLevel(zerolog.InfoLevel)

	zerolog.CallerFieldName = "line"
	zerolog.CallerMarshalFunc = func(file string, line int) string {
		rel := strings.Split(file, "chronicles/")
		return fmt.Sprintf("%s:%d", rel[1], line)
	}

	zerolog.TimeFieldFormat = time.RFC3339Nano
	zerolog.ErrorStackMarshaler = pkgerrors.MarshalStack
	output := zerolog.ConsoleWriter{Out: os.Stderr, TimeFormat: time.RFC3339Nano}
	log.Logger = log.Output(output).With().Caller().Stack().Logger()
}

// zerolog helpers adapted for gin (github.com/rs/zerolog/hlog)

func LoggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()

		// Create a copy of the logger (see hlog.NewHandler)
		l := requestLog.With().Logger()
		c.Set("LOGGER", l)

		// request id (see hlog.RequestIDHandler)
		requestID := ksuid.New()
		c.Set("REQUEST_ID", requestID)
		c.Header("X-Request-ID", requestID.String())
		l.UpdateContext(func(c zerolog.Context) zerolog.Context {
			return c.Str("request_id", requestID.String())
		})

		// log line (see hlog.AccessHandler)
		r := c.Request
		path := r.URL.RequestURI() // some evil middleware modify this values

		c.Next()

		l.Info().
			Str("method", r.Method).
			Str("path", path).
			Int("status", c.Writer.Status()).
			Int("size", c.Writer.Size()).
			Dur("duration", time.Since(start)).
			Str("ip", c.ClientIP()).
			Msg("")
	}
}
