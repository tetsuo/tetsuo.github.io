---
title: Why Haskell Just Works?
description: Why Haskell Just Works?
cover_title: Understanding FP semantics
tags: haskell,fp,language
published: 2023-05-30T12:41:00
updated: 2024-11-13T00:00:00
---

> This article delves into Haskell's use of denotational semantics, a mathematical approach to defining program logic.

In Haskell, a **function** is a fixed mapping between inputs (arguments) and their corresponding values. Here is an example demonstrating the Fibonacci sequence.

```haskell
fib :: Integer -> Integer
fib 0 = 0
fib 1 = 1
fib n = fib (n-1) + fib (n-2)
```

This defines `fib` as a function that takes an integer `n` and returns the nth Fibonacci number. Each case acts as an equation, establishing the relationship between input and output. `fib n` runs recursively until the base case is reached and a sum is returned.

This view of a function is called [denotational](https://en.wikipedia.org/wiki/Denotational_semantics). We define its "meaning" by describing the relationships between inputs and outputs. This contrasts with [operational semantics](https://en.wikipedia.org/wiki/Operational_semantics), where functions are seen as sequences of _operations_ executed over time.

Each expression in Haskell has a meaning rooted in its mathematical equivalent. For example, `fib 1` and `5-4` both represent the integer 1 in the program. We say they _denote_ the same value.

>> The collection of such mathematical objects is called the **semantic domain**. Broadly speaking, denotational semantics is concerned with finding domains that represent what programs do; it aims to provide a mathematical foundation for understanding program behavior.

Notice that the meaning of `fib 2` is derived from the meanings of `fib 1` and `fib 0`. This **compositional** property is essential for building formal proofs of program correctness within denotational semantics.

To maintain compositionality, an expression must be [referentially transparent](https://en.wikipedia.org/wiki/Referential_transparency), meaning it can be replaced with its equivalent value without altering the program's outcome.

For example, a function that adds two numbers is referentially transparent. In contrast, a function that divides a number by another is not, as the divisor could be zero.

```haskell
> 10 `div` 2
5
> 10 `div` 0
*** Exception: divide by zero
```

Dividing by zero is undefined and results in an exception—a side effect.

### Dealing with Side Effects

To handle division by zero, Haskell offers the [`Maybe`](https://wiki.haskell.org/Maybe) data type. It can either hold a value (`Just a`) or indicate no value (`Nothing`). This ensures a _total_ division function that always returns a result, avoiding exceptions.

```haskell
data Maybe a = Just a | Nothing
```

> This type is also known as an [Algebraic Data Type](https://en.wikipedia.org/wiki/Algebraic_data_type) (ADT):
>
> * [Sum types](https://en.wikipedia.org/wiki/Tagged_union) represent _alternation_: `A | B` means `A` or `B` but not both.
> * [Product types](https://en.wikipedia.org/wiki/Product_type) represent _combination_: `A B` means `A` and `B` together.

The improved division function avoids side effects, returning a result based solely on its inputs:

```haskell
safeDiv :: Integral a => a -> a -> Maybe a
safeDiv a 0 = Nothing
safeDiv a b = Just (a `div` b)
```

By eliminating side effects and state mutations, functional languages like Haskell, PureScript, and Scala create environments where function behavior is fully predictable and [_pure_](https://en.wikipedia.org/wiki/Pure_function), ensuring referential transparency.

# Denotational semantics

Imagine a box `⟦⟧` that evaluates programs into mathematical objects. You place any **expression** inside, and the box gives you its corresponding **value**.

This can be represented as `⟦E⟧ : V`, where `E` represents an expression (syntactic object) and `V` is the abstract value (e.g., a number or function).

#### Example: Calculator syntax

Consider some arithmetic expressions in prefix notation:

```
⟦add 1 2⟧ = 1 + 2
⟦mul 2 5⟧ = 2 × 5
     ⟦42⟧ = 42
 ⟦neg 42⟧ = -42
```

We can define the **abstract syntax** of these expressions using [Backus-Naur form](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form):

```
n ∈ Int ::= ... | -1 | 0 | 1 | 2 | ...
e ∈ Exp ::= add e e
         |  mul e e
         |  neg e
         |  n
```

Here, all expressions evaluate to integers, making the **semantic domain** the set of all integers (ℤ). This definition aligns with how Haskell's [numerals-base](https://hackage.haskell.org/package/numerals-base-0.3/docs/Text-Numeral-Exp.html) package encodes numerals using the `data` keyword.


```haskell
type ℤ = Integer

-- | An expression that represents the structure of a numeral.
data Exp = Lit ℤ
         | Neg Exp
         | Add Exp Exp
         | Mul Exp Exp
```

While the specifics of evaluating these expressions are beyond our scope, the goal is to assign a value from the domain (ℤ) to every possible expression this syntax can generate. This function that assigns values is called a **valuation function**.

```
      ⟦Exp⟧ : Int
⟦add e1 e2⟧ = ⟦e1⟧ + ⟦e2⟧
⟦mul e1 e2⟧ = ⟦e1⟧ × ⟦e2⟧
    ⟦neg e⟧ = -⟦e⟧
        ⟦n⟧ = n
```

# Move language

>> Move language specification is adapted from [Eric Walkingshaw](https://web.engr.oregonstate.edu/~walkiner/)'s [CS581 lecture notes](https://web.engr.oregonstate.edu/~walkiner/teaching/cs581-fa20).

This example introduces a simple robot language called "Move", where commands like `go E 3` instruct a robot to move a specified number of steps in a direction.

```
go E 3; go N 4; go S 1;
```

* Each `go` command constructs a new **Step**, an n-unit movement horizontally or vertically.
* A **Move** consists of steps separated by semicolons.

```
n ∈ Nat  ::= 0 | 1 | 2 | ...
d ∈ Dir  ::= N | S | E | W
s ∈ Step ::= go d n
m ∈ Move ::= ε | s ; m
```

(Epsilon denotes an empty string.)

Let's explore two ways to interpret Move programs.

### Total Distance Calculation

Here, the semantic domain is the set of natural numbers (ℕ), representing the total distance traveled.

For Step expressions:

```
  S⟦Step⟧ : Nat
S⟦go d k⟧ = k
```

For Move expressions:

```
  M⟦Move⟧ : Nat
     M⟦ε⟧ = 0
   M⟦s;m⟧ = S⟦s⟧ + M⟦m⟧
```

### Target Position Calculation

Here, the semantic domain is the set of **functions** that map a starting position (x, y) to a final position after executing the Move program.

```
⟦Expr⟧ : Pos → Pos
```

We use [Lambda calculus](https://en.wikipedia.org/wiki/Lambda_calculus) (λ-calculus) to express these functions. Lambda abstractions take the form `λx.y`, where `x` is a variable and `y` is the function body.

For each Step:

```
  S⟦Step⟧ : Pos → Pos
S⟦go N k⟧ = λ(x,y).(x,y+k)
S⟦go S k⟧ = λ(x,y).(x,y−k)
S⟦go E k⟧ = λ(x,y).(x+k,y)
S⟦go W k⟧ = λ(x,y).(x−k,y)
```

A Move expression, as a sequence of steps, can be viewed as a pipeline where each Step processes the preceding output. An empty Move, represented by `ε`, returns the input position unchanged.

```
M⟦Move⟧ : Pos → Pos
   M⟦ε⟧ = λp.p
 M⟦s;m⟧ = M⟦m⟧ ◦ S⟦s⟧
```
