ARG work_dir=/go/src/github.com/Bnei-Baruch/chronicles
ARG build_number=dev
ARG db_url="postgres://user:password@host.docker.internal/chronicles?sslmode=disable"

FROM golang:1.14-alpine3.11 as build

LABEL maintainer="kolmanv@gmail.com"

ARG work_dir
ARG build_number
ARG db_url

ENV GOOS=linux \
	CGO_ENABLED=0 \
	DB_URL=${db_url}

RUN apk update && \
    apk add --no-cache \
    git

WORKDIR ${work_dir}
COPY . .

RUN go test -v $(go list ./... | grep -v /models) \
    && go build -ldflags "-w -X github.com/Bnei-Baruch/chronicles/version.PreRelease=${build_number}"


FROM alpine:3.11
ARG work_dir
WORKDIR /app
COPY ./misc/wait-for /wait-for
COPY --from=build ${work_dir}/chronicles .

EXPOSE 8080
CMD ["./chronicles", "server"]
