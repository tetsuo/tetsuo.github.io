---
title: Going Monadic with Go Generics
cover_title: Going Monadic with Go Generics
description: Experimenting with Monad implementations in Golang
tags: go,fp,language
published: 2024-08-30T00:00:00
updated: 2024-11-30T00:00:00
---

> Package [warp](https://github.com/tetsuo/warp) provides a collection of experimental Monad implementations in Go.

The introduction of [generics](https://go.dev/blog/intro-generics) in Go 1.18—a long-awaited feature enabling [parametric polymorphism](https://en.wikipedia.org/wiki/Parametric_polymorphism)—has greatly simplified implementing functional patterns, making the language more appealing and practical for functional programmers.

Before we dive in, it's worth noting that Go's core strengths are rooted in imperative programming rather than functional abstractions like Monads. For example, if you're only interested in batching or delaying incoming data, the [rate](https://pkg.go.dev/golang.org/x/time/rate) package is likely more suitable than implementing a Monad to manage channels. Nonetheless, exploring monadic patterns provides valuable insights. Let's begin by comparing polymorphism in Haskell and Go.

## Polymorphism in Haskell

Here's a Haskell definition for a "plus" operator:

```haskell
(+) :: Number -> Number -> Number
```

We can generalize this by replacing `Number` with a _type variable_ `a` to accommodate any data type. This is known as **parametric polymorphism**.

```haskell
(+) :: a -> a -> a
```

Or, restrict the type `a` to instances of the `Num` class. Here, `(Num a) =>` is a _type constraint_: this is **ad-hoc polymorphism** in Haskell.

```haskell
(+) :: (Num a) => a -> a -> a
```

In Haskell, [type classes](https://en.wikipedia.org/wiki/Type_class) like `Num` are defined by specifying a set of functions, along with their types, that must exist for every type that belongs to the class. So types can be parameterized; a type class `Eq` intended to contain types that admit equality would be declared in the following way:

```haskell
class Eq a where
  (==) :: a -> a -> Bool
  (/=) :: a -> a -> Bool
```

For instance, the `Maybe` data type is an _instance_ of both the `Eq` and `Ord` type classes, providing implementations for their respective functions (equality and ordering). This designates `Maybe` as a [type constructor](https://wiki.haskell.org/Constructor).

This kind of polymorphism is termed [higher-kinded polymorphism](https://en.wikipedia.org/wiki/Kind_(type_theory)). Similar to how [higher-order functions](https://en.wikipedia.org/wiki/Higher-order_function) abstract over values and functions, higher-kinded types (HKTs) abstract over types and type constructors.

## Polymorphism in Go

Similarly, here's a "greater than" definition in Go:

```go
func GreaterThan(x, y int64) bool
```

Go has supported [structural subtyping](https://en.wikipedia.org/wiki/Structural_type_system) through structures and interfaces. The newly introduced `any` keyword, an alias for the empty `interface{}`, indicates no type constraints when used as a _type parameter_:

```go
func GreaterThan[T any](x, y T) bool
```

To restrict the type, we can use [`constraints.Ordered`](https://pkg.go.dev/golang.org/x/exp/constraints#Ordered), which specifies types supporting comparison operators.

```go
import "golang.org/x/exp/constraints"

func GreaterThan[T constraints.Ordered](x, y T) bool
```

There is also a built-in [comparable](https://go.dev/ref/spec#Comparison_operators) constraint for types supporting equality operators, `==`, `!=`.

```go
func Equals[T comparable](x, y T) bool
```

> For more details, refer to the [Introduction to Generics](https://go.dev/blog/intro-generics) and the [Type Parameters Proposal](https://go.googlesource.com/proposal/+/HEAD/design/43651-type-parameters.md).

# What is a Monad?

A Monad defines a way to sequence computations. For example, in Haskell, the `Eq` type class allows equality operations for various types. While commonly used for numbers and strings, the concept of equality can be extended to other data types. For instance, we could define equality for a hypothetical `Fruit` type, allowing comparisons between apples and oranges. Essentially, any type can be compared for equality as long as an appropriate `Eq` implementation exists.

Similarly, the [Monad](https://wiki.haskell.org/All_About_Monads) class introduces the `>>=` (bind) operator:

```haskell
class Monad m where
  (>>=)  :: m a -> (  a -> m b) -> m b
  (>>)   :: m a ->  m b         -> m b
  return ::   a                 -> m a
```

The `bind` operator, `m a -> (a -> m b) -> m b`, allows us to chain computations within a monadic context, enabling declarative control flow. Using `>>=`, we can sequentially apply functions while managing values within specific contexts. With a suitable Monad instance, any computation can be sequenced using `>>=`.

Now that my Monad elevator pitch is over, it's time to take them for a spin with the `Result` and `Event` Monads.

# Result

A `Result` represents a computation that either yields a value of type `A` or an error—in other words, a computation that either succeeds or fails.

```go
type Result[A any] func(context.Context) (A, error)
```

> See the `Result` documentation at [pkg.go.dev](https://pkg.go.dev/github.com/tetsuo/warp/result).

In Haskell, this is similar to [`Either`](https://hackage.haskell.org/package/base/docs/Data-Either.html):

```haskell
data  Either a b  =  Left a | Right b
  deriving (Eq, Ord)
```

You can compare `Either` values if their underlying types support equality. A Go equivalent using `Result` and [comparable](https://go.dev/ref/spec#Comparison_operators) is shown below:

```go
type Eq[T any] func(a, b T) bool

func GetEq[A comparable](el Eq[error], ea Eq[A]) Eq[warp.Result[A]] {
	return func(fa, fb warp.Result[A]) bool {
		a1, err1 := fa()
		a2, err2 := fb()

		if err1 != nil {
			return err2 != nil && el(err1, err2)
		}
		return err2 == nil && ea(a1, a2)
	}
}
```

Here, we demonstrate a sequence of safe mathematical operations in Go—division, logarithm, square root, and doubling—using a `Result` monad to handle potential errors gracefully:

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"math"

	"github.com/tetsuo/warp"
	"github.com/tetsuo/warp/result"
	"golang.org/x/exp/constraints"
)

// Define custom error messages for specific invalid operations
var (
	errDivisionByZero       = errors.New("division by zero")
	errNegativeSquareRoot   = errors.New("negative square root")
	errNonPositiveLogarithm = errors.New("non-positive logarithm")
)

// Type constraint for numeric types that can be used in calculations
type num interface {
	constraints.Float | constraints.Integer
}

// Safe division function that returns a Result with an error if y is zero
func div[T num](x, y T) warp.Result[T] {
	if y == 0.0 {
		return result.Error[T](errDivisionByZero)
	}
	return result.Ok(x / y)
}

// Safe square root function that returns an error for negative inputs
func sqrt[T num](x T) warp.Result[T] {
	if x < 0.0 {
		return result.Error[T](errNegativeSquareRoot)
	}
	return result.Ok(T(math.Sqrt(float64(x))))
}

// Safe logarithm function that returns an error for non-positive inputs
func log[T num](x T) warp.Result[T] {
	if x <= 0.0 {
		return result.Error[T](errNonPositiveLogarithm)
	}
	return result.Ok(T(math.Log(float64(x))))
}

// Function to double the input value
func double[T num](x T) T {
	return x * 2
}

// Function that chains the operations: division, logarithm, square root, and doubling
func calculateResult[T num](x, y T) warp.Result[T] {
	return result.Ap(
		result.Ok(double[T]),
		result.Chain(
			result.Chain(div(x, y), log[T]),
			sqrt[T],
		),
	)
}

func main() {
	// Perform the calculation and handle the result or error using Fork
	result.Fork(
		context.TODO(),
		result.Map(
			calculateResult(20.0, 10.0),
			func(a float64) string {
				return fmt.Sprintf("%.6f", a)
			},
		),
		// Error handler: prints the error message if an error occurs
		func(err error) {
			fmt.Printf("Error is %v\n", err)
		},
		// Success handler: prints the result if calculation succeeds
		func(msg string) {
			fmt.Printf("Result is %s\n", msg)
		})
}
```

> For a more comprehensive example, see the [**middleware**](https://github.com/tetsuo/middleware) package, which introduces `Middleware` built on top of the `Result` type.

# Event

An `Event` represents a series of occurrences over time, each with associated data:

```go
type Event[A any] func(context.Context, chan<- A)
```

> See the `Event` documentation at [pkg.go.dev](https://pkg.go.dev/github.com/tetsuo/warp/event).

Inspired by Phil Freeman's [purescript-event](https://github.com/paf31/purescript-event), the Go `Event` implementation uses channels for a fully asynchronous approach.

An `Event` constructor accepts two parameters:

* A _context_ to signal upstream cancellation.
* A _send-only channel_ for pushing values of type `A` to downstream.

To create a basic event that emits the current time every second:

```go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/tetsuo/warp/event"
)

func main() {
	run := event.Interval(time.Second * 1) // Emit every second

	values := make(chan time.Time)

	go run(context.TODO(), values)

	for v := range values {
		fmt.Println(v)
	}
}

// Output:
// 2024-09-02 11:47:48.941034 +0200 CEST m=+1.001269253
// 2024-09-02 11:47:49.940117 +0200 CEST m=+2.000392628
// 2024-09-02 11:47:50.940966 +0200 CEST m=+3.001281450
```

Using combinators like `Map`, `Filter`, and `Alt`, we can manipulate event streams. Here's an example that filters, maps, and merges events:

```go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/tetsuo/warp/event"
)

func main() {
	// Create a channel to receive integer events
	nums := make(chan int)

	// First event stream: emits a count every second, filtering out the value 3
	first := event.Filter(
		event.Count(
			event.Interval(time.Second * 1),
		),
		func(x int) bool {
			return x != 3
		},
	)

	// Second event stream: emits the value 21 after a 2-second delay and doubles it
	second := event.Map(
		event.After(time.Second*2, 21),
		func(x int) int {
			return x * 2
		},
	)

	// Merge the two event streams using Alt, which combines the events
	run := event.Alt(first, second)

	// Start the merged event stream in a goroutine, sending results to nums channel
	go run(context.TODO(), nums)

	// Print each value as it is received from the nums channel
	for num := range nums {
		fmt.Println(num)
	}
}

// Output:
// 1
// 2
// 42
// 4
// 5
```
