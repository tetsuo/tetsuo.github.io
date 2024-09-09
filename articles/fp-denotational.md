---
title: What makes Haskell click
description: What makes Haskell click
cover_title: Understanding FP semantics
tags: haskell,fp,language
published: 2023-05-30T12:41:00
updated: 2024-09-08T01:20:00
---

> Exploring denotational semantics &mdash;a mathematical approach to defining what programs mean.

In Haskell, a **function** is a fixed mapping between inputs (arguments) and their corresponding values. Here is an example demonstrating the Fibonacci sequence.

```haskell
fib :: Integer -> Integer
fib 0 = 0
fib 1 = 1
fib n = fib (n-1) + fib (n-2)
```

This defines `fib` as a function that takes an integer `n` and returns the nth Fibonacci number. Each case acts like an equation, defining the relationship between input and output. `fib n` runs recursively until the base case is reached and a sum is returned.

This view of a function is called [denotational](https://en.wikipedia.org/wiki/Denotational_semantics). We define its "meaning" by establishing relationships between inputs and outputs. This contrasts with [operational semantics](https://en.wikipedia.org/wiki/Operational_semantics), where functions are seen as sequences of _operations_ executed over time.

Each expression can be understood based on its mathematical equivalent. For example, `fib 1` and `5-4` both represent the integer 1 in the program. We say they _denote_ the same value.

>> The collection of such mathematical objects is called the **semantic domain**. Broadly speaking, denotational semantics is concerned with finding domains that represent what programs do; it aims to provide a mathematical foundation for understanding program behavior.

Note that here, the meaning of `fib 2` is derived from the meanings of `fib 1` and `fib 0`. This **compositional** property is foundational for building _formal proofs of program correctness_ within denotational semantics.

To ensure compositionality, an expression must be [referentially transparent](https://en.wikipedia.org/wiki/Referential_transparency), meaning it can be substituted with its equivalent value without altering the program's outcome.

For instance, a function adding two numbers is referentially transparent. In contrast, a function that divides a number by another is not, because the divisor can be zero.

```haskell
> 10 `div` 2
5
> 10 `div` 0
*** Exception: divide by zero
```

Dividing by zero is undefined, which is a side effect in this case, resulting in an exception.

### Dealing with side-effects

To handle division by zero, Haskell offers the [`Maybe`](https://wiki.haskell.org/Maybe) data type. It can either hold a value (`Just a`) or indicate no value (`Nothing`). This allows us to ensure a _total_ division function that always return a result, avoiding exceptions.

```haskell
data Maybe a = Just a | Nothing
```

> While we're at it, a type such as this is also known as an [Algebraic Data Type](https://en.wikipedia.org/wiki/Algebraic_data_type) (ADT for short):
>
> * [Sum types](https://en.wikipedia.org/wiki/Tagged_union) are used for _alternation_: `A | B` meaning `A` or `B` but not both.
> * [Product types](https://en.wikipedia.org/wiki/Product_type) are used for _combination_: `A B` meaning `A` and `B` together.

The improved version doesn't produce any observable effects other than its return value:

```haskell
safeDiv :: Integral a => a -> a -> Maybe a
safeDiv a 0 = Nothing
safeDiv a b = Just (a `div` b)
```

By avoiding side effects and state mutations, functional languages such as Haskell, PureScript, and Scala foster a programming environment where the behavior of functions is fully predictable and transparent &mdash;in other words, [_pure_](https://en.wikipedia.org/wiki/Pure_function). This brings us to our main topic.

# Denotational semantics

Denotational semantics is a formal method for describing the meaning of programs by mapping each expression to a mathematical object. It supports equational reasoning, as we've seen, and focuses on _what_ a program computes, rather than _how_ it computes it.

Imagine a box `⟦⟧` that evaluates programs into mathematical objects. You place any **expression** inside, and the box gives you its corresponding **value**.

This can be represented as `⟦E⟧ : V`, where `E` represents an expression (syntactic object) built according to the programming language's rules, while `V` represents the abstract value (e.g., a number, a function).

#### Example: Calculator syntax

Here are some arithmetic expressions in prefix notation:

```
⟦add 1 2⟧ = 1 + 2
⟦mul 2 5⟧ = 2 × 5
     ⟦42⟧ = 42
 ⟦neg 42⟧ = -42
```

We can define the **abstract syntax** of such expressions using [Backus-Naur form](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form):

```
n ∈ Int ::= ... | -1 | 0 | 1 | 2 | ...
e ∈ Exp ::= add e e
         |  mul e e
         |  neg e
         |  n
```

Here, all expressions eventually evaluate to integers, so the **semantic domain** is the set of all integers (ℤ). This definition aligns with how Haskell's [numerals-base](https://hackage.haskell.org/package/numerals-base-0.3/docs/Text-Numeral-Exp.html) package encodes numerals using the `data` keyword.


```haskell
type ℤ = Integer

-- | An expression that represents the structure of a numeral.
data Exp = Lit ℤ
         | Neg Exp
         | Add Exp Exp
         | Mul Exp Exp
```

While the specifics of evaluating these expressions are beyond our scope, the key is to assign a value from the domain (ℤ) to every possible expression this syntax can generate. This function that assigns values is called a **valuation function**.

```
      ⟦Exp⟧ : Int
⟦add e1 e2⟧ = ⟦e1⟧ + ⟦e2⟧
⟦mul e1 e2⟧ = ⟦e1⟧ × ⟦e2⟧
    ⟦neg e⟧ = -⟦e⟧
        ⟦n⟧ = n
```

# Move language

>> Move language specification is taken from [Eric Walkingshaw](https://web.engr.oregonstate.edu/~walkiner/)'s [CS581 lecture notes](https://web.engr.oregonstate.edu/~walkiner/teaching/cs581-fa20).

This example introduces a simple robot language called "Move". It uses commands like `go E 3` to instruct a robot to move specific steps in a direction.

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

Let's explore two interpretations of Move programs.

### Find total distance

We define a semantic domain of natural numbers (ℕ) and functions that compute the total distance the robot travels.

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

### Find target position

The semantic domain then becomes the set of all **functions** that map a starting position (x, y) to a target position after executing the Move program.

```
⟦Expr⟧ : Pos → Pos
```

This involves using [Lambda calculus](https://en.wikipedia.org/wiki/Lambda_calculus) (λ-calculus) to express functions for each movement, the world's first programming language.

Lambda abstractions are expressed in the form of `λx.y`, where `x` is the variable of the function and `y` is its body. This is the complete BNF grammar of λ-calculus:

```
e ::= x            // variable
    | e e          // function application
    | λ x . e      // function definition
```

For practical purposes, we'll extend lambda calculus to include addition and subtraction operators in the following examples. It's important to note that pure lambda calculus is inherently simpler, with only unary functions and no built-in arithmetic or control flow constructs. Surprisingly, even with these limitations, [it's theoretically capable of computing anything a Turing machine can](https://en.wikipedia.org/wiki/Church%E2%80%93Turing_thesis).

Here, we evaluate Step expressions into λ terms to find a target position:

```
  S⟦Step⟧ : Pos → Pos
S⟦go N k⟧ = λ(x,y).(x,y+k)
S⟦go S k⟧ = λ(x,y).(x,y−k)
S⟦go E k⟧ = λ(x,y).(x+k,y)
S⟦go W k⟧ = λ(x,y).(x−k,y)
```

A Move expression is a sequence of Step expressions. It can be visualized as a pipeline where each Step processes the output of the preceding one. An empty Move expression, represented by an empty string, simply returns the input position unchanged.

```
M⟦Move⟧ : Pos → Pos
   M⟦ε⟧ = λp.p
 M⟦s;m⟧ = M⟦m⟧ ◦ S⟦s⟧
```

The **◦** operator means [function composition](https://en.wikipedia.org/wiki/Function_composition): a [higher-order function](https://en.wikipedia.org/wiki/Higher-order_function) which takes one or more functions as arguments and returns a function as a result.

Note that, function composition shares similarities with arithmetic operations like addition and multiplication. Both are associative binary operations with identity elements. For instance, just as `(a + b) + c` equals `a + (b + c)`, the composition of functions follows the same pattern: that is, if `f`, `g` and `h` are composable, then `f ∘ (g ∘ h)` is equivalent to `(f ∘ g) ∘ h`.

> As you may know, functional programming languages draw a lot of inspiration from [category theory](https://en.wikipedia.org/wiki/Category_theory), the _science_ of composition. Category theory formalizes the concept of composition and structure, providing a robust framework for reasoning about program behavior. While not strictly necessary for coding (and definitely out of scope today), understanding this mathematical foundation offers valuable insights into languages like Haskell.

Before concluding, let's see how Move expressions can be evaluated in Python to determine a target position.

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
