---
title: Making sense of Haskell
description: The basics of denotational semantics and how it provides a mathematical framework for reasoning about program correctness in Haskell
cover_title: Making sense of Haskell
tags: haskell
published: 2023-05-30T12:41:00
updated: 2025-08-09T13:37:00
---

> Here's my take on explaining denotational semantics 😬

## What is a function?

Functions in Haskell are _pure_, meaning they're fixed mappings from inputs to outputs with no side effects like performing I/O or throwing exceptions.

Here is an example demonstrating the Fibonacci sequence:

```haskell
fib :: Integer -> Integer
fib 0 = 0
fib 1 = 1
fib n = fib (n-1) + fib (n-2)
```

This defines `fib` as a function that takes an integer `n` and returns the nth Fibonacci number. Each match corresponds to an equation defining the function's _meaning_ in terms of input-output relationships.

This view of a function is called **denotational**, in contrast to **operational semantics**, where functions are sequences of *operations* executed over time, like in imperative languages.

## Denotational semantics

Denotational semantics is powerful because it turns programs into _mathematical objects_ in some **semantic domain**, be it numbers, functions, sets, or even stranger things.

Formally, a language's meaning is defined by its **semantic function**, which maps program syntax to a chosen semantic domain. Think of it as a box `⟦⟧` where you place a syntactic expression inside and get back its value in that domain. For example:

```
⟦E⟧ : V
```

means the **expression** `E` is assigned a **value** in the semantic domain `V` (which could be numbers, functions, etc.).

### Example: Calculator

Consider arithmetic expressions written in prefix notation:

```
⟦add 1 2⟧ = 1 + 2
⟦mul 2 5⟧ = 2 × 5
     ⟦42⟧ = 42
 ⟦neg 42⟧ = -42
```

We can define the **abstract syntax** for these expressions using Backus-Naur Form (BNF):

```
n ∈ Int ::= ... | -1 | 0 | 1 | 2 | ...
e ∈ Exp ::= add e e
         |  mul e e
         |  neg e
         |  n
```

Here, every expression evaluates to an integer, so the semantic domain is ℤ (the set of all integers). In Haskell, we might denote this with:

```haskell
type ℤ = Integer

-- | An expression representing a numeral structure.
data Exp = Lit ℤ         -- Literal integer
         | Neg Exp       -- Negation of an expression
         | Add Exp Exp   -- Addition of two expressions
         | Mul Exp Exp   -- Multiplication of two expressions
```

The _valuation function_ then assigns a mathematical meaning to each expression:

```
      ⟦Exp⟧ : ℤ
⟦add e1 e2⟧ = ⟦e1⟧ + ⟦e2⟧
⟦mul e1 e2⟧ = ⟦e1⟧ × ⟦e2⟧
    ⟦neg e⟧ = -⟦e⟧
        ⟦n⟧ = n
```

or, in Haskell:

```haskell
eval :: Exp -> ℤ
eval (Lit n)     = n                   -- ⟦n⟧ = n
eval (Neg e)     = - (eval e)          -- ⟦neg e⟧ = -⟦e⟧
eval (Add e1 e2) = eval e1 + eval e2   -- ⟦add e1 e2⟧ = ⟦e1⟧ + ⟦e2⟧
eval (Mul e1 e2) = eval e1 * eval e2   -- ⟦mul e1 e2⟧ = ⟦e1⟧ × ⟦e2⟧
```

---

## Move language

Consider _Move_, a made-up DSL for controlling a robot.

The Move language specifies commands such as `go E 3`, which instruct a robot to move a given number of steps in a specified direction:

```
go E 3; go N 4; go S 1;
```

- Each `go` command constructs a `Step`, representing an n-unit movement in one of the cardinal directions.
- A `Move` is a sequence of steps separated by semicolons.

The abstract syntax for the Move language might be defined as:

```
n ∈ Nat  ::= 0 | 1 | 2 | ...
d ∈ Dir  ::= N | S | E | W
s ∈ Step ::= go d n
m ∈ Move ::= ε | s ; m
```

We can explore two interpretations (semantic domains) for Move programs:

### 1. Total distance calculation

In this interpretation, the semantic domain is ℕ (the natural numbers), representing the total distance traveled.

For `Step` expressions:

```
  S⟦Step⟧ : Nat
S⟦go d k⟧ = k
```

For `Move` expressions:

```
  M⟦Move⟧ : Nat
   M⟦ε⟧ = 0
 M⟦s;m⟧ = S⟦s⟧ + M⟦m⟧
```

### 2. Target position calculation

Here, the semantic domain is the set of functions that map a starting position `(x, y)` to a final position. We denote this using lambda calculus (λ-calculus):

```
⟦Expr⟧ : Pos → Pos
```

For each `Step`:

```
  S⟦Step⟧ : Pos → Pos
S⟦go N k⟧ = λ(x,y).(x,y+k)
S⟦go S k⟧ = λ(x,y).(x,y−k)
S⟦go E k⟧ = λ(x,y).(x+k,y)
S⟦go W k⟧ = λ(x,y).(x−k,y)
```

A `Move` expression composes these functions in sequence. For an empty `Move`, the function simply returns the starting position:

```
M⟦Move⟧ : Pos → Pos
   M⟦ε⟧ = λp.p
 M⟦s;m⟧ = M⟦m⟧ ∘ S⟦s⟧
```

## Implementing Move in Haskell

Here's the thing, the Move DSL can be implemented directly in Haskell by mirroring its BNF grammar with algebraic data types and defining its semantics as pure functions.

```haskell
-- Abstract syntax
data Dir = N | S | E | W

data Step = Go Dir Int

data Move
  = Empty
  | Seq Step Move

-- Semantics: total distance
stepDist :: Step -> Int
stepDist (Go _ k) = k

moveDist :: Move -> Int
moveDist Empty       = 0
moveDist (Seq s m)   = stepDist s + moveDist m

-- Semantics: final position
type Pos = (Int, Int)

stepPos :: Step -> Pos -> Pos
stepPos (Go N k) (x, y) = (x    , y + k)
stepPos (Go S k) (x, y) = (x    , y - k)
stepPos (Go E k) (x, y) = (x + k, y    )
stepPos (Go W k) (x, y) = (x - k, y    )

movePos :: Move -> Pos -> Pos
movePos Empty       p = p
movePos (Seq s m)   p = movePos m (stepPos s p)
```

To test it, save the code as `Move.hs` and run `ghci Move.hs`.

Then define a program:

```haskell
let prog = Seq (Go E 3) (Seq (Go N 4) (Seq (Go S 1) Empty))
```

Total distance traveled:

```haskell
moveDist prog
-- 8
```

Final position from the origin:

```haskell
movePos prog (0, 0)
-- (3, 3)
```

Final position from an arbitrary point:

```haskell
movePos prog (10, -2)
-- (13, 1)
```
