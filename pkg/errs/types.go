package errs

type WithMessage struct {
	Msg string
	Err error
}

func (e *WithMessage) Error() string {
	return e.Msg
}

func (e *WithMessage) Cause() error {
	return e.Err
}

func (e *WithMessage) Unwrap() error {
	return e.Err
}
