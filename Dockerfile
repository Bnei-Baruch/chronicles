ARG work_dir=/go/src/github.com/Bnei-Baruch/chronicles
ARG build_number=dev

FROM golang:1.17-alpine3.15 AS build

LABEL maintainer="kolmanv@gmail.com"

ARG work_dir
ARG build_number

RUN apk update && \
    apk add --no-cache \
    git 

WORKDIR ${work_dir}
COPY . .

ENV GOOS=linux \
	CGO_ENABLED=0 
RUN go build -ldflags "-w -X github.com/Bnei-Baruch/chronicles/version.PreRelease=${build_number}"

FROM alpine:latest

ARG work_dir
WORKDIR /app
COPY ./misc/wait-for /wait-for
COPY --from=build ${work_dir}/chronicles .

EXPOSE 8080
CMD ["./chronicles", "server"]
