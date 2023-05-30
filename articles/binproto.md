---
title: Length-prefix message framing in Go
cover_title: binproto
description: Support for binary-based request response protocols in Go
tags: go,net
published: 2023-01-07T21:25:00
updated: 2023-05-29T14:25:00
---

> [**binproto**](https://github.com/onur1/binproto) implements low-level support for binary-based two-way communication protocols. You can use it to create your own low-latency binary protocols for things like game networking or file transfer.

The Transmission Control Protocol (TCP) provides reliable delivery of a **stream** of bytes between two hosts. But it's the responsibility of the application level protocols to parse incoming data (either in text or bytes) into an application-specific _message_.

Go's standard library provides [net/textproto](https://pkg.go.dev/net/textproto) for implementing text protocols (in the style of HTTP, SMTP) in a convenient fashion. However, for binary protocols, there is really no consensus on what might be the most generic way for dividing a long stream of bytes into discrete messages.

## Message format

[binproto](https://github.com/onur1/binproto) internally implements a streaming state machine borrowed from the [hypercore wire protocol](https://dat-ecosystem-archive.github.io/how-dat-works/#wire-protocol). Over the wire each message is packed in the following format:

```
╔──────────────────────────────────────────────╗
│ length | channel ID × channel type │ payload │
╚──────────────────────────────────────────────╝
           └─ 60-bits   └─ 4-bits
```

This simple technique, which is performed basically by writing the size of each message to a stream before a message itself, is called **length-prefix framing**.

Each message starts with a header which is a varint encoded unsigned 64-bit integer and consists of a **channel ID** (first 60-bits) and a **channel type** (last 4-bits), the rest is the body of a message.

## Buffering

binproto uses an internal buffer which allocates 4096 bytes by default, meaning that it will process what's inside the buffer as long its size is equal or greater than this value; which is a sensible default for many applications. You can adjust this value for optimal performance if your protocol requires larger (or smaller) chunks.

> See the full [API documentation](https://pkg.go.dev/github.com/onur1/binproto) at pkg.go.dev

## Example: Echo

To start receiving and sending messages, all we really need to do is to pipe a `net.Conn` into a `binproto.Conn` instance. Once a connection is established, we can call `ReadMessage()` and `Send()` methods on a `Conn` instance to read and send messages.

```go
package main

import (
	"fmt"
	"log"
	"net"
	"time"

	"github.com/onur1/binproto"
)

func main() {
	s := &server{}

	time.AfterFunc(time.Millisecond*1, func() {
		c, err := binproto.Dial("tcp", ":4242")
		if err != nil {
			log.Fatal(err)
		}

		go func() {
			for {
				msg, err := c.ReadMessage()
				if err != nil {
					log.Fatal(err)
					return
				}

				fmt.Printf("%d %d %s\n", msg.ID, msg.Channel, msg.Data)

				s.close()
			}
		}()

		_, err = c.Send(binproto.NewMessage(42, 3, []byte("hi")))
		if err != nil {
			log.Fatal(err)
		}
	})

	if err := s.serve("tcp", ":4242"); err != nil {
		log.Fatal(err)
	}

}

type server struct {
	listener net.Listener
}

func (s *server) handle(conn net.Conn) {
	defer conn.Close()

	c := binproto.NewConn(conn)

	for {
		msg, err := c.ReadMessage()
		if err != nil {
			fmt.Printf("error: %v", err)
			return
		}

		fmt.Printf("%d %d %s\n", msg.ID, msg.Channel, msg.Data)

		_, err = c.Send(binproto.NewMessage(112, 5, []byte("hey")))
		if err != nil {
			log.Fatal(err)
		}
	}
}

func (s *server) serve(network, address string) error {
	l, err := net.Listen(network, address)
	if err != nil {
		return err
	}

	s.listener = l

	for {
		if s.listener == nil {
			break
		}

		c, err := l.Accept()
		if err != nil {
			continue
		}

		go s.handle(c)
	}

	return nil
}

func (s *server) close() error {
	err := s.listener.Close()
	s.listener = nil
	return err
}
```

## Encryption

Note that, binproto doesn't implement encryption, but there should be some module somewhere which implements the open source [NOISE protocol](http://www.noiseprotocol.org/) that you can use as a drop-in replacement for `net`.
