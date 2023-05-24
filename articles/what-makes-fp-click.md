---
title: What makes functional programming click?
description: Things to know about functional programming before jumping on the lambda train
cover_title: Intro to FP
tags: haskell,fp,language
published: 2023-05-22T12:41:00
updated: 2023-05-22T12:41:00
---

> Things to know about FP before jumping on the lambda train.

This post is the first of a series, which I think may be useful for those learning functional programming.

# Ways of expressing

Functional programming is **declarative**, meaning that computation's logic is expressed without describing its control flow. In contrast, languages like C, Python etc. are **imperative**. In those languages, you use statements like `if/else` and `while` to change a program's state.

For example, [HTML](https://en.wikipedia.org/wiki/HTML) is a declarative [markup language](https://en.wikipedia.org/wiki/Markup_language), it only describes _what_ should appear on a browser window.

```html
<article>
  <p>I'm a paragraph text.</p>
</article>
```

In contrast, you interact with [the HTML DOM API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_DOM_API) imperatively. You give it a series of instructions that tells _how_ something should appear.

```js
let article = document.createElement("article");
let p = document.createElement("p");
p.append("I'm a paragraph text.");
article.append(p);
```

HTML is designed as a markup language, it's not [Turing-complete](https://en.wikipedia.org/wiki/Turing_completeness). It needs an interpreter which will traverse an HTML tree and call the DOM API to draw elements on your screen. Nevertheless, it's a good idea. Trees and grids... You can almost picture a webpage's layout in your mind just by looking at its HTML code. It's almost like how composers can hear the music just by looking at musical notes.

Let's also not forget that HTML is also one of the building blocks of a thing called the semantic web where it is used to define some knowledge object and its relationships to other knowledge objects, and etc.

While we're at it, the web is not the only semantic domain that we can represent using trees and graphs this way. Many other things may fall under this category. For instance, this is a sample from [Virtual Human Markup Language (VHML)](https://en.wikipedia.org/wiki/Computer_facial_animation#Face_animation_languages) which is used to describe facial expressions in animations.

```xml
<vhml>
  <person disposition="angry">
    First I speak with an angry voice and look very angry,
    <surprised intensity="50">
      but suddenly I change to look more surprised.
    </surprised>
  </person>
</vhml>
```

## What happened to side effects?

More importantly, a DSL give us the ability to write programs without worrying about the _side effects_ under the hood. Side effects such as rendering HTML elements or animating a face, outputting to console, playing a sound, selling stocks, injecting the right dose of insulin into someone's bloodstream. You know, [side effects](https://en.wikipedia.org/wiki/Side_effect_(computer_science)).

In imperative programming, side effects are explicit, but the result is hidden. We have a list of instructions, but we don't know _what_ the result is going to look like in the end. Conversely, in declarative programming, the result is explicit, but side effects are implicit. We know what is going to happen, but not _how_. Yet, the lack of side effects makes it easier to do [formal verification](https://en.wikipedia.org/wiki/Formal_verification) of a program which in turn increases our chance to write [correct](https://en.wikipedia.org/wiki/Correctness_(computer_science)) code.

# Making sense of the syntax

Syntactically speaking, HTML has everything it needs to become a Turing complete programming language. In fact there is a programming syntax called [S-Expression](https://en.wikipedia.org/wiki/S-expression) which is structurally identical to XML.

[![Cassidy.1985.015.gif](./Cassidy.1985.015.gif)](./Cassidy.1985.015.gif)

This is the standard definition of the [Fibonacci sequence](https://rosettacode.org/wiki/Fibonacci_sequence) written in [Lisp](https://en.wikipedia.org/wiki/Lisp_(programming_language)), a real programming language from the 1960s. Replace parentheses with angle brackets, you have an XML tree instead.

```lisp
(defun fibonacci(n)
  (cond
    ((eq n 0) 0)
    ((eq n 1) 1)
    ((+ (fibonacci (- n 1)) (fibonacci (- n 2))))))
```

Lisp uses [prefix notation](https://en.wikipedia.org/wiki/Polish_notation) by the way, but deciphering it shouldn't be too hard.

Actually, let's see its modern equivalent in [Haskell](https://www.haskell.org/). It has the same internal structure but with a simpler syntax and a type annotation.

```haskell
fib :: Integer -> Integer
fib 0 = 0
fib 1 = 1
fib n = fib (n-1) + fib (n-2)
```

Indeed, this is the Fibonacci sequence defined by the linear recurrence equation:

<math display="block">
  <mrow>
    <msub>
      <mi>F</mi>
      <mi>n</mi>
    </msub>
    <mo>=</mo>
    <msub>
      <mi>F</mi>
      <mrow>
        <mi>n</mi>
        <mo>−</mo>
        <mn>1</mn>
      </mrow>
    </msub>
    <mo>+</mo>
    <msub>
      <mi>F</mi>
      <mrow>
        <mi>n</mi>
        <mo>−</mo>
        <mn>2</mn>
      </mrow>
    </msub>
  </mrow>
</math>

Furthermore, what we have in here consists of equations again (and not assignments), each of which establishes an equality between the left and right hand sides of the equal sign. Even if you don't know anything about Haskell, you can still make the conclusion that each case expects some input integer to conform to a given pattern, `0`, `1` or `n` and outputs a Fibonacci number. `fib n` runs recursively until the base case is reached and a sum is returned.

This is an elegant idea for defining functions, **equational reasoning** isn't something that many are unfamiliar with. We learn it in elementary school. Perhaps there must be some clever way to evaluate these kinds of expressions.

But, before going into that, isn't C the same?

```c
int fib(int n) {
  if (n <= 1) {
    return n;
  }
  return fib(n-1) + fib(n-2);
}
```

Replace `if` with a ternary operator like in JavaScript, you end up with the following definition. This also looks declarative to me.

```js
const fib = n => n <= 1 ? n : fib(n-1) + fib(n-2)
```

# Denotational semantics

> There are two ways of looking at a function: as an algorithm which will produce a value given an argument, or as a set of ordered argument-value pairs. The first view is "dynamic" or **operational**, in that it sees a function as a sequence of operations in time. The second view is "static" or **denotational**: the function is regarded as a fixed set of associations between arguments and the corresponding values. &mdash; Simon L. Peyton Jones [^spj-book]

Not exactly. Explicit or not, it wouldn't have made any sense for the C compiler (nor the JavaScript interpreter) if there were no statements to begin with. Simply because a C program is a sequence of commands separated by the **;** symbol&mdash; that's what a C program means.

But for Haskell it makes perfect sense. Why? What does a Haskell program _mean_ then?

One seemingly unrelated triangle, the [semiotic triangle](https://en.wikipedia.org/wiki/Triangle_of_reference), says that in order for something to make sense there needs to be a relation such that:

[![semiotic triangle](./Ogden_semiotic_triangle-50.png )](./Ogden_semiotic_triangle-50.png)

Now take the bottom edge of the semiotic triangle, and imagine that we have this magical box (like **⟦⟧**) which evaluates programmatic objects (like syntax) into [mathematical objects](https://en.wikipedia.org/wiki/Mathematical_object) (like values).

That is to say, you put any programmatic expression inside this box and on the other end of the equation you get something real, something that exists beyond thought, language and the known universe, like the integer 10 for instance.

```
⟦add 1 2⟧ = 1 + 2
⟦mul 2 5⟧ = 2 × 5
```

or, in infix form with symbols instead:

```
⟦2 * 5⟧ = 2 × 5
   ⟦10⟧ = 10
```

> In functional programming, we understand the "true meaning" of a program, because we know the mathematical object it denotes. As an example, the mathematical object for the Haskell programs `10`, `9+1`, `2*5` and `sum [1..4]` can be represented by the integer 10. We say that all those programs _denote_ the integer 10, an element of the set ℤ. [^haskell-denotation]

With this, we can deduce that the expression `fib 0` _means_ 0, `fib 1` _means_ 1, and `fib 2` which is equivalent to `fib (2-1) + fib (2-2)` _means_ 0 &plus; 1, or simply integer 1.

We also understand from this example that [denotational semantics](https://en.wikipedia.org/wiki/Denotational_semantics) is **compositional**. `fib 2` depends on the meaning of its constituents, `fib 1` and `fib 0`.

It can be said that the denotation (or the meaning) of our simple `fib n` expression is the n-th Fibonacci number. The collection of such mathematical objects is called the **semantic domain**. Our semantic domain is in this case the Fibonacci sequence.

## Example: Arithmetic

So what do we need for creating a DSL for simple arithmetics? [^numerals-base]

We first define a semantic **domain**, for instance, the set of all integers ℤ.

Then, we define the **abstract syntax** using a metasyntax notation such as [Backus-Naur form](https://en.wikipedia.org/wiki/Backus%E2%80%93Naur_form).

```
n ∈ Int ::= ... | -1 | 0 | 1 | 2 | ...
e ∈ Exp ::= add e e
         |  mul e e
         |  neg e
         |  n
```

And finally, we define the **valuation** aka the semantic function:

```
      ⟦Exp⟧ : Int
⟦add e1 e2⟧ = ⟦e1⟧ + ⟦e2⟧
⟦mul e1 e2⟧ = ⟦e1⟧ × ⟦e2⟧
    ⟦neg e⟧ = -⟦e⟧
        ⟦n⟧ = n
```

Here we go, we created an arithmetic expression language:

```
       ⟦add 1 2⟧ = 1 + 2
       ⟦mul 2 5⟧ = 2 × 5
⟦add mul 2 4 10⟧ = 2 × 4 + 10
```

Note that, a syntax doesn't necessarily have to be textual. In fact, when you hear FP folks talking about a DSL, it often means a library in a host language like Haskell, not a separate language.

You define an abstract syntax in Haskell using the `data` keyword:

```haskell
-- | An expression that represents the structure of a numeral.
data Exp   -- | A literal value.
         = Lit ℤ
           -- | Negation of an expression.
         | Neg Exp
           -- | Addition of two expressions.
         | Add Exp Exp
           -- | Multiplication of two expressions.
         | Mul Exp Exp
```

And a semantic domain using the `type` keyword:

```haskell
type ℤ = Integer
```

This is comparable to the following TypeScript definition generated by [fp-ts-codegen](https://gcanti.github.io/fp-ts-codegen/).

```typescript
export type Exp = {
    readonly type: "Lit"
    readonly value0: Nat
} | {
    readonly type: "Neg"
    readonly value0: Exp
} | {
    readonly type: "Add"
    readonly value0: Exp
    readonly value1: Exp
} | {
    readonly type: "Mul"
    readonly value0: Exp
    readonly value1: Exp
}
```

## Example: Robot language

In the following syntax, each `go` command instructs our robot to move n steps in the given direction. A semicolon is used to chain a sequence of steps. [^denot-walkingshaw]

```
go E 3; go N 4; go S 1;
```

* We can say that each `go` command constructs a new **Step**, an n-unit horizontal or vertical movement.
* A **Move** then is expressed as a sequence of steps separated by semicolon.

```
n ∈ Nat  ::= 0 | 1 | 2 | ...
d ∈ Dir  ::= N | S | E | W
s ∈ Step ::= go d n
m ∈ Move ::= ε | s ; m
```

(Epsilon stands for empty string.)

### Finding the total distance

We can evaluate the expression `go E 3; go N 4;` into the total number of steps needed to finish executing a move.

```
            ⟦Move⟧ : Int
M⟦go E 3; go N 4;⟧ = 7
```

In that case, the semantic domain will be the set of all natural numbers. We can define a valuation function which sums up the total distance given a Step or a Move expression:

```
  S⟦Step⟧ : Int
S⟦go d k⟧ = k

  M⟦Move⟧ : Int
     M⟦ε⟧ = 0
   M⟦s;m⟧ = S⟦s⟧ + M⟦m⟧
```

### Moving on a 2d plane

Imagine our robots are placed on a 2d plane and that they already have a mechanism of their own for moving from one (x,y) position to another.

In this case, we will need our programs to help find a target position given an initial (x,y) position to actually move a robot on a 2d plane. So far it sounds like our semantic domain needs to be the set of all functions from one position to another: `ƒ : Pos → Pos`

To express functions, we'll use **λ-calculus** (Lambda Calculus): a specialized function notation which is used to explicitly express the basic notions of function abstraction and application. I'll explain why it's very important in the next section, but for now you can think of those λ expressions on the right hand side as normal functions (e.g. `(x, y) => (x, y + k)`).

```
  S⟦Step⟧ : Pos → Pos
S⟦go N k⟧ = λ(x,y).(x,y+k)
S⟦go S k⟧ = λ(x,y).(x,y−k)
S⟦go E k⟧ = λ(x,y).(x+k,y)
S⟦go W k⟧ = λ(x,y).(x−k,y)

  M⟦Move⟧ : Pos → Pos
     M⟦ε⟧ = λp.p
   M⟦s;m⟧ = M⟦m⟧ ◦ S⟦s⟧
```

The **◦** operator means [function composition](https://en.wikipedia.org/wiki/Function_composition). In the jungle, it is said that, if `f` and `g` are two functions then `(g◦f)` is the function such that `(g◦f)(x) = g(f(x))` for every value of `x`. It is also said that a [higher-order function](https://en.wikipedia.org/wiki/Higher-order_function) is a function which takes one or more functions as arguments and returns a function as a result.

A Move expression is composed of Step expressions and it can be likened to a pipeline where each Step is passed the result of the one it succeeds. In the case of an empty string after a semicolon, we simply return the position passed without making any changes.

Here is roughly how that would be implemented in Python.

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

initial_pos = (0,0)

# go E 3; go N 4; go E 3;
program = compose(compose(go_e(3), go_n(4)), go_e(3))

print(program(initial_pos))
# Output:
# (6,4)
```

# λ-calculus

In 1937, [Alan Turing](https://en.wikipedia.org/wiki/Alan_Turing) conceptualized a [machine with a mutable state](https://en.wikipedia.org/wiki/Turing_machine) to show that a general solution to [the decision problem](https://en.wikipedia.org/wiki/Entscheidungsproblem) is impossible.

His solution inspired others and within a decade it gave rise to the [Von-Neumann architecture](https://en.wikipedia.org/wiki/Von_Neumann_architecture) which eventually evolved into the modern PCs we use today.

Computing machines... _with memories._

This is not the end of the story though. The same year a man named [Alonzo Church](https://en.wikipedia.org/wiki/Alonzo_Church) invented a type of mathematical formalism he called [**λ-calculus**](https://en.wikipedia.org/wiki/Lambda_calculus) which [happens to be equivalent](https://en.wikipedia.org/wiki/Church%E2%80%93Turing_thesis) to a [Turing machine](https://en.wikipedia.org/wiki/Turing_machine). Anything a Turing machine can do, Lambda calculus can do, and vice versa.

It is a specialized function notation which he used to explicitly express the basic notions of function abstraction and application. It's the world's first programming language and arguably the simplest.

This is the complete BNF grammar of Lambda calculus:

```
e ::= x            // variable
    | e e          // function application
    | λ x . e      // function definition
```

Lambda abstractions are expressed in the form of `λx.y`, where `x` is the variable of the function and `y` is its body. Lambda functions are identical to functions in programming except that they are [unary](https://en.wikipedia.org/wiki/Unary_function).

> Also, "The procedure of viewing a multiple-arity operation as a sequence of abstractions that yield an equivalent unary operation is called [_currying_](https://en.wikipedia.org/wiki/Currying) the operation." [^plato-lambda-calculus] &mdash; It is a reference to logician [Haskell Curry](https://en.wikipedia.org/wiki/Haskell_Curry).

Examples in JavaScript:

```js
// λx.x
I = x => x

// λxy.yx
T = x => f => f(x)

// λf.(λx.f(λy.xxy)) (λx.f(λy.xxy))
Z = f => (x => f(y => x(x)(y)))(x => f(y => x(x)(y)))
```

In the robot language, for practicality, I extended λ-calculus to include `+` and `-` operators. In pure lambda there are no numbers, no operators, no booleans, no if/else, no loops, no self references, no recursions, but still it is _sufficiently expressive_ to compute anything a Turing machine can compute. Go figure.

Turing machines are state-based model of computation. Church captures a function-based model of computation. If it's true that they are equivalent, then we should be able to encode all these  abstract concepts, which we encounter while programming, using only functions and nothing else.

In fact a lot of these _combinator_ functions with one-letter names you've been seeing lately are coming from [combinatory logic](https://en.wikipedia.org/wiki/Combinatory_logic) (which is a variant of λ-calculus) and they are used to denote certain notions of computation such as recursions like the infamous [Y combinator](https://en.wikipedia.org/wiki/Fixed-point_combinator) does. [^y-combinator]

You'll hear that word a lot but it's important to understand in the beginning, the meaning of "combinator" is a more informal sense referring to the style of organizing libraries centered around the idea of combining things as we'll see in the next section, and not strictly to combinatory logic.

> Check out [Raymond Smullyan](https://en.wikipedia.org/wiki/Raymond_Smullyan)'s [To Mock a Mockingbird](https://en.wikipedia.org/wiki/To_Mock_a_Mockingbird) if you want to learn more about combinatory logic.

# Total and partial functions

An expression is said to be _referentially transparent_ if it can be replaced with its corresponding value without changing the program's behavior. Since we only use [pure functions](https://en.wikipedia.org/wiki/Pure_function) (functions that have no side-effects) in FP, we can replace any function application with its output.

Besides, without this property we wouldn't be able to achieve _compositionality_ needed for denotational semantics and equational reasoning to work their magic in the first place. These are the two main pillars of functional programming: [referential transparency](https://en.wikipedia.org/wiki/Referential_transparency) and [composition](https://en.wikipedia.org/wiki/Principle_of_compositionality).

Let me give an example: a function that adds two numbers is referentially transparent, but a function that divides a number by another is not, simply because the divisor can be zero and division by zero is undefined. In a lot of languages (including Haskell) division by zero throws an exception (a side-effect) since _division_ is a [partial function](https://en.wikipedia.org/wiki/Partial_function).

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

# Algebraic Data Types (ADTs)

`Maybe` is a sum type which is defined as follows:

```haskell
data Maybe a = Just a | Nothing
    deriving (Eq, Ord)
```

In Haskell, we use [ADTs](https://en.wikipedia.org/wiki/Algebraic_data_type) to define domains which combine other semantic domains.

* [**Sum types**](https://en.wikipedia.org/wiki/Tagged_union) are used for _alternation_: `A | B` meaning `A` or `B` but not both.
* [**Product types**](https://en.wikipedia.org/wiki/Product_type) are used for _combination_: `A B` meaning `A` and `B` together.

Here is an example of how a binary tree would be declared in Haskell:

```haskell
data Tree = Empty
          | Leaf Int
          | Node Int Tree Tree

tree = Node 1 (Leaf 2) (Node 3 (Leaf 4) Empty)
```

Finally, following is the semantic function for including a total distance report along with a movement for our robot language.

```
 M⟦Move⟧ : Pos → Pos
Md⟦Move⟧ : Int

Mc⟦Move⟧ : Int × (Pos → Pos)
   Mc⟦m⟧ = (Md⟦m⟧, M⟦m⟧)
```

`Md` stands for the function we defined earlier for finding the distance. `Mc` then returns a tuple (a product) of the total distance calculated along with a function which would calculate a target location.

# Higher-kinded polymorphism &mdash;i.e. abstraction over type _constructors_

In Object-oriented Programming (OOP), an _instance_ is an individual object which belongs to a certain type of class.

In Haskell, [type classes](https://en.wikipedia.org/wiki/Type_class) are defined by specifying a set of functions (together with their respective types) that must exist for every type that belongs to the class. So types can be parameterized; a type class `Eq` intended to contain types that admit equality would be declared in the following way:

```haskell
class Eq a where
  (==) :: a -> a -> Bool
  (/=) :: a -> a -> Bool
```

`Maybe` data type is an _instance_ of `Eq` and `Ord` type classes (respectively for equality and ordering) and provides implementations for the operators/functions defined on them. It is also said to be a [type constructor](https://wiki.haskell.org/Constructor) for this reason.

This type of polymorphism is called [higher-kinded polymorphism](https://en.wikipedia.org/wiki/Kind_(type_theory)). So just as [higher-order functions](https://en.wikipedia.org/wiki/Higher-order_function) abstract both first-order values and functions, higher-kinded types (HKTs for short) abstract both types and type constructors. [^lightweight-hkt]

# Function composition

So far we've seen how denotational semantics is baked into FP languages and how Haskell marries abstract syntax into lambda terms.

Earlier in the arithmetic example we turned syntactic expressions like `add 1 2` and `mul 2 5` into `1 + 2` and `2 × 5`. Note that addition and multiplication are both [associative](https://en.wikipedia.org/wiki/Associative_property) binary operations with identity elements.

In the robot language we composed function domains to denote a chain of steps. The composition of functions is also associative. That is, if `f`, `g` and `h` are composable, then `f ∘ (g ∘ h) = (f ∘ g) ∘ h`. Since the result won't change, it doesn't matter in which order the steps are added to each other.

Now get ready for the impact. This is the schematic representation (namely, a [commutative diagram](https://en.wikipedia.org/wiki/Commutative_diagram)) of a [Category](https://en.wikipedia.org/wiki/Category_(mathematics)) from [Category theory](https://en.wikipedia.org/wiki/Category_theory): a general theory for describing abstract structures and their relations. [^category-id] It is used in almost all areas of mathematics, NLP, AI and even in physics.

[![commutative-morphism-50.png](./commutative-morphism-50.png)](./commutative-morphism-50.png)


# † In Category We Trust †

It turns out we've been modeling our language semantics with a **Category** from the very beginning.

A [Category](https://en.wikipedia.org/wiki/Category_(mathematics)) is like a Set except that it focuses not on objects (as elements) but on the relations or **morphisms between objects**; _how things relate_ to each other.

What's more, "[Type theory](https://en.wikipedia.org/wiki/Type_theory) and a [certain kind of category theory](https://en.wikipedia.org/wiki/Cartesian_closed_category) are closely related. By a syntax-semantics duality one may view type theory as a formal syntactic language or _calculus_ for category theory, and conversely one may think of category theory as providing _semantics_ for type theory." [^ncat-category-theory]

A _type_ by itself doesn't mean anything in programming. It only starts to make sense as a notion when you try to connect it with other types. So when you apply a function, you go from one type to another: `ƒ : A → B`. This corresponds to a morphism in category theory: `f : A ⟼ B`, but it also corresponds to an [entailment](https://en.wikipedia.org/wiki/Logical_consequence) in logic: `A ⊢ B`.

```
if A ⊢ B and B ⊢ C then A ⊢ C
```

> "The doctrine of _computational trinitarianism_ holds that computation manifests itself in three forms: **proofs of propositions**, **programs of a type**, and **mappings between structures**. These three aspects give rise to three sects of worship: **Logic**, which gives primacy to proofs and propositions; **Languages**, which gives primacy to programs and types; **Categories**, which gives primacy to mappings and structures. The central dogma of computational trinitarianism holds that Logic, Languages, and Categories are but three manifestations of one divine notion of computation. There is no preferred route to enlightenment: each aspect provides insights that comprise the experience of computation in our lives. Computational trinitarianism entails that any concept arising in one aspect should have meaning from the perspective of the other two.  If you arrive at an insight that has importance for logic, languages, and categories, then you may feel sure that you have elucidated an essential concept of computation&mdash;you have made an enduring scientific discovery." &mdash; [Robert Harper, The Holy Trinity.](https://existentialtype.wordpress.com/2011/03/27/the-holy-trinity/)  [^curry-howard]

And what does this all mean for [the humble programmer](https://www.cs.utexas.edu/~EWD/transcriptions/EWD03xx/EWD340.html)?

It means a **gold mine of abstractions** waiting to be excavated.

[^haskell-denotation]: Haskell wiki: [Denotational semantics](https://en.wikibooks.org/wiki/Haskell/Denotational_semantics)
[^spj-book]: Simon L. Peyton Jones, [The Implementation of Functional Programming Languages](https://www.microsoft.com/en-us/research/wp-content/uploads/1987/01/slpj-book-1987-small.pdf)
[^plato-lambda-calculus]: Stanford Encyclopedia of Philosophy: [The Lambda Calculus](https://plato.stanford.edu/entries/lambda-calculus/)
[^lightweight-hkt]: Libraries like [fp-ts](https://www.github.com/gcanti/fp-ts) emulate HKTs, which TypeScript doesn't support natively. See: [Lightweight higher-kinded polymorphism](https://www.cl.cam.ac.uk/~jdy22/papers/lightweight-higher-kinded-polymorphism.pdf)
[^typed-lambda]: See: [Typed lambda calculus](https://en.wikipedia.org/wiki/Typed_lambda_calculus)
[^numerals-base]: This is [implemented](https://hackage.haskell.org/package/numerals-base-0.3/docs/Text-Numeral-Exp.html) in Haskell as part of the [numerals](https://hackage.haskell.org/package/numerals-base) package
[^curry-howard]: The [Curry–Howard correspondence](https://en.wikipedia.org/wiki/Curry%E2%80%93Howard_correspondence) is the observation that there is an isomorphism between the proof systems, and the models of computation. It is the statement that these two families of formalisms can be considered as identical
[^denot-walkingshaw]: Denotational semantics examples are adapted from [Eric Walkingshaw](https://web.engr.oregonstate.edu/~walkiner/)'s [CS581 lecture notes](https://web.engr.oregonstate.edu/~walkiner/teaching/cs581-fa20/slides/6.DenotationalSemantics.pdf)
[^ncat-category-theory]: ncatlab.org: [Relation between type theory and category theory](https://ncatlab.org/nlab/show/relation+between+type+theory+and+category+theory)
[^category-id]: The category's three identity morphisms, if explicitly represented, would appear as three arrows, from the letters X, Y, and Z to themselves, respectively. See the [full diagram](https://en.wikipedia.org/wiki/Category_(mathematics)#/media/File:Category_SVG.svg)
[^y-combinator]: More at Enrico Piccinin's blog: [Y and Z combinators in Javascript ](https://medium.com/swlh/y-and-z-combinators-in-javascript-lambda-calculus-with-real-code-31f25be934ec)

