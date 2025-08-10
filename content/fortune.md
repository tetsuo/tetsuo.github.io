---
title: Fortune as a Service
cover_title: Fortune as a Service
description: Simple Go service that delivers random fortune cookies over HTTP
tags: go
published: 2025-03-31T00:00:00
updated: 2025-08-09T13:37:00
navbar_disabled: true
---

> [**fortune**](https://github.com/tetsuo/fortune) is a simple HTTP API that delivers random fortune cookies, built as a working reference for setting up observability on GCP and to refresh my memory.

#### API

The fortune API has two endpoints. `GET /` returns a random fortune from the database. `POST /` accepts a plain text body with fortunes separated by `%`, as per the original format of the Unix `fortune` command.

#### Third-party code

I reused some internals from [**pkgsite**](https://go.googlesource.com/pkgsite/) (the Go package index) and adapted them to work with MySQL.

Specifically, I modified the `internal/database` package to support MySQL, along with the CLI tool in `devtools/cmd/db`. The other borrowed packages from pkgsite (`memory`, `middleware`, `wraperr`) remain largely unchanged, aside from minor cleanup.

## Code

The repo is here: [**github.com/tetsuo/fortune**](https://github.com/tetsuo/fortune)

Docs cover local setup, development, and deployment.
