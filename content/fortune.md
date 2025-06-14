---
title: Fortune-as-a-Service
cover_title: Fortune-as-a-Service
description: Simple Go service that delivers random fortune cookies over HTTP
tags: go,starter
published: 2025-03-31T00:00:00
updated: 2025-06-09T13:37:00
navbar_disabled: true
---

> [**fortune**](https://github.com/tetsuo/fortune) is a simple HTTP API that delivers random fortune cookies.

It's built with minimal dependencies and reuses internals from [**pkgsite**](https://go.googlesource.com/pkgsite/) (the Go package index), adapted to work with MySQL.

Though simple, the service runs on a lean, GCP-native stack with full observability: logging, metrics, tracing, and profiling included. The goal is to show what a Go backend looks like when it's easy to understand, straightforward to deploy, and ready for real use.

#### API

The API has two endpoints. `GET /` returns a random fortune from the database. `POST /` accepts a plain text body with fortunes separated by `%`, as per the original format of the Unix `fortune` command.

#### Third-party code

I adapted the `internal/database` package to support MySQL, as well as the CLI tool under `devtools/cmd/db`. The other packages I borrowed from pkgsite (`memory`, `middleware`, `wraperr`) are mostly unchanged apart from some cleanup.

## Code

The repo is here: [**github.com/tetsuo/fortune**](https://github.com/tetsuo/fortune)

Docs cover local setup, development, and deployment.
