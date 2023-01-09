---
title: binproto
tags: golang,networking
published: 2023-01-07T21:25:00
updated: 2023-01-07T21:25:00
---

> [binproto](https://github.com/onur1/binproto) implements generic support for binary-based request response protocols. You can use it to create your own binary network protocols for things like RPC or file transfer.

## Message format

Internally, it implements a streaming state machine borrowed from the [hypercore wire protocol](https://dat-ecosystem-archive.github.io/how-dat-works/#wire-protocol). Over the wire messages are length-prefixed and packed in the following format:

```
<varint - length of rest of message>
  <varint - header>
  <payload>
```

Each message starts with a header which is a varint encoded unsigned 64-bit integer and consists of a **channel ID** (first 60-bits) and a **channel type** (last 4-bits), the rest of the message is payload.

## Tutorial — Bleach logger

Here is an example of a client/server application to keep track of bleach levels in your pool or hot tub.

### Overview

In this tutorial, you are going to build three components, a server, a client and a command-line interface.

The client will send a message to the server every time a cup of bleach is added. The server's responsibility is to count the number of cups added within a time interval and run an alarm if the given cup limit is exceeded.

### Getting started

Type `go mod init example` to initialize your go project in an empty directory. We start with some boilerplate before adding binproto to the mix.

`server.go`

```go
package main

import "net"

type server struct {
	listener net.Listener
}

func (s *server) handle(conn net.Conn) {
	defer conn.Close()

	// to be continued...
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

On the client side, just add an empty `sendCupAdded(address)` function for now.

`client.go`

```go
package main

func sendCupAdded(address string) {
  // to be continued...
}
```

The CLI by default starts the program in server mode and waits for new connections on `localhost:4242`. You can listen on a different address via the `-address HOST:PORT` flag.

To start in client mode you run it with `-dial HOST:PORT`.

`main.go`

```go
package main

import (
	"flag"
	"log"
	"os"
)

var (
	help    = flag.Bool("help", false, "show this screen")
	address = ""
	remote  = ""
)

func main() {
	flag.StringVar(&remote, "dial", "", "connect to this address")
	flag.StringVar(&address, "address", "localhost:4242", "listen on this address")

	flag.Parse()

	if *help {
		flag.Usage()
		os.Exit(0)
	}

	if remote != "" {
		sendCupAdded(remote)
	} else {
		s := &server{}

		if err := s.serve("tcp", address); err != nil {
			log.Fatal(err)
		}
	}
}
```

### Let's communicate

Currently this client/server application does nothing, you can try sending some bytes back and forth through `net.Conn`, and if you are lucky, your messages will arrive in one piece at your destination, but that's usually not the case. This is where binproto comes into play. binproto simply packs your payload in a standard format which the other end could unpack without having to worry about low-level details of how the data is chunked up and put together.

Each connection creates a channel: a channel is identified by a channel ID and a channel type which is found in every message header. Since the ID is the larger number, we use it to identify a client connection, whereas the channel type is used to identify a command.

With that being said, authentication is out of scope, so the client ID will not be too relevant for this tutorial. We'll use the channel type however to specify a common language between the client and the server, namely the BLEACH protocol.

##### The BLEACH protocol

Most protocols start with a handshake to exchange some initial information to set things up on the connected side, such as version, identity and capabilities. For the sake of simplicity, we'll do none of these things.

In our protocol, the clients will simply start off by sending the duration of time frame in milliseconds which they want to track events for, that's the configuration message and its type number is `1`.

When the server receives this message, it will respond with an acknowledgement message which has the type number `2`. This finalizes the handshake and for the rest of the communication, the client keeps sending "cup added" events with type `3`.

|Type|Description|Payload|
|:--|:--|:--|
|1|Configuration|Duration in ms|
|2|Acknowledgement|_none_|
|3|Cup added event|_none_|

### Implementation

If you are familiar with the [textproto](https://pkg.go.dev/net/textproto) package, binproto is very similar.

`binproto.Conn` consists of a `binproto.Reader` and `binproto.Writer` to manage I/O. To start reading and sending messages, all you really need to do is to pipe the `conn` into a newly created `binproto.Conn` instance. You can then call `ReadMessage()` and `Send()` methods on this instance to read and send messages.

> [See the full binproto API documentation at pkg.go.dev](https://pkg.go.dev/github.com/onur1/binproto)

I used the [sliding](https://github.com/onur1/sliding) package (which I ported to Go from [mafintosh/sliding-window-counter](https://github.com/mafintosh/sliding-window-counter)) for counting cup additions. It is a small and efficient data structure for counting events in a moving time window.

In this demonstration, the duration of this time window will be set by the initial configuration message sent by the client. For handling configuration messages, the server needs to decode the duration value within the received payload. This value will be simply encoded as little-endian uint32. Consider using [Protocol Buffers](https://developers.google.com/protocol-buffers) for serializing complex data.

`server.go`

```go
func (s *server) handle(conn net.Conn) {
	defer conn.Close()

	c := binproto.NewConn(conn)

	var counter *sliding.Counter

	// start waiting for messages
	for {
		msg, err := c.ReadMessage()
		if err != nil {
			log.Fatal(err)
			return
		}

		switch msg.Channel {
		case 1:
			{
				// decode duration value
				duration := binary.LittleEndian.Uint32(msg.Data)

				// initialize a new counter
				counter = sliding.NewCounter(time.Duration(duration))

				fmt.Printf("-> Received configuration (id=%d, duration=%d)\n", msg.ID, duration)

				// send the ack message
				_, err = c.Send(binproto.NewMessage(42, 2, nil))
				if err != nil {
					log.Fatal(err)
				}

				fmt.Printf("<- Acknowledgement sent (id=%d)\n", msg.ID)
			}
		case 3:
			{
				// increment counter by 1
				counter.Inc(1)

				value := counter.Peek()

				fmt.Printf("-> Cup added event received (value=%d, id=%d)\n", value, msg.ID)

				// log an alarm text if needed
				if value > 5 {
					fmt.Printf("[ALARM] Oh noes! %d cups of bleach!\n", value)
				}
				if value > 6 {
					fmt.Println("I'm exiting, that's a lot of bleach!")

					s.close()
				}
			}
		}
	}
}
```

The client initiates the connection with `binproto.Dial()` and immediately sends the configuration message. The server then responds with an acknowledgement, and as a result the client proceeds to send 7 cup added events which will print out two alarm log lines on the server side.

`client.go`

```go
func sendCupAdded(address string) {
	c, err := binproto.Dial("tcp", address)
	if err != nil {
		log.Fatal(err)
	}

	// duration is 3 seconds
	duration := uint32((time.Second * 3).Milliseconds())

	// pack configuration payload
	payload := make([]byte, 4)
	binary.LittleEndian.PutUint32(payload, duration)

	// send configuration message
	_, err = c.Send(binproto.NewMessage(99, 1, payload))
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("<- Configuration sent (duration=%d)\n", duration)

	// start waiting for response
	for {
		msg, err := c.ReadMessage()
		if err != nil {
			log.Fatal(err)
			return
		}

		switch msg.Channel {
		case 2:
			{
				fmt.Printf("-> Received acknowledgement (id=%d)\n", msg.ID)

				// send 7 cup added events to trigger alarm twice
				for i := 0; i < 7; i++ {
					c.Send(binproto.NewMessage(99, 3, nil))
					fmt.Printf("<- Cup added event sent (i=%d, id=%d)\n", i, msg.ID)
				}
			}
		}
	}
}
```

Type `go run .` to start the server, and `go run . -dial localhost:4242` to connect to it.

Output on the client side:

```
<- Configuration sent (duration=3000)
-> Received acknowledgement (id=42)
<- Cup added event sent (i=0, id=42)
<- Cup added event sent (i=1, id=42)
<- Cup added event sent (i=2, id=42)
<- Cup added event sent (i=3, id=42)
<- Cup added event sent (i=4, id=42)
<- Cup added event sent (i=5, id=42)
<- Cup added event sent (i=6, id=42)
2023/01/03 08:29:55 EOF
exit status 1
```

Output on the server side:

```
-> Received configuration (id=99, duration=3000)
<- Acknowledgement sent (id=99)
-> Cup added event received (value=1, id=99)
-> Cup added event received (value=2, id=99)
-> Cup added event received (value=3, id=99)
-> Cup added event received (value=4, id=99)
-> Cup added event received (value=5, id=99)
-> Cup added event received (value=6, id=99)
[ALARM] Oh noes! 6 cups of bleach!
-> Cup added event received (value=7, id=99)
[ALARM] Oh noes! 7 cups of bleach!
I'm exiting, that's a lot of bleach!
```

## Final notes

### Buffer

binproto uses an internal buffer which allocates `4096` bytes by default, that means it will process what's inside the buffer as long as its size is equal or greater than this value, which is a sensible default for many applications. You can adjust this value for optimal performance if your protocol requires larger (or smaller) chunks.

### Encryption

Note that, binproto doesn't implement encryption, but there should be some module somewhere which implements the open source [NOISE protocol](http://www.noiseprotocol.org/) that you can use as a drop-in replacement for `net`. In the next part of this series, we'll see how we can secure our connection and discuss some authentication strategies as well.
