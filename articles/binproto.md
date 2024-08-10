---
title: Build custom binary protocols in Go with multiplexing support
cover_title: binproto
description: Build custom binary protocols in Go with multiplexing support
tags: go,net
published: 2023-01-07T21:25:00
updated: 2024-08-10T00:00:00
---

> [**binproto**](https://github.com/onur1/binproto) provides generic support for binary communication protocols. Ideal for applications like game networking or file transfer, it enables low-latency data exchange.

The Transmission Control Protocol (TCP) ensures reliable delivery of byte streams between devices. However, application-level protocols are responsible for parsing incoming data (text or binary) into meaningful messages specific to the application.

While Go's standard library offers a convenient framework for handling text-based protocols (like HTTP and SMTP) with [net/textproto](https://pkg.go.dev/net/textproto), there's no widely agreed-upon approach for dividing a long stream of bytes into discrete messages.

## Length-Prefix Framing

Internally, binproto leverages a streaming state machine inspired by the [hypercore wire protocol](https://dat-ecosystem-archive.github.io/how-dat-works/#wire-protocol). Over the wire each message is packed in the following format:

```
╔──────────────────────────────────────────────╗
│ length | channel ID × channel type │ payload │
╚──────────────────────────────────────────────╝
           └─ 60-bits   └─ 4-bits
```

This simple technique prefaces each message with its size, allowing binproto to efficiently determine individual message boundaries within the byte stream.

## Message Structure

Each message starts with a header, which is a variable-length encoded (varint) unsigned 64-bit integer, containing:

* **Channel ID (first 60 bits)**: Identifies the specific channel for the message.
* **Channel Type (last 4 bits)**: Denotes the type of data contained in the message.

Header is followed by the message payload.

## Configurable Buffer Size

binproto uses an internal buffer with a default size of 4096 bytes. This means it processes data within the buffer as long as the data size meets or exceeds this value, a reasonable default for many applications. However, you can adjust this value for optimal performance if your protocol deals with larger or smaller data chunks.

> For detailed information on the available functions and functionalities, refer to the [API documentation](https://pkg.go.dev/github.com/onur1/binproto) available at pkg.go.dev.

## Example Usage

To start receiving and sending messages, simply pipe a `net.Conn` (network connection) into a `binproto.Conn` instance. Once the connection is established, use the `ReadMessage()` and `Send()` methods on the `Conn` object to read incoming messages and send messages over the network, respectively.

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

**Note**: binproto doesn't provide encryption, but there are Go modules out there which can be used as a drop-in replacement for `net` to add encryption capabilities. See: [NOISE protocol](http://www.noiseprotocol.org/).
