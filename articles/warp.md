---
title: Implementing monads in Go
cover_title: Implementing monads in Go
description: Experimenting with Go's generics and their practicality in modeling FP patterns
tags: go,tutorial
published: 2024-08-30T00:00:00
updated: 2025-06-05T13:37:00
---

> This post explores using Go's generics to structure and compose computations in a functional style.

Let's begin by comparing polymorphism in Haskell and Go.

# Polymorphism in Haskell

Here's a **Haskell** definition for a "plus" operator:

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

This kind of polymorphism is termed [**higher-kinded polymorphism**](https://en.wikipedia.org/wiki/Kind_(type_theory)). Similar to how [higher-order functions](https://en.wikipedia.org/wiki/Higher-order_function) abstract over values and functions, higher-kinded types (HKTs) abstract over types and type constructors.

# Polymorphism in Go

Similarly, here's a "greater than" definition in **Go**:

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

Unlike Haskell, Go does not natively support higher-kinded types (HKTs), which enable parameterization over type constructors. However, with the introduction of generics, we can achieve similar abstractions by leveraging [first-class function types](https://en.wikipedia.org/wiki/First-class_function) as an alternative.

# How generics help

Generics in Go allow us to write functions and data structures that can work with a range of types without having to write separate versions for each type.

For example, before generics, if we wanted a `List` (or slice) that could hold integers, we'd have `[]int`. For strings, we'd have `[]string`.  And if we wanted a function to operate on either, we'd have to write separate versions.

With generics, we can now write:

```go
type List[T any] []T

func mapList[T, U any](l List[T], f func(T) U) List[U] {
    // ... implementation ...
}
```

This `List` type and `mapList` function can now work with lists of any type. We can have` List[int]`, `List[string]`, `List[MyStruct]`, etc., and the same `mapList` function can operate on all of them.

# Where generics fall short for HTKs

The key difference lies in what generics can _abstract over_.

- **Go generics** – Can abstract over _concrete types_ (like `int`, `string`, `MyStruct`).  They can also abstract over _type parameters_ (like `T` and `U` in the example above).
- **HKTs** – Can abstract over _type constructors_ (like `List`, `Maybe`, `IO`). This allows us to create generic functions that work with a variety of _data structures_ themselves.

For example, a `Functor` is something we can map over (like our `mapList` example).  In Haskell, we can define a `Functor` type class:

```haskell
class Functor f where  -- 'f' is a type constructor (like List, Maybe)
  fmap :: (a -> b) -> f a -> f b
```

This says "anything that implements Functor must provide an fmap function."  `f` here is a _type constructor_.  We can then make `List`, `Maybe`, and many other things _instances_ of `Functor`.

In Go, even with generics, we can't express this level of abstraction. We can write a generic `mapList` for `List[T]`, but we'd have to write separate mapping functions for other data structures (e.g., if we had a `Maybe[T]` type). We can't write a single function that works for _any type that can be mapped over_ in the same way it's possible in Haskell with the `Functor` type class.

# Representing monads in Go

Monads in Haskell are typically defined using algebraic data types that encapsulate computations, like:

```haskell
data Result a = Ok a | Error String
```

which represent computations that may succeed or fail, or

```haskell
data Event a = Event (IO a)
```

which represent asynchronous computations or event streams.

Go doesn't have native support for type constructors or ADTs like Haskell does. Instead, the closest approximation is to use **function types** that encapsulate computations. This lets us represent monadic computations as first-class functions carrying the context and data flow.

For a `Result[A]` monad (similar to Haskell's `Result a`), we model it as:

```go
type Result[A any] func(context.Context) (A, error)
```

This is a function that, given a `context.Context`, returns either a value of type `A` or an error.

Similarly, for an event stream monad, we can represent it as a function that takes a context and a channel to push results to:

```go
type Event[A any] func(context.Context, chan<- A)
```

# Implementing monads in Go

To see how this works in practice, I implemented a small set of monads in Go. These are the types provided by [**warp**](https://github.com/tetsuo/warp).

>> #### ⚠️ Go 1.23 Update
>>
>> **warp** explores functional patterns in Go from the perspective of the language's capabilities **prior to Go 1.23**. With that release, native support for function-based iteration became available through [**range over function types**](https://go.dev/blog/range-functions). Additionally, a [proposal](https://github.com/golang/go/issues/61898) is underway for `golang.org/x/exp/xiter` to introduce similar combinators as part of the standard package. These advancements mean the straightforward first-class function approach demonstrated in this package has now been superseded by more idiomatic and performant Go solutions.

### `IO[A]`

An [`IO`](https://github.com/tetsuo/warp/blob/master/io/io.go) represents a computation that never fails and yields a value of type `A`.

It encapsulates a delayed computation, ensuring that side effects (such as I/O operations) are only executed when the function is invoked.

```go
type IO[A any] func() A
```

### `Result[A]`

A [`Result`](https://github.com/tetsuo/warp/blob/master/result/result.go) represents a computation that either yields a value of type `A` or an error—in other words, a computation that either succeeds or fails.

This enables safe chaining of operations while handling errors in a functional way.

```go
type Result[A any] func(context.Context) (A, error)
```

### `Event[A]`

An [`Event`](https://github.com/tetsuo/warp/blob/master/event/event.go) represents a collection of discrete occurrences of values over time.

It models asynchronous data streams and allows functional composition of event-driven logic.

```go
type Event[A any] func(context.Context, chan<- A)
```

### `Future[A]`

A [`Future`](https://github.com/tetsuo/warp/blob/master/future/future.go) represents a collection of discrete occurrences of events with associated values or errors.

```go
type Future[A any] Event[Result[A]]
```

> 📄 **See the full warp documentation at [pkg.go.dev](https://pkg.go.dev/github.com/tetsuo/warp).**

# Examples

## Result

Here's how we can safely chain mathematical operations—division, logarithm, square root, and doubling—using `Result` to handle potential errors gracefully:

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

>> 🐸 Also check out the [**middleware**](https://github.com/tetsuo/middleware) package, which introduces `Middleware` built on top of the `Result` type.

## Event

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
