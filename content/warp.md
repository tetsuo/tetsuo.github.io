---
title: Faking monads in Go
cover_title: Faking monads in Go
description: Experimenting with Go's generics and their practicality in modeling FP patterns
tags: go,tutorial
published: 2024-08-30T00:00:00
updated: 2025-06-15T13:37:00
---

> This post explores how Go's new generics provide a safer environment for function composition.

Go doesn't have native support for type constructors or algebraic data types like Haskell does, so implementing functional structures isn't as straightforward.

However, the language has been evolving. With the recent addition of parametric polymorphism (generics), we finally have the tools and _added safety_ to experiment with advanced functional styles and higher-level abstractions.

Let's begin by comparing polymorphism in Haskell and Go.

---

## Polymorphism in Haskell

Here's a **Haskell** definition for a "plus" operator:

```haskell
(+) :: Number -> Number -> Number
```

We can generalize this by replacing `Number` with a _type variable_ `a` to accommodate any data type. This is called **parametric polymorphism**.

```haskell
(+) :: a -> a -> a
```

Or, restrict the type `a` to instances of the `Num` class. Here, `(Num a) =>` is a _type constraint_: this is **ad-hoc polymorphism** in Haskell.

```haskell
(+) :: (Num a) => a -> a -> a
```

In Haskell, [type classes](https://en.wikipedia.org/wiki/Type_class) like `Num` are defined by specifying a set of functions, along with their types, that must exist for every type that belongs to the class. **So types can be parameterized;** a type class `Eq` intended to contain types that admit equality would be declared in the following way:

```haskell
class Eq a where
  (==) :: a -> a -> Bool
  (/=) :: a -> a -> Bool
```

For instance, the `Maybe` data type is an _instance_ of both the `Eq` and `Ord` type classes, providing implementations for their respective functions (equality and ordering). This designates `Maybe` as a [type constructor](https://wiki.haskell.org/Constructor).

This kind of polymorphism is termed [**higher-kinded polymorphism**](https://en.wikipedia.org/wiki/Kind_(type_theory)). Similar to how [higher-order functions](https://en.wikipedia.org/wiki/Higher-order_function) abstract over values and functions, higher-kinded types (HKTs) abstract over types and type constructors.

---

## Polymorphism in Go

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

Finally, we have structural type constraints with `~` which allows more flexible constraints.

`~T` in a constraint means _any type whose underlying type is `T`_.

```go
type MyInt int

// Only matches int, not MyInt
func Foo[T int](v T) {}     // Foo(MyInt(42)) => error

// Matches int or MyInt
func Bar[T ~int](v T) {}    // Bar(MyInt(42)) => ok
```

> For more details, refer to the [Introduction to Generics](https://go.dev/blog/intro-generics) and the [Type Parameters Proposal](https://go.googlesource.com/proposal/+/HEAD/design/43651-type-parameters.md).

### How generics help

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

### Where generics fall short for HKTs

The key difference lies in what generics can _abstract over_.

- **Go generics** can abstract over _concrete types_ (like `int`, `string`, `MyStruct`).  They can also abstract over _type parameters_ (like `T` and `U` in the example above).
- **HKTs** can abstract over _type constructors_ (like `List`, `Maybe`, `IO`). This allows us to create generic functions that work with a variety of _data structures_ themselves.

For example, a `Functor` is something we can map over (like our `mapList` example).  In Haskell, we can define a `Functor` type class:

```haskell
class Functor f where  -- 'f' is a type constructor (like List, Maybe)
  fmap :: (a -> b) -> f a -> f b
```

This says "anything that implements Functor must provide an fmap function."  `f` here is a _type constructor_.  We can then make `List`, `Maybe`, and many other things _instances_ of `Functor`.

In Go, even with generics, we can't express this level of abstraction. We can write a generic `mapList` for `List[T]`, but we'd have to write separate mapping functions for other data structures (e.g., if we had a `Maybe[T]` type). We can't write a single function that works for _any type that can be mapped over_ in the same way it's possible in Haskell with the `Functor` type class.

---

## Monads in Haskell



Monads in Haskell are defined using algebraic data types that encapsulate computations, like:

```haskell
data Result a = Ok a | Error String
```

which represent computations that may succeed or fail, or

```haskell
import Control.Concurrent.Async

data Event a = Event (IO (Async a))
```

which represent asynchronous computations or event streams.

### Result

Type class instances require no explicit interface code; you just implement the functions.

```haskell
data Result a = Ok a | Error String

instance Functor Result where
    fmap f (Ok x)    = Ok (f x)
    fmap _ (Error s) = Error s

instance Applicative Result where
    pure = Ok
    Ok f <*> Ok x    = Ok (f x)
    Error s <*> _    = Error s
    _ <*> Error s    = Error s

instance Monad Result where
    return = pure
    Ok x >>= f    = f x
    Error s >>= _ = Error s
```

* `fmap` (**map**) is implemented via the `Functor` instance.
* `<*>` (**ap**) is implemented via the `Applicative` instance.
* `>>=` (**chain/bind**) is implemented via the `Monad` instance.

Let's also implement a `Show` instance and print some output:

```haskell
instance Show a => Show (Result a) where
    show (Ok x)    = "Ok " ++ show x
    show (Error s) = "Error " ++ show s

safeDiv :: Int -> Int -> Result Int
safeDiv _ 0 = Error "division by zero"
safeDiv x y = Ok (x `div` y)

example :: Result Int
example = do
    a <- safeDiv 10 2
    b <- safeDiv a 0 -- Boom: div by zero
    c <- safeDiv b 2
    return c

main :: IO ()
main = print example
```

Save as `Main.hs`, run with `ghc Main.hs && ./Main`.

Output: `Error "division by zero"`

---

## Monads in Go

Go does not natively support HKTs, which enable parameterization over type constructors, but we can still encode them in Go using functions.

```go
type IO[A any] func() A
```

The [**warp**](https://github.com/tetsuo/warp) package uses this approach to implement types like `Result`, `Event`, `Future`, and etc.

> 📄 **See the full documentation at [pkg.go.dev](https://pkg.go.dev/github.com/tetsuo/warp).**

### Result

For a `Result[A]` monad (similar to Haskell's `Result a`), we can simply model it as a function that returns either a value of type `A` or an error:

```go
type Result[A any] func() (A, error)

// Ok creates a result which never fails and returns a value of type A.
func Ok[A any](a A) Result[A] {
	return func() (A, error) {
		return a, nil
	}
}

// Error creates a result which always fails with an error.
func Error[A any](err error) Result[A] {
	return func() (a A, _ error) {
		return a, err
	}
}
```

Then implement its combinators, `Map`, `Ap`, and `Chain`:

```go
// Map creates a result by applying a function on a succeeding
func Map[A, B any](fa Result[A], f func(A) B) Result[B] {
	return func() (b B, err error) {
		var a A
		if a, err = fa(); err != nil {
			return
		}
		b = f(a)
		return
	}
}

// Ap creates a result by applying a function contained in the first result
// on the value contained in the second
func Ap[A, B any](fab Result[func(A) B], fa Result[A]) Result[B] {
	return func() (b B, err error) {
		var ab func(A) B

		if ab, err = fab(); err != nil {
			return
		}

		var a A

		if a, err = fa(); err != nil {
			return
		}

		b = ab(a)

		return
	}
}

// Chain creates a result which combines two results in sequence, using the
// return value of one result to determine the next one.
func Chain[A, B any](ma Result[A], f func(A) Result[B]) Result[B] {
	return func() (_ B, err error) {
		var a A
		if a, err = ma(); err != nil {
			return
		}
		return f(a)()
	}
}
```

Finally a small utility function to _fork_ a `Result`:

```go
func Fork[A any](ma Result[A], onError func(error), onSuccess func(A)) {
	if a, err := ma(); err != nil {
		onError(err)
	} else {
		onSuccess(a)
	}
}
```

Let's give it a go:

```go
package main

import (
	"errors"
	"fmt"
	"math"

	"golang.org/x/exp/constraints"
)

// Define errors for invalid operations:
var (
	errDivisionByZero       = errors.New("division by zero")
	errNegativeSquareRoot   = errors.New("negative square root")
	errNonPositiveLogarithm = errors.New("non-positive logarithm")
)

// Type constraint for numeric types that can be used in calculations:
type num interface {
	constraints.Float | constraints.Integer
}

// Safe division function that returns an error when y is zero:
func safeDiv[T num](x, y T) Result[T] {
	if y == 0.0 {
		return Error[T](errDivisionByZero)
	}
	return Ok(x / y)
}

// Safe square root function that returns an error for negative inputs:
func safeSqrt[T num](x T) Result[T] {
	if x < 0.0 {
		return Error[T](errNegativeSquareRoot)
	}
	return Ok(T(math.Sqrt(float64(x))))
}

// Safe logarithm function that returns an error for non-positive inputs:
func safeLog[T num](x T) Result[T] {
	if x <= 0.0 {
		return Error[T](errNonPositiveLogarithm)
	}
	return Ok(T(math.Log(float64(x))))
}

// Function to double the input value:
func double[T num](x T) T {
	return x * 2
}

func program[T num](x, y T) Result[T] {
	return Ap(
		Ok(double[T]),
		Chain(
			Chain(safeDiv(x, y), safeLog[T]),
			safeSqrt[T],
		),
	)
}

func main() {
	Fork(
		Map(
			program(20.0, 10.0),
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

>> 🦀 Also check out the [**middleware**](https://pkg.go.dev/github.com/tetsuo/middleware) package which allows type-safe HTTP middleware composition and introduces the `Middleware` monad built on top `warp.Result`.


### Event

Similarly, for an event stream monad, we can represent it as a function that accepts two parameters:

* A _context_ to signal upstream cancellation.
* A _send-only channel_ for pushing values of type `A` to downstream.

```go
type Event[A any] func(context.Context, chan<- A)
```

Here's an example that filters, maps, and merges event streams in functional style using channels under the hood:

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

---

## Conclusion

Implementing monads in Haskell is naturally concise because the language was built for such abstractions. Go, on the other hand, has its own idioms, syntax, and conventions for sequencing computations safely. Comparing the two isn't entirely fair, as each approaches the problem from a fundamentally different perspective.

Since Go 1.18 and the introduction of generics, the language has evolved significantly. Go 1.23 (released August 2024) added [range-over-func types](https://go.dev/blog/range-functions), and there's an active [proposal](https://github.com/golang/go/issues/61898) for `golang.org/x/exp/xiter` that would bring functional-style iteration to the standard library.

These changes show that Go is evolving to support more functional patterns while maintaining its core simplicity. And perhaps, what seems experimental today may become idiomatic Go tomorrow.
