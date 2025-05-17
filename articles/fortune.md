---
title: Lightweight Go backend on GCP with built-in observability
cover_title: Lightweight Go backend on GCP with built-in observability
description: Intentionally boring, production-ready Go service that serves up random fortune cookies
tags: go,starter
published: 2025-03-31T00:00:00
updated: 2025-05-17T13:37:00
---

> [**fortune**](https://github.com/tetsuo/fortune) is an intentionally boring, production-ready Go service that serves random fortune cookies over HTTP.

It's built with minimal dependencies and reuses internals from [**pkgsite**](https://go.googlesource.com/pkgsite/) (the Go package index), adapted to work with MySQL. The service runs on a lean, GCP-native stack with full observability—logging, metrics, tracing, and profiling included. The goal is to show what a Go backend can look like when it's easy to understand, straightforward to deploy, and ready for real use.

#### API

The API has two endpoints. `GET /` returns a random fortune from the database. `POST /` accepts a plain text body with fortunes separated by `%`, as per the original format of the Unix `fortune` command.

#### Third-party code

I adapted the `internal/database` package to support MySQL. The other packages (`memory`, `middleware`, `wraperr`) are mostly unchanged apart from some cleanup. There's also a small CLI tool under `devtools/cmd/db` to help with database tasks, and a trimmed-down `all.bash` script for linting and tests.

## Code

The repo is here: [**github.com/tetsuo/fortune**](https://github.com/tetsuo/fortune)

Docs cover local setup, development, and deployment.
