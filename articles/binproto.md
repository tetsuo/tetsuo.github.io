---
title: Wire-safe framing protocol for multiplexed binary streams
cover_title: Wire-safe framing protocol for multiplexed binary streams
description: Message parsing for applications that require structured, channel-aware transmission over continuous byte input
tags: go,tool
published: 2023-01-07T21:25:00
updated: 2025-05-17T13:37:00
---

> [**binproto**](https://github.com/tetsuo/binproto) simplifies message parsing for applications that require structured, channel-aware transmission over continuous byte input.

The Transmission Control Protocol (TCP) ensures reliable delivery of byte streams between devices, but interpreting this data stream (whether text or binary) and converting it into meaningful messages is left to application-level protocols.

While Go's standard library offers a convenient framework for handling text-based protocols (like HTTP and SMTP) with [net/textproto](https://pkg.go.dev/net/textproto), there's no widely agreed-upon approach for dividing a long stream of bytes into discrete messages.

## Length-prefix framing

Internally, binproto leverages a streaming state machine inspired by the [hypercore wire protocol](https://dat-ecosystem-archive.github.io/how-dat-works/#wire-protocol). Each message is packed in the following format:

```
╔──────────────────────────────────────────────╗
│ length | channel ID × channel type │ payload │
╚──────────────────────────────────────────────╝
           └─ 60-bits   └─ 4-bits
```

_Length-prefix framing_ is a technique that prepends each message with its length, allowing the receiver to efficiently determine message boundaries within a continuous byte stream.

## Message structure

Each message includes a header, which is a variable-length encoded (varint) unsigned 64-bit integer, containing:

* **Channel ID (first 60 bits)**: Identifies the specific channel for the message.
* **Channel Type (last 4 bits)**: Specifies the type of data in the message.

Header is followed by the message payload.

## Configurable buffer size

binproto operates with a default internal buffer size of 4096 bytes, meaning data is processed as long as it meets or exceeds this buffer size—an effective default for many applications. You can adjust this value to better suit protocols dealing with larger or smaller data chunks, optimizing performance as needed.

> For more details on available functions and features, see the API documentation at [pkg.go.dev](https://pkg.go.dev/github.com/tetsuo/binproto).

## Example

To start receiving and sending messages, you simply pipe a `net.Conn` (network connection) into a `binproto.Conn` instance. Once connected, use the `ReadMessage()` and `Send()` methods on the `Conn` object to read incoming messages and send messages over the network.

```go
package main

import (
	"fmt"
	"log"
	"net"
	"time"

	"github.com/tetsuo/binproto"
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
