---
title: flixbox
description: Movie trailers and typed functional programming in TypeScript
tags: typescript,fp
published: 2023-01-25T12:41:00
updated: 2023-01-25T12:41:00
---

[![flixbox - Search movie trailers](./flixbox.jpg)](https://ogu.nz/wr/flixbox.html)

> [flixbox](https://www.github.com/onur1/flixbox) implements a server and a GUI application for interacting with the [TMDb](https://www.themoviedb.org/) API using typed functional programming library [fp-ts](https://gcanti.github.io/fp-ts/).

## Background

[fp-ts](https://gcanti.github.io/fp-ts/) is a library by [Giulio Canti](https://twitter.com/giuliocanti) that brings the power of [typeclasses](https://en.wikipedia.org/wiki/Type_class) and the [higher kinded types](https://en.wikipedia.org/wiki/Kind_(type_theory)) from functional programming languages (such as [Haskell](https://www.haskell.org/) and [PureScript](https://www.purescript.org/)) into the world of [TypeScript](https://www.typescriptlang.org/).

If you are new to FP, I highly recommend you to watch the first 9 minutes of Philip Wadler's [Propositions as Types](https://www.youtube.com/watch?v=IOiZatlZtGU) talk, so you can get an idea about the earliest work that made this type of programming possible. If you are the adventurous type, you can continue watching the rest of the talk&mdash; don't let the title scare you! But, you most likely won't need to learn how β-reduction works or the other cool stuff in formal logic in order to program a washing machine display. Trust me, for washing machine displays, you only need to know about [the difference between product and sum types](https://dev.to/gcanti/functional-design-algebraic-data-types-36kf).

When I first started learning FP in JS, I was having trouble reading [Hindley Milney](https://en.wikipedia.org/wiki/Hindley%E2%80%93Milner_type_system) type signatures and the projects like [Fantasy Land](https://github.com/fantasyland/fantasy-land) and [Sanctuary](https://sanctuary.js.org/) haven't really helped much due to the heavy Haskell jargon in their documentation. (It seems some Haskellers are having the same syndrome, [but in the opposite direction](https://www.reddit.com/r/typescript/comments/ond5d8/struggling_to_read_typescript_signatures_convert/)).

So, I resorted to [fp-ts](https://github.com/gcanti/fp-ts) for deciphering typeclasses in TypeScript. I was lucky in the meantime that Giulio Canti was bombarding GitHub with a new addition to his toolstack every other day, and the community consisted of only a couple of newbies like myself. _Experts_ had not have arrived yet!

All of the functionality in the application above (including the server side API) is implemented using libraries from the [fp-ts module ecosystem](https://gcanti.github.io/fp-ts/ecosystem/).

These are all very cool ideas from all around the FP world, so let me introduce some of these modules to you and show what makes them so great.

## Flixbox API

Before going into details, here is a quick overview of how the HTTP API works.

#### Requests and data formats

All requests to the flixbox API are HTTP GET requests. API responses are only available in JSON format. No authentication required.

#### Errors

When something goes wrong, flixbox will respond with the appropriate HTTP status code and an error. This can be one of:

- Validation error: User input couldn't be validated.
- Provider error: TMDb failed to respond with valid payload.
- Not found: Requested resource not found.
- Server error: Generic server error.
- Method error: Method not allowed.

### Searching movies

```
GET /results?search_query=QUERY
```

Responds with a [`SearchResultSet`](./src/tmdb/model/SearchResultSet.ts) object.

### Retrieving a movie

```
GET /movie/ID
```

Responds with a [`Movie`](./src/tmdb/model/Movie.ts) object.

### Get popular movies

```
GET /popular
```

Responds with a [`SearchResultSet`](./src/tmdb/model/SearchResultSet.ts) object.

## Type-safe composable HTTP middlewares

The [server side](https://github.com/onur1/flixbox/tree/0.0.6/src/server) API is implemented using [hyper-ts](https://github.com/DenisFrezzato/hyper-ts), the fp-ts porting of [Hyper](https://hyper.wickstrom.tech/). This is an experimental middleware architecture which enforces strict ordering of middleware compositions using static type-checking.

Under the hood, hyper-ts runs [Express](https://expressjs.com/) server, but you can integrate it with any HTTP server you like. You can even use a parser combinator library like [parser-ts](https://github.com/gcanti/parser-ts) to bridge it with the NodeJS Stream API to create your own text protocol.

Hyper is modeled as a [State monad](https://paulgray.net/the-state-monad/)&mdash; it's the combination of [Reader](https://dev.to/gcanti/getting-started-with-fp-ts-reader-1ie5) and [Writer](https://levelup.gitconnected.com/reader-writer-and-state-monad-with-fp-ts-6d7149cc9b85) monads, the kind of [monads](https://dev.to/gcanti/getting-started-with-fp-ts-monad-6k) which allow you to read and write a value in a safe way as their names suggest. In this case, it reads information about the incoming request and writes a response through the Express API.

The main principle is that it doesn't immediately mutate the connection (by writing headers or etc.), but it gives you a list of actions to run in strictly correct order (otherwise your code wouldn't have compiled in the first place) when the middleware has finished processing a request. This concept is also really helpful [while testing](https://github.com/onur1/flixbox/blob/0.0.6/__tests__/server.ts) your applications.

In the example below, you can see the entire pipeline for handling requests to the `/movie/ID` endpoint, it proxies requests to TMDb with caching support.

When [`/movie/3423`](https://onurgunduz.com/flixbox/movie/3423) is called on the flixbox API:

* The server checks the internal cache first:
  * If this movie is already found there, it returns the cached value.
  * Otherwise it calls the TMDb API to retrieve it and saves the result into the cache, returning the newly cached value.
* Responds with a JSON object if the data retrieval succeeded in one way or another.

[`server/Flixbox.ts`](https://github.com/onur1/flixbox/blob/0.0.6/src/server/Flixbox.ts#L87)

```typescript
pipe(
  GET,
  // continue if this is a GET request only
  H.apSecond(
    pipe(
      // retrieve the requested entry from cache
      get(store, `/movies/${String(route.id)}`),
      H.map(entry => entry.value),
      // if not exists, fetch from TMDb
      H.orElse(() =>
        pipe(
          movie(tmdb, route.id),
          H.chain(value =>
            pipe(
              // insert the TMDb response to cache
              put(store, `/movies/${String(route.id)}`, value),
              H.map(entry => entry.value)
            )
          )
        )
      )
    )
  ),
  // write JSON response
  H.ichain(res =>
    pipe(
      H.status<AppError>(200),
      H.ichain(() => sendJSON(res))
    )
  )
)
```

Here, the function we passed into `apSecond` only executes if the preceding `GET` middleware succeeds, and the function we passed into `orElse` only executes if the preceding `get` call fails.

The main pipeline will short-circuit with an [`AppError`](https://github.com/onur1/flixbox/blob/0.0.6/src/server/Error.ts) if any of the inner pipelines fails for some reason, and exit without writing a response.

Let's see the `GET` (essentially `method`) middleware which is the initial middleware used in the example above.

[`middleware/Method.ts`](https://github.com/onur1/flixbox/blob/0.0.6/src/server/middleware/Method.ts)

```typescript
import { right, left } from 'fp-ts/lib/Either'
import { StatusOpen } from 'hyper-ts'
import { decodeMethod, Middleware } from 'hyper-ts/lib/Middleware'
import { MethodError, AppError } from '../Error'

function method<T>(name: string): Middleware<StatusOpen, StatusOpen, AppError, T> {
  const lowercaseName = name.toLowerCase()
  const uppercaseName = name.toUpperCase()
  return decodeMethod(s =>
    s.toLowerCase() === lowercaseName
      ? right<AppError, T>(uppercaseName as T)
      : left(MethodError)
  )
}

export const GET = method<'GET'>('GET')
```

The `method` middleware compares the incoming request method with the provided method name in the lowercase form and outputs it in the uppercase form if they match, otherwise it throws a `MethodError` (which is a kind of `AppError`). This middleware can only be composed with other middlewares if the initial connection state `StatusOpen` has not changed yet, which means you can only compose this with other middlewares if you haven't written a header or response yet.

Like `method`, all middlewares in the main pipeline return an `AppError`:

* `get` returns a `NotFoundError` when an entry is not found.
* `put` returns a `ServerError` when an entry couldn't be saved.
* `movie` fails with `ProviderError` that encapsulates the TMDb API errors.

If I pipe the result of this middleware pipeline into another `orElse` call and compose it with an error handler middleware as the final thing, then I can handle the `AppError` it throws very conveniently, and eventually send the appropriate error message (with sensitive information redacted) or log important errors. The [`destroy`](https://github.com/onur1/flixbox/blob/0.0.6/src/server/middleware/Error.ts) middleware just does that.

## Logging

While we're at it&mdash; the logging functionality is based on the [logging-ts](https://github.com/gcanti/logging-ts/) module which is adapted from [purescripting-logging](https://github.com/rightfold/purescript-logging). This is a very light-weight logging solution for creating composable loggers. I [wired it up](https://github.com/onur1/flixbox/blob/0.0.6/src/logging/TaskEither.ts) with hyper-ts over a [`TaskEither`](https://gcanti.github.io/fp-ts/modules/TaskEither.ts.html) instance, but I don't see any reason why the Middleware itself couldn't be used to implement the [`Console`](https://github.com/onur1/flixbox/blob/0.0.6/src/logging/Console.ts).

## Runtime type system

If I had to choose only one thing from the fp-ts toolstack, that would be [io-ts](https://github.com/gcanti/io-ts/). Both the server and the client use this library extensively for type validation.

To name a few use cases,

- [The client application state](https://github.com/onur1/flixbox/blob/0.0.6/src/app/Model.ts) is defined with it.
- [TMDb data model](https://github.com/onur1/flixbox/tree/0.0.6/src/tmdb/model) is defined with it, too.
- It is used for [reporting validation errors](https://github.com/onur1/flixbox/blob/0.0.6/src/server/Error.ts#L17).
- Routers use it for [matching queries](https://github.com/onur1/flixbox/blob/0.0.6/src/app/Router.ts#L5).
- React components use it with [prop-types-ts](https://github.com/gcanti/prop-types-ts/) for [validating received props](https://github.com/onur1/flixbox/blob/0.0.6/src/app/components/Layout.tsx#L77).
- [Environment variables](https://github.com/onur1/flixbox/blob/0.0.6/src/server/index.ts#L72) are validated with it.

Everybody writes type validation libraries, but there must be a reason why the ones written by Giulio Canti (previously [tcomb](https://github.com/gcanti/tcomb) as well) became so popular and widely adopted in the JS community.

The reason is that other libraries are full of design mistakes which cause [type inference](https://en.wikipedia.org/wiki/Type_inference) to work poorly. You can't just _invent_ a technique for composing types, you can only _discover_ such things; and that discovery was made decades ago, io-ts is simply implementing that.

## Optics and immutable state updates

[monocle-ts](https://www.github.com/gcanti/monocle-ts) is a partial porting of [Monocle](https://www.optics.dev/Monocle/) from Scala. It is used in the client application for reading and transforming the application state.

This library provides support for [composable optics](https://medium.com/@gcanti/introduction-to-optics-lenses-and-prisms-3230e73bfcfe) that are used for reading and writing immutable data. Simply told, you can create such an optic structure (perhaps a [Lens](https://gcanti.github.io/monocle-ts/modules/Lens.ts.html) composition) to zoom into a deeply nested object for transforming or reading a value inside it without touching the original value.

There are other libraries such as [Immer.js](https://immerjs.github.io/immer/) for doing this type of stuff. It gives you this `produce` function that you can use to change a value inside some object and return a copy.

```javascript
import produce from "immer"

// curried producer:
const toggleTodo = produce((draft, id) => {
    const todo = draft.find(todo => todo.id === id)
    todo.done = !todo.done
})

const nextState = toggleTodo(baseState, "Immer")
```

Optics do a similar thing, but in a type-safe composable fashion. This is one of the ways how you would program the same functionality in monocle-ts using a [`Traversal`](https://gcanti.github.io/monocle-ts/modules/Traversal.ts.html):

```typescript
import * as _ from 'monocle-ts/lib/Traversal'

type T = { id: number; done: boolean }

type S = ReadonlyArray<T>

const getNextState = (id: number) =>
  pipe(
    _.id<S>(),
    _.findFirst(n => n.id === id),
    _.prop('done'),
    _.modify(done => !done)
  )

const nextState = getNextState(42)(baseState)
```

## Routing

On this page, the URL in the address bar is synced with the flixbox window. You can actually [visit the current page with an initial route](./flixbox.html#/movie/545611).

Both the client and the server use [fp-ts-routing](https://github.com/gcanti/fp-ts-routing) for parsing request routes. It is a cross-platform library and stacks with io-ts very nicely.

```typescript
import * as t from 'io-ts'
import { lit, query, int, zero } from 'fp-ts-routing'

// popular matches /popular.
const popular = lit('popular')

// movie matches /movie/ID.
const movie = lit('movie').then(int('id'))

// SearchQuery is an io-ts type for matching the query part of a URL.
const SearchQuery = t.interface({
  search_query: t.union([t.string, t.undefined]),
})

// results matches /results?search_query=WORD.
const results = lit('results').then(query(SearchQuery))
```

## Concurrency

If you have ever stumbled upon the programming language book shelf in a library, you may have noticed many of these books are structured in the same format.

In the first 9 or 10 chapters, they explain the fundamentals. It starts with some background and motivation, then it first teaches you data types, then operators, how to write expressions in this language, control structures like for loops, then you learn functions and it shows you some examples of how to implement a linked list or something. Between chapters 10 and 13 there is some nonsense, and finally there is Chapter 14: Concurrency.

This is actually the chapter that most people skip, also the most fun part of the book, since every language deals with concurrency in a different way. Some of them deal with it simply with mutexes, some use the actor model, atomic pointers, eventlets, greenlets, observable streams, goroutines... The list goes on.

The irony is that many of these languages that provide _first-class_ support for concurrency are not even widely used in reactive domains where concurrency needs to be tackled the most, such as graphical user interface development.

The one programming language that needs to have the most powerful concurrency support, namely  JavaScript, provides [promises](https://avaq.medium.com/broken-promises-2ae92780f33), [callbacks](https://www.geeksforgeeks.org/what-is-callback-hell-in-node-js/) and [async/await](https://www.youtube.com/watch?v=ITogH7lJTyE).

The weak concurrency support in JS is also the reason why we're seeing a new ground-breaking UI framework idea popping up every now and then. But if you think development with [MobX](https://mobx.js.org/) is magic, then you have to understand that callbacks are no different.

### Enter Elm

[Elm](https://elm-lang.org/) is a programming language designed specifically for programming GUIs, and [elm-ts](https://github.com/gcanti/elm-ts) is the fp-ts adaptation of the [Elm architecture](https://guide.elm-lang.org/architecture/) implemented using [RxJS](https://rxjs.dev/). It is worth noting that elm-ts works like Elm only on the surface, otherwise internally they are totally different. Also, the Elm language uses the Hindley Milner type system [which is quite different](https://dev.to/lucamug/typescript-and-elm-3g38) from TypeScript's own type system.

There is an entire literature about [Functional Reactive Programming](https://en.wikipedia.org/wiki/Functional_reactive_programming) (FRP) and [the Elm paper](https://elm-lang.org/assets/papers/concurrent-frp.pdf) by [Evan Czaplicki](https://github.com/evancz) is a good start if you want to dig in deeper. For those interested, I would also recommend taking a look at [purescript-behaviors](https://github.com/paf31/purescript-behaviors) by [Phil Freeman](https://functorial.com/) which implements [push-pull FRP](http://conal.net/papers/push-pull-frp/) in PureScript and has been ported to fp-ts too by Giulio Canti, under the name [graphics-ts](https://github.com/gcanti/graphics-ts).

If you have previously worked with Redux, [Elm is very similar](https://redux.js.org/understanding/history-and-design/prior-art). The terms, Message and the Update function in Elm are analogous to Action and Reducer in Redux.

Basically, you provide an initial state to it, a [pure function](https://en.wikipedia.org/wiki/Pure_function) for drawing visual elements (based on the current state), and finally another pure function which is responsible for transforming the application state when something happens.

The Flixbox UI defines the following `Msg` type. These are the only side-effects that can occur while you are browsing the app.

[`src/app/Msg.ts`](https://github.com/onur1/flixbox/tree/0.0.6/src/app/Msg.ts)

```typescript
type Msg =
  | Navigate
  | PushUrl
  | UpdateSearchTerm
  | SubmitSearch
  | SetHttpError
  | SetNotification
  | SetSearchResults
  | SetPopularResults
  | SetMovie
```

When you dispatch one of these messages (for example when a link is clicked and `Navigate` is triggered), the [update function](https://github.com/onur1/flixbox/blob/0.0.6/src/app/Effect.ts#L64) is called with a particular type of message and the current application state as input.

```typescript
declare function update<S, A>(msg: A, state: S): [S, A]
```

As you see, `update` takes a `msg` which has type `A` as its first parameter, and a `state` with type `S` as the second, returning both a new state and an action to run in the next loop. This pattern, as simple as it may seem, is actually a very powerful way to model state changes in UIs, to test and debug them.

## Conclusion

[PureScript and Haskell](https://gcanti.github.io/fp-ts/guides/purescript.html) are very elegant and concise programming languages. fp-ts is only emulating them and it has to deal with all the nitty gritty details to make this work with TypeScript types, while keeping the API up to date to not fall behind the developments within TypeScript, or the greater JavaScript ecosystem.

So, working with fp-ts may feel like working in a construction zone sometimes, with coils of cables lying around everywhere and the loud [V8](https://v8.dev/) engine sound in the background; but once you get the hang of it, those cables or the noise doesn't bother you too much, because everything works flawlessly and nobody has to wear helmets in this worksite .
