---
title: Building a full-stack web app with fp-ts
description: Full-stack client/server web app interacting with the TheMovieDB API
cover_title: Building a full-stack web app with fp-ts
tags: typescript,fp
published: 2023-01-25T12:41:00
updated: 2025-03-30T13:37:00
---

[![flixbox - Search movie trailers](./flixbox.jpg)](https://ogu.nz/wr/flixbox.html)

> [**flixbox**](https://www.github.com/tetsuo/flixbox) showcases a full-stack client/server web application interacting with the [TheMovieDB](https://www.themoviedb.org/) API. It leverages the functional programming library [fp-ts](https://gcanti.github.io/fp-ts/) and its [module ecosystem](https://gcanti.github.io/fp-ts/ecosystem/).

[fp-ts](https://gcanti.github.io/fp-ts/) brings [typeclasses](https://en.wikipedia.org/wiki/Type_class) and [higher kinded types](https://en.wikipedia.org/wiki/Kind_(type_theory)), concepts from functional programming languages like [Haskell](https://www.haskell.org/) and [PureScript](https://www.purescript.org/), to [TypeScript](https://www.typescriptlang.org/). The entire flixbox application, including the server-side API, is built using libraries from the [fp-ts module ecosystem](https://gcanti.github.io/fp-ts/ecosystem/).

## Overview of the HTTP API

#### Requests and data formats

All flixbox API requests are HTTP GET requests, and responses are exclusively in JSON format. No authentication is required.

#### Errors

flixbox responds with appropriate HTTP status codes and errors for issues:

- Validation error: Invalid user input.
- Provider error: TMDb returned invalid data.
- Not found: Requested resource unavailable.
- Server error: Generic server-side failure.
- Method error: Incorrect HTTP method.

## Searching movies

```
GET /results?search_query=QUERY
```

Responds with a [`SearchResultSet`](https://github.com/tetsuo/flixbox/tree/0.0.7/src/tmdb/model/SearchResultSet.ts) object.

## Retrieving a movie

```
GET /movie/ID
```

Responds with a [`Movie`](https://github.com/tetsuo/flixbox/tree/0.0.7/src/tmdb/model/Movie.ts) object.

## Get popular movies

```
GET /popular
```

Responds with a [`SearchResultSet`](https://github.com/tetsuo/flixbox/tree/0.0.7/src/tmdb/model/SearchResultSet.ts) object.

# HTTP middleware architecture

> The [server](https://github.com/tetsuo/flixbox/tree/0.0.7/src/server) API uses [hyper-ts](https://github.com/DenisFrezzato/hyper-ts), an fp-ts port of [Hyper](https://hyper.wickstrom.tech/), enforcing strict middleware composition through static type checking. It runs on Express but can integrate with other HTTP servers.

Hyper is modeled as a State monad, reading incoming requests and writing responses through Express. Instead of directly mutating the connection, it produces a list of actions to execute in order.

The example below showcases the pipeline for handling `/movie/ID` requests, caching results from TMDb.

When [`/movie/3423`](https://onurgunduz.com/flixbox/movie/3423) is called:

* Checks the internal cache.
  * If cached, returns the cached value.
  * Otherwise fetches data from TMDb caches it, and returns the result.
* Responds with a JSON object.

[`server/Flixbox.ts`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/Flixbox.ts#L87)

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

The `apSecond` function executes only if the preceding `GET` middleware succeeds, while `orElse` handles failures. The main pipeline short-circuits on [`AppError`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/Error.ts).

### The `GET` middleware

[`middleware/Method.ts`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/middleware/Method.ts)

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

The method middleware compares the request method to the provided one, returning it in uppercase if matched, otherwise throwing a `MethodError` (an `AppError` subtype). It can only be composed before writing headers or responses.

All core middlewares return `AppError`:

* `get`: Returns `NotFoundError` if an entry is not found.
* `put`: Returns `ServerError` on save faillures.
* `movie`: Handles TMDb API errors as `ProviderError`.

An `orElse` handler can be added to manage `AppError`, sending appropriate error messages or logging issues. The [`destroy`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/middleware/Error.ts) middleware handles this.

# Logging

flixbox utilizes the lightweight and composable logging module, [logging-ts](https://github.com/gcanti/logging-ts/). This library, adapted from [purescripting-logging](https://github.com/rightfold/purescript-logging), integrates seamlessly with hyper-ts using the [TaskEither](https://github.com/tetsuo/flixbox/blob/0.0.7/src/logging/TaskEither.ts) type.

# Runtime type system

[io-ts](https://github.com/gcanti/io-ts/) is crucial for type validation throughout the application:

- [Defining client application state](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/Model.ts)
- [Modeling TMDb data](https://github.com/tetsuo/flixbox/tree/0.0.7/src/tmdb/model)
- [Reporting validation errors](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/Error.ts#L17)
- [Matching queries](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/Router.ts#L5)
- [Validating React props](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/components/Layout.tsx#L77)
- [Validating environment variables](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/index.ts#L72)

There are many type validation libraries available in the JavaScript community. However, the libraries developed by Giulio Canti, including io-ts and its predecessor [tcomb](https://github.com/gcanti/tcomb), have gained significant popularity and adoption.

Many other libraries suffer from design flaws that hinder [type inference](https://en.wikipedia.org/wiki/Type_inference). Type composition techniques aren't inventions, but rather discoveries made decades ago. io-ts excels by effectively implementing these established principles.

# Optics &mdash;i.e. immutable state updates

> [monocle-ts](https://www.github.com/gcanti/monocle-ts) is a  porting of [Monocle](https://www.optics.dev/Monocle/) from Scala, offering type-safe and [composable](https://medium.com/@gcanti/introduction-to-optics-lenses-and-prisms-3230e73bfcfe) state manipulation.

In simpler terms, optics allow you to create structures (like [Lens](https://gcanti.github.io/monocle-ts/modules/Lens.ts.html) compositions) that focus on specific parts of your data. You can then transform or read values within that targeted area without modifying the original data.

[Immer.js](https://immerjs.github.io/immer/) offers a similar functionality, relying on a `produce` function that creates a copy of the object before making changes.

```javascript
import produce from "immer"

// curried producer:
const toggleTodo = produce((draft, id) => {
    const todo = draft.find(todo => todo.id === id)
    todo.done = !todo.done
})

const nextState = toggleTodo(baseState, "Immer")
```

You can achieve the same result using [`Traversal`](https://gcanti.github.io/monocle-ts/modules/Traversal.ts.html):

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

# Routing

> This application synchronizes the URL in the address bar with the content displayed in the flixbox window. You can directly access a specific page by providing an initial route in the URL. ([Example](./flixbox.html#/movie/545611))

Both client and server use [fp-ts-routing](https://github.com/gcanti/fp-ts-routing) for parsing request routes, integrating well with io-ts.

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

# Elm in TypeScript

flixbox UI builds on concepts from [Elm](https://elm-lang.org/), a language specifically designed for building graphical user interfaces (GUIs). [elm-ts](https://github.com/gcanti/elm-ts), which leverages [RxJS](https://rxjs.dev/), provides a TypeScript adaptation using fp-ts.

While elm-ts bears a surface-level resemblance to Elm, they function quite differently under the hood. Additionally, Elm employs the Hindley-Milner type system, which [differs significantly](https://dev.to/lucamug/typescript-and-elm-3g38) from TypeScript's type system.

In flixbox, application state is managed through messages and an update function—similar to Redux but with a more functional approach. This cyclical pattern significantly simplifies state management, making testing and debugging (including time-travel debugging) much more straightforward.

For those interested in exploring FRP further, here are some resources:

* [Functional Reactive Programming](https://en.wikipedia.org/wiki/Functional_reactive_programming)
* [Elm paper](https://elm-lang.org/assets/papers/concurrent-frp.pdf) by [Evan Czaplicki](https://github.com/evancz)
* [Push-pull FRP](http://conal.net/papers/push-pull-frp/) in PureScript using [purescript-behaviors](https://github.com/paf31/purescript-behaviors)

Elm's design shares similarities with [Redux](https://redux.js.org/understanding/history-and-design/prior-art). Messages in Elm are comparable to actions in Redux, and Elm's update function aligns with Redux's reducer function, both facilitating predictable state changes in applications.

[`src/app/Msg.ts`](https://github.com/tetsuo/flixbox/tree/0.0.7/src/app/Msg.ts)

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

#### The flixbox update cycle

* **Initial State**: You define an initial application state.
* **View Function**: A pure view function renders visual elements based on the current state.
* **Update Function**: When user interaction triggers a message (e.g., clicking a link triggers a `Navigate` message), the [update function](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/Effect.ts#L64) is called.
  * It receives the message and the current state as inputs.
  * It transforms the state and potentially returns a new message.
* **State Updates**: The new state is sent to [subscribers](https://package.elm-lang.org/packages/elm/core/latest/Platform-Sub) like the `view` function.
* **Continuous Processing**: New actions are processed until no further actions remain.
