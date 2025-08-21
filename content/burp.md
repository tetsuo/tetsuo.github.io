---
title: Old-school LLM chatroom
description: Chat with LLMs
cover_title: Old-school LLM chatroom
tags: go,js,llm
published: 2025-08-19T13:37:00
updated: 2025-08-19T13:37:00
---

> [**burp**](https://github.com/tetsuo/burp) is a chat server that connects clients to [OpenAI](https://openai.com/api/) and [Anthropic](https://www.anthropic.com/api) APIs. It provides HTTP endpoints and a browser-based chat frontend.

![burp](./images/burp-screenshot.png)

## Getting started

```sh
go install github.com/tetsuo/burp
```

This installs a `burp` executable to your `$GOPATH/bin`.

##### Start the server

```bash
burp
```

By default it binds to `localhost:9042`. You can change this with the `-addr` argument.

Set API keys via environment variables:

* `OPENAI_API_KEY` for OpenAI models
* `ANTHROPIC_API_KEY` for Claude models

##### Send messages

POST to `/ask?id=<channel>&model=<model>` with body text

```sh
curl --header "Content-Type: text/plain" \
  --request POST \
  --data "Tell a joke" \
  "http://localhost:9042/chat?id=emu&model=claude-3-haiku-20240307&temp=0.75"
```

##### Receive messages

- `/wait?id=<channel>` - long-poll up to 30s
- `/recent?id=<channel>` - fetch message history

##### Use the web UI

Open `/chat?id=<channel>&model=<model>` in a browser

---

# How it works

![burp](./images/burp_chat_flow.svg)

## Sending messages

### Message history & Context

burp keeps a rolling, in-memory buffer of recent messages per channel (default: last 50 entries). Old messages are dropped after ~1 hour or when the buffer grows beyond the minimum keep size.

You can access the channel history by calling `/recent?id=<channel>`.

This history is also passed back into the provider on each `/ask` request, together with the system prompt, so replies remain contextual.

### Message parameters

When you send a message, burp forwards generation parameters to the chosen provider.
Supported fields include:

* `temp` – temperature, always set (0.0–2.0 for OpenAI, 0.0–1.0 for Anthropic)
* `max_tokens` – capped per-model, defaults to the model’s maximum
* `top_p` – optional nucleus sampling
* `top_k` – optional, Anthropic only

These values are stored alongside the channel state and displayed in the chat UI, so you always know what settings were used.

## Receiving messages

Responses from OpenAI or Anthropic are streamed into an in-memory queue powered by [github.com/tetsuo/bbq](https://github.com/tetsuo/bbq).

Each request gets its own small queue: the provider SDK writes token deltas into it, and a batching loop reads from it to publish messages back into the channel.

### Long polling

When a client calls `/wait?id=<channel>&after=<time>`, the server will:

1. Hold the request open for up to 30 seconds.
2. If a new message arrives in that channel after the given `after` timestamp, it is immediately returned.
3. If no message arrives in that window, the server responds with a timeout marker message and the client retries with the latest cursor.

## What's next?

I built this mainly as a console for my LLM dev environment. The chat UI reuses bits from a WebRTC-powered [P2P chat app](https://github.com/tetsuo/r2) I hacked together years ago at a Mendix hackathon.

In the future I might add slash commands (IRC-style) or even [Matrix](https://matrix.org/) integration, but for now the chatroom alone is already a solid base, especially for wiring into tools like Google Sheets or Excel as an extension backend/UI.
