package middleware

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/go-playground/validator"
	pkgerr "github.com/pkg/errors"
	"github.com/rs/zerolog"

	"github.com/Bnei-Baruch/chronicles/pkg/sqlutil"
)

func ValidationErrorMessage(e validator.FieldError) string {
	switch e.Tag() {
	case "required":
		return "required"
	case "max":
		return fmt.Sprintf("cannot be longer than %s", e.Param())
	case "min":
		return fmt.Sprintf("must be longer than %s", e.Param())
	case "len":
		return fmt.Sprintf("must be %s characters long", e.Param())
	case "email":
		return "invalid email format"
	case "hexadecimal":
		return "invalid hexadecimal value"
	default:
		return "invalid value"
	}
}

func BindErrorMessage(err error) string {
	switch err.(type) {
	case *json.SyntaxError:
		e := err.(*json.SyntaxError)
		return fmt.Sprintf("json: %s [offset: %d]", e.Error(), e.Offset)
	case *json.UnmarshalTypeError:
		e := err.(*json.UnmarshalTypeError)
		return fmt.Sprintf("json: expecting %s got %s [offset: %d]", e.Type.String(), e.Value, e.Offset)
	default:
		return err.Error()
	}
}

// Handle all errors
func ErrorHandlingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()

		if len(c.Errors) == 0 {
			return
		}

		log := c.MustGet("LOGGER").(zerolog.Logger)
		for _, e := range c.Errors {
			switch e.Type {
			case gin.ErrorTypePublic:
				if e.Err != nil {
					log.Warn().Msgf("Public error: %s", e.Error())
					c.JSON(c.Writer.Status(), gin.H{"status": "error", "error": e.Error()})
				}

			case gin.ErrorTypeBind:
				// Keep the preset response status
				status := http.StatusBadRequest
				if c.Writer.Status() != http.StatusOK {
					status = c.Writer.Status()
				}

				switch e.Err.(type) {
				case validator.ValidationErrors:
					errs := e.Err.(validator.ValidationErrors)
					errMap := make(map[string]string)
					for field, err := range errs {
						msg := ValidationErrorMessage(err)
						log.Warn().
							Int("field", field).
							Str("error", msg).
							Msg("Validation error")
						errMap[err.Field()] = msg
					}
					c.JSON(status, gin.H{"status": "error", "errors": errMap})
				default:
					log.Warn().
						Str("error", e.Err.Error()).
						Msg("Bind error")
					c.JSON(status, gin.H{"status": "error", "error": BindErrorMessage(e.Err)})
				}

			default:
				// Log all other errors
				err := e.Err
				messages := []string(nil)
				for err != nil {
					messages = append(messages, fmt.Sprintf("%+v", err))
					var e *sqlutil.TxError
					if pkgerr.As(err, &e) {
						err = e.Unwrap()
					} else {
						break
					}
				}
				log.Error().Err(err).Msg(strings.Join(messages, "\n"))
				// TODO: Uncomment after Rollbar integration.
				// LogRequestError(c.Request, e.Err)
			}
		}

		// If there was no public or bind error, display default 500 message
		if !c.Writer.Written() {
			c.JSON(http.StatusInternalServerError, gin.H{"status": "error", "error": "Internal Server Error"})
		}

	}
}
