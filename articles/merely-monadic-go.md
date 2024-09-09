---
title: Merely monadic in Go
cover_title: Merely monadic in Go
description: Experimenting with Monad implementations in Golang
tags: go,fp,language
published: 2024-08-30T00:00:00
updated: 2024-08-30T00:00:00
---

> Package [warp](https://github.com/onur1/warp) provides a collection of experimental Monad implementations in Go.

Since Go version 1.18, the language has incorporated [generics](https://go.dev/blog/intro-generics), a highly anticipated feature enabling [parametric polymorphism](https://en.wikipedia.org/wiki/Parametric_polymorphism).

Last summer, inspired by **Philip Wadler**'s [Featherweight Go](https://www.youtube.com/watch?v=Dq0WFigax_c) presentation, I experimented with several Monad implementations. It seems the addition of generics has made it possible to implement them with relative ease.

Before we proceed, it's important to acknowledge that Go's core strengths lie in imperative programming rather than functional abstractions like monads. For most use cases, the [rate](https://pkg.go.dev/golang.org/x/time/rate) package is likely a more suitable option than implementing a monad to abstract over channels. Nonetheless, exploring the monadic approach provides valuable insights. Let's begin by briefly comparing polymorphism in Haskell and Go.

## Polymorphism in Haskell

Here's a Haskell definition for a "plus" operator:

```haskell
(+) :: Number -> Number -> Number
```

We can generalize this by replacing `Number` with a _type variable_ `a` to accommodate any data type. This is known as **parametric polymorphism**.

```haskell
(+) :: a -> a -> a
```

Or, restrict the type `a` to instances of the `Num` class. In the following example, `(Num a) =>` is a _type constraint_: this is **ad-hoc polymorphism** in Haskell.

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

Go has long supported a form of [structural subtyping](https://en.wikipedia.org/wiki/Structural_type_system) through structures and interfaces. The newly introduced `any` keyword is an alias for the empty `interface{}`. When used as a _type parameter_, `any` signifies no type constraints, allowing `T` to represent any type in the following definition.

```go
func GreaterThan[T any](x, y T) bool
```

We can restrict it to [`constraints.Ordered`](https://pkg.go.dev/golang.org/x/exp/constraints#Ordered), which specifies types supporting comparison operators.

```go
import "golang.org/x/exp/constraints"

func GreaterThan[T constraints.Ordered](x, y T) bool
```

There is also a built-in [comparable](https://go.dev/ref/spec#Comparison_operators) constraint for types supporting equality operators, `==`, `!=`.

```go
func Equals[T comparable](x, y T) bool
```

> Refer to the [Introduction to Generics](https://go.dev/blog/intro-generics) and the [Type Parameters Proposal](https://go.googlesource.com/proposal/+/HEAD/design/43651-type-parameters.md) for more information.

# What is a Monad?

Let's consider the `==` operator defined in the `Eq` class first. While commonly used for numbers and strings, the concept of equality can be extended to other data types as well. For example, we could define equality for a hypothetical "Fruit" type, allowing comparisons between apples and oranges. Essentially, any type can be compared for equality as long as an appropriate `Eq` implementation exists.

Similarly, the [Monad](https://wiki.haskell.org/All_About_Monads) class introduces the `>>=` (bind) operator:

```haskell
class Monad m where
  (>>=)  :: m a -> (  a -> m b) -> m b
  (>>)   :: m a ->  m b         -> m b
  return ::   a                 -> m a
```

The `bind` operator, with the `m a -> (a -> m b) -> m b` type signature, defines a function for **sequencing computations** within a _monadic_ context. It takes a _monadic value_ of type `a` and a function that maps a value of type `a` to a monadic value of type `b`. It then applies the function to the value inside the input monad and returns a new monadic value of type `b`, effectively chaining two computations together.

Long story short, any computation can be sequenced using `>>=` given a suitable Monad instance. Computations on [lists](https://www.schoolofhaskell.com/school/starting-with-haskell/basics-of-haskell/13-the-list-monad), [branching logic](https://hackage.haskell.org/package/base/docs/Data-Either.html), and [asynchronous operations](https://rxjs.dev/guide/overview) can all be composed using the `bind` operator within the context of a Monad. [Declarative style](https://en.wikipedia.org/wiki/Declarative_programming), in particular, benefit significantly from this pattern as control flow is implicitly managed.

It's worth noting that [most Monads are also Applicatives and Functors](https://www.adit.io/posts/2013-04-17-functors,_applicatives,_and_monads_in_pictures.html), forming a hierarchical relationship.

Now, my Monad elevator pitch is over. Time to take it for a spin with the `Result` and `Event` Monads.

# Result

A `Result` represents a computation that either yields a value of type `A` or an error:

```go
type Result[A any] func(context.Context) (A, error)
```

> See the [API documentation](https://pkg.go.dev/github.com/onur1/warp/result) at pkg.go.dev

Compare it with Haskell's [`Either`](https://hackage.haskell.org/package/base/docs/Data-Either.html):

```haskell
data  Either a b  =  Left a | Right b
  deriving (Eq, Ord)
```

Type classes like `Eq` and `Ord` offer additional capabilities. For instance, you can compare `Either` values if their underlying types support equality. Here's how [fp-ts](https://gcanti.github.io/fp-ts/) handles `Eq` for `Either`.

```typescript
const getEq = <E, A>(EL: Eq<E>, EA: Eq<A>): Eq<Either<E, A>> => ({
  equals: (x, y) =>
    x === y || (
      isLeft(x)
      ? isLeft(y) && EL.equals(x.left, y.left)
      : isRight(y) && EA.equals(x.right, y.right)
    )
})
```

A Go equivalent using `Result` is shown below.

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

One might expect to use a generic `Eq` function to compare `Result` values. However, since `Result` internally represents computations as functions, direct comparison is not possible as functions are not [comparable](https://go.dev/ref/spec#Comparison_operators).

Fortunately, the monad interface provides a suitable abstraction. Additionally, Go's [error subtyping](https://go.dev/blog/go1.13-errors) feature (introduced in version 1.13) enables effective error handling through pattern matching.

```go
package main

import (
	"context"
	"errors"
	"fmt"
	"math"

	"github.com/onur1/warp"
	"github.com/onur1/warp/result"
	"golang.org/x/exp/constraints"
)

var (
	errDivisionByZero       = errors.New("division by zero")
	errNegativeSquareRoot   = errors.New("negative square root")
	errNonPositiveLogarithm = errors.New("non-positive logarithm")
)

type num interface {
	constraints.Float | constraints.Integer
}

func div[T num](x, y T) warp.Result[T] {
	if y == 0.0 {
		return result.Error[T](errDivisionByZero)
	}
	return result.Ok(x / y)
}

func sqrt[T num](x T) warp.Result[T] {
	if x < 0.0 {
		return result.Error[T](errNegativeSquareRoot)
	}
	return result.Ok(T(math.Sqrt(float64(x))))
}

func log[T num](x T) warp.Result[T] {
	if x <= 0.0 {
		return result.Error[T](errNonPositiveLogarithm)
	}
	return result.Ok(T(math.Log(float64(x))))
}

func double[T num](x T) T {
	return x * 2
}

func op[T num](x, y T) warp.Result[T] {
	return result.Ap(
		result.Ok(double[T]),
		result.Chain(
			result.Chain(div(x, y), log[T]),
			sqrt[T],
		),
	)
}

func main() {
	result.Fork(
		context.TODO(),
		result.Map(
			op(20.0, 10.0),
			func(a float64) string {
				return fmt.Sprintf("%.6f", a)
			},
		),
		func(err error) {
			fmt.Printf("Error is %v\n", err)
		}, func(msg string) {
			fmt.Printf("Result is %s\n", msg)
		})
}
```

>> A more comprehensive usage example is provided by the [**middleware**](https://github.com/onur1/middleware) package, which introduces the `Middleware` monad built upon the `Result` type.

# Event

An `Event` represents a timeline of distinct happenings, each with corresponding data.

```go
type Event[A any] func(context.Context, chan<- A)
```

> See the [API documentation](https://pkg.go.dev/github.com/onur1/warp/event) at pkg.go.dev

The `Event` implementation is based on Phil Freeman's [purescript-event](https://github.com/paf31/purescript-event), subsequently ported to TypeScript by Giulio Canti as part of [behaviors-ts](https://github.com/gcanti/behaviors-ts), but it differs by utilizing **channel subscriptions** in Go for a fully asynchronous approach.

#### PureScript

```haskell
newtype Event a = Event ((a -> Effect Unit) -> Effect (Effect Unit))
```

#### TypeScript

```typescript
type Subscriber<A> = (a: A) => void

interface Event<A> {
  (sub: Subscriber<A>): void
}
```

>> **Extra knowledge:** While the theoretical foundations of the `Event` monad can be attributed to Conal Elliott and Paul Hudak's ['Functional Reactive Animation'](http://conal.net/papers/icfp97/), the `Observable` monad from [ReactiveX](https://reactivex.io/intro.html) is undoubtedly its most widely recognized implementation.

An `Event` constructor accepts two parameters:

* A _context_ to signal upstream cancellation.
* A _send-only channel_ for pushing values of type `A` to downstream.

A single event constructed with `event.Internal` is demonstrated below. This event emits the current time at a frequency of one second.

```go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/onur1/warp/event"
)

func main() {
	run := event.Interval(time.Second * 1) // emit every second

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

Let's spice things up a bit by using combinators such as `Map`, `Filter`, and `Alt`.

```go
package main

import (
	"context"
	"fmt"
	"time"

	"github.com/onur1/warp/event"
)

func main() {
	nums := make(chan int)

	first := event.Filter( // skip 3
		event.Count( // count number events
			event.Interval(time.Second*1), // emit every second
		),
		func(x int) bool {
			return x != 3
		},
	)

	second := event.Map( // double it
		event.After(time.Second*2, 21), // emit 21 after 2 seconds
		func(x int) int {
			return x * 2
		},
	)

	// merge events
	run := event.Alt(first, second)

	go run(context.TODO(), nums)

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

`event.Alt` is used for alternating between two events.

Note that in both purescript-event and event-ts, the first subscription must complete before the second one can start. This means that the second event won't be subscribed to until the first one emits a value.

```haskell
instance altEvent :: Alt Event where
  alt (Event f) (Event g) = Event \k -> do
    c1 <- f k
    c2 <- g k
    pure (c1 *> c2)
```

in TypeScript:

```typescript
const alt = <A>(fx: Event<A>, fy: Event<A>): Event<A> =>
  sub => {
    fx(sub)
    fy()(sub)
  }
```

The channel-based version in Go doesn't have this limitation. The implementation is bulkier, but much of it is boilerplate code to ensure that no values are emitted when the context is canceled.

```go
// Alt creates an event which emits values simultaneously from two source events.
func Alt[A any](x warp.Event[A], y warp.Event[A]) warp.Event[A] {
	return func(ctx context.Context, sub chan<- A) {
		defer close(sub)

		var (
			xs = make(chan A)
			ys = make(chan A)
			a  A
			ok bool
		)

		var done <-chan struct{}

		if ctx != nil {
			done = ctx.Done()
		}

		go x(ctx, xs)
		go y(ctx, ys)

		for {
			select {
			case a, ok = <-xs:
				if !ok {
					xs = nil
					if ys == nil {
						return
					}
					break
				}
				select {
				case <-done:
					return
				default:
					select {
					case <-done:
						return
					case sub <- a:
					}
				}
			case a, ok = <-ys:
				if !ok {
					ys = nil
					if xs == nil {
						return
					}
					break
				}
				select {
				case <-done:
					return
				default:
					select {
					case <-done:
						return
					case sub <- a:
					}
				}
			}
		}
	}
}
```

The same pattern is used throughout the other combinator implementations. One potential issue with this approach is that it can create an excessive number of nested goroutines, especially for tasks that do not require asynchronous execution. To address this, the channel scheduler should be decoupled. However, for now, I'm not sure if the benefits justify the additional hassle for implementing a scheduler.
