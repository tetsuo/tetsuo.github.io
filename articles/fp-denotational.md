---
title: Denotational semantics
description: Learn how fp provides mathematical meaning to programs
cover_title: Denotational
tags: haskell,fp,language
published: 2023-05-30T12:41:00
updated: 2023-05-30T12:41:00
---

> This post is the first of a series, which I think may be useful for those learning functional programming.

In purely functional programming, a **function** is regarded as a fixed set of associations between arguments and the corresponding values.

Here is the [Fibonacci sequence](https://rosettacode.org/wiki/Fibonacci_sequence) defined by the linear recurrence equation in [Haskell](https://www.haskell.org/):

```haskell
fib :: Integer -> Integer
fib 0 = 0
fib 1 = 1
fib n = fib (n-1) + fib (n-2)
```

What we have in here consists of _equations_, each of which establishes an equality between the left and right hand sides of the equal sign. Each case expects some input integer to conform to a given pattern, `0`, `1` or `n` and outputs a Fibonacci number. `fib n` runs recursively until the base case is reached and a sum is returned.

This view of a function is said to be [denotational](https://en.wikipedia.org/wiki/Denotational_semantics) since you are constructing _denotations_ (or meanings) to define it; in contrast to [operational](https://en.wikipedia.org/wiki/Operational_semantics), where a function is seen as a sequence of _operations_ in time.

> In FP, we understand the "true meaning" of a program, because we know the mathematical object it denotes. The mathematical objects for the Haskell programs `fib 1`, `1`, `5-4`, and `fib (2-1) + fib (2-2)` can be represented by the integer 1. We say that all those programs _denote_ the integer 1.

Similarly, `fib 0`, `fib 1` and `fib 42`, what they all have in common is that they all denote Fibonacci numbers: the meaning of the `fib n` expression is the n-th Fibonacci number, an element of the Fibonacci sequence.

The collection of such mathematical objects is called the **semantic domain**. Broadly speaking, denotational semantics is concerned with finding domains that represent what programs do.

# Referential transparency

Denotational semantics is **compositional**. `fib 2` depends on the meaning of its constituents, `fib 1` and `fib 0`. To achieve compositionality, an expression must be [referentially transparent](https://en.wikipedia.org/wiki/Referential_transparency) meaning that it can be replaced with its corresponding value without changing the program's behavior.

**Example**: A function that adds two numbers is referentially transparent, but a function that divides a number by another is not, simply because the divisor can be zero and division by zero is undefined. In a lot of languages (including Haskell) division by zero throws an exception (a side-effect) since _division_ is a [partial function](https://en.wikipedia.org/wiki/Partial_function).

```haskell
> 10 `div` 2
5
> 10 `div` 0
*** Exception: divide by zero
```

To turn a partial function into a total function (a function defined for all possible input values) in Haskell, we can wrap the result with a [`Maybe`](https://wiki.haskell.org/Maybe) data type.

```haskell
safeDiv :: Integral a => a -> a -> Maybe a
safeDiv a 0 = Nothing
safeDiv a b = Just (a `div` b)
```

Now this gives us a total meaning. `safeDiv` returns _Just_ a number or _Nothing_ (given 0), but it never throws an exception.

# Denotational definition

So imagine that there is a magical box (like **⟦⟧**) which evaluates programs into mathematical objects. You put any programmatic **expression** inside this box, and on the other end of the equation you get some **value** for it.

```
⟦E⟧ : V
```

"An expression is a _syntactic_ object, formed according to the syntax rules of the language. A value, by contrast, is an _abstract_ mathematical object, such as 'the number 5', or 'the function which squares its argument'." [^spj-book]

Take simple arithmetic expressions written in prefix notation as example:

```
⟦add 1 2⟧ = 1 + 2
⟦mul 2 5⟧ = 2 × 5
     ⟦42⟧ = 42
 ⟦neg 42⟧ = -42
```

We can define the **abstract syntax** of such a language in [Backus-Naur form](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form):

```
n ∈ Int ::= ... | -1 | 0 | 1 | 2 | ...
e ∈ Exp ::= add e e
         |  mul e e
         |  neg e
         |  n
```

All expressions map to an integer eventually. Therefore we can say, the **semantic domain** of this language is the set of all integers ℤ.

In fact, this definition is equivalent to how Haskell's [numerals-base](https://hackage.haskell.org/package/numerals-base-0.3/docs/Text-Numeral-Exp.html) package encodes a numeral using the `data` keyword and a `type` alias.

```haskell
type ℤ = Integer

-- | An expression that represents the structure of a numeral.
data Exp = Lit ℤ
         | Neg Exp
         | Add Exp Exp
         | Mul Exp Exp
```

You can work out the rest of the implementation for evaluating those expressions in Haskell, but it's beyond the scope of this document. Essentially, you need a way of assigning a value from the domain ℤ, to each and every expression that this syntax can produce. Namely, a **valuation function**.

```
      ⟦Exp⟧ : Int
⟦add e1 e2⟧ = ⟦e1⟧ + ⟦e2⟧
⟦mul e1 e2⟧ = ⟦e1⟧ × ⟦e2⟧
    ⟦neg e⟧ = -⟦e⟧
        ⟦n⟧ = n
```

# Algebraic data types

As you see, _domain_ has a very precise meaning in denotational semantics. Haskell's `data` keyword allows writing structured **type** definitions that describe the **composition** of different domains, as well.

`Maybe` is actually a sum type which is defined as follows:

```haskell
data Maybe a = Just a | Nothing
```

A type such as this is also known as an [algebraic data type](https://en.wikipedia.org/wiki/Algebraic_data_type) (ADT for short):

* [Sum types](https://en.wikipedia.org/wiki/Tagged_union) are used for _alternation_: `A | B` meaning `A` or `B` but not both.
* [Product types](https://en.wikipedia.org/wiki/Product_type) are used for _combination_: `A B` meaning `A` and `B` together.

Here is an example of how a binary tree would be declared in Haskell:

```haskell
data Tree = Empty
          | Leaf Int
          | Node Int Tree Tree

tree = Node 1 (Leaf 2) (Node 3 (Leaf 4) Empty)
```

# Example: Move language

>> Move language specification is taken from [Eric Walkingshaw](https://web.engr.oregonstate.edu/~walkiner/)'s [CS581 lecture notes](https://web.engr.oregonstate.edu/~walkiner/teaching/cs581-fa20).

In the following **Move** program, each `go` command instructs a robot to move n steps in the given direction. A semicolon is used for chaining a sequence of steps.

```
go E 3; go N 4; go S 1;
```

* Each `go` command constructs a new **Step**, an n-unit horizontal or vertical movement.
* A **Move** is expressed as a sequence of steps separated by a semicolon.

```
n ∈ Nat  ::= 0 | 1 | 2 | ...
d ∈ Dir  ::= N | S | E | W
s ∈ Step ::= go d n
m ∈ Move ::= ε | s ; m
```

(Epsilon stands for empty string.)

The same syntax can have many different meanings.

### Finding the total distance

Here is a how a Step or a Move expression would be evaluated for summing up the total distance a robot needs to travel. In that case, the semantic domain is the set of all natural numbers ℕ.

```
  S⟦Step⟧ : Nat
S⟦go d k⟧ = k

  M⟦Move⟧ : Nat
     M⟦ε⟧ = 0
   M⟦s;m⟧ = S⟦s⟧ + M⟦m⟧
```

### Moving robots around

Based on its current position on a 2d plane, a robot should be able to compute a target position to move into. In this scenario, a Move program's semantic domain is the set of all functions that map a position (x,y) pair into another one:

```
⟦Expr⟧ : Pos → Pos
```

To denote functions, we'll use a mathematical formalism which is called [Lambda calculus](https://en.wikipedia.org/wiki/Lambda_calculus). Without going into too much detail: λ-calculus is used for explicitly expressing the basic notions of function abstraction and application. It's the world's first programming language, and arguably the simplest.

This is the complete BNF grammar of λ-calculus:

```
e ::= x            // variable
    | e e          // function application
    | λ x . e      // function definition
```

Lambda abstractions are expressed in the form of `λx.y`, where `x` is the variable of the function and `y` is its body.

> For practicality, λ-calculus is extended to include `+` and `-` operators in the following example. Also in pure lambda, all functions are [unary](https://en.wikipedia.org/wiki/Currying); there are no numbers, no operators, no booleans, no if/else, no loops, no self references, no recursions. But still it is _sufficiently expressive_ to compute anything a Turing machine can compute. [Go figure](https://en.wikipedia.org/wiki/Church%E2%80%93Turing_thesis).

That said, here is how we evaluate Step expressions into λ terms:

```
  S⟦Step⟧ : Pos → Pos
S⟦go N k⟧ = λ(x,y).(x,y+k)
S⟦go S k⟧ = λ(x,y).(x,y−k)
S⟦go E k⟧ = λ(x,y).(x+k,y)
S⟦go W k⟧ = λ(x,y).(x−k,y)
```

A Move expression is composed of Step expressions and it can be likened to a pipeline where each Step is passed the result of the one it succeeds. In the case of an empty string after a semicolon, it simply returns the position passed without making any changes.

```
M⟦Move⟧ : Pos → Pos
   M⟦ε⟧ = λp.p
 M⟦s;m⟧ = M⟦m⟧ ◦ S⟦s⟧
```

The **◦** operator means [function composition](https://en.wikipedia.org/wiki/Function_composition): a [higher-order function](https://en.wikipedia.org/wiki/Higher-order_function) which takes one or more functions as arguments and returns a function as a result.

Functional programming is all about function composition, and we'll discover more about it in my upcoming [FP primer](./fp-primer.html) posts. For now, let's just note that function composition is really is no different than adding two numerals or multiplying them. Those are both associative binary operations with identity elements; so does the composition of functions. That is, if `f`, `g` and `h` are composable, then `f ∘ (g ∘ h) = (f ∘ g) ∘ h`.

Finally, here is how Move expressions would be evaluated in Python for finding a target position:

```python
# M⟦ε⟧ = λp.p
def empty():
  def move(p):
    return p
  return move

# M⟦m⟧ ◦ S⟦s⟧
def compose(f, g):
  def move(x):
    return f(g(x))
  return move

# S⟦go N k⟧ = λ(x,y).(x,y+k)
def go_n(k):
  def step(pos):
    x = pos[0]
    y = pos[1]+k
    return (x, y)
  return step

# S⟦go E k⟧ = λ(x,y).(x+k,y)
def go_e(k):
  def step(pos):
    x = pos[0]+k
    y = pos[1]
    return (x, y)
  return step

# go E 3; go N 4; go E 3;
run = compose(compose(go_e(3), go_n(4)), go_e(3))

initial_pos = (0,0)
target_pos = run(initial_pos)

print(target_pos)
# Output:
# (6,4)
```

[^spj-book]: Simon L. Peyton Jones, [The implementation of functional programming languages (P29)](https://www.microsoft.com/en-us/research/wp-content/uploads/1987/01/slpj-book-1987-small.pdf)
