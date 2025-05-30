---
title: Building a full-stack web app with fp-ts
description: Full-stack client/server web app interacting with the TheMovieDB API
cover_title: Building a full-stack web app with fp-ts
tags: typescript,starter
published: 2023-01-25T12:41:00
updated: 2025-05-30T13:37:00
---

[![flixbox - Search movie trailers](./flixbox.jpg)](https://tetsuo.github.io/wr/flixbox.html)

> This post outlines the architecture and key components of [**flixbox**](https://www.github.com/tetsuo/flixbox), a full-stack web app built in TypeScript with [fp-ts](https://gcanti.github.io/fp-ts/) and its [ecosystem](https://gcanti.github.io/fp-ts/ecosystem/) of libraries.

# Server

The server is powered by [**hyper-ts**](https://github.com/DenisFrezzato/hyper-ts), a functional HTTP framework inspired by [Hyper](https://hyper.wickstrom.tech/).

Internally, a set of middlewares are defined like `get`, `put`, `movie`, and `results` for interacting with the [TMDb](https://www.themoviedb.org/) API and managing caching. Storage uses [xache](https://github.com/mafintosh/xache), a simple caching library by mafintosh.

## Middleware architecture

API endpoints are structured as middleware pipelines that can short-circuit on failure. Each middleware performs a specific task and is responsible for handling failures within that scope, including validation of user input, provider errors when TMDb returns bad data, not found for missing resources, and so on.

### Example: Movie middleware

The following middleware handles `/movie/ID` requests.

When `/movie/3423` is called:

* 🗂️ Check the internal cache:
  * ✅ Return cached data if available.
  * 🔄 Otherwise, fetch data from TMDb, store it in the cache, and return the result.
* 📦 Respond with a JSON object.

```typescript
import * as H from 'hyper-ts/lib/Middleware'

// ...

function getMovieMiddleware(
  tmdb: TMDb,
  store: Storage<Document>
): (route: MovieRoute) => H.Middleware<StatusOpen, ResponseEnded, AppError, void> {
  return route =>
    pipe(
      GET,
      H.apSecond(
        pipe(
          get(store, `/movies/${route.id}`),
          H.map(entry => entry.value),
          H.orElse(() =>
            pipe(
              movie(tmdb, route.id),
              H.chain(value =>
                pipe(
                  put(store, `/movies/${route.id}`, value),
                  H.map(entry => entry.value)
                )
              )
            )
          )
        )
      ),
      H.ichain(res =>
        pipe(
          H.status<AppError>(200),
          H.ichain(() => sendJSON(res))
        )
      )
    )
}
```

> 📄 **See the full implementation in [`server/Flixbox.ts`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/Flixbox.ts).**

# Cross-stack shared modules

On both client and server, flixbox utilizes a set of common modules including:

- [**logging-ts**](https://github.com/gcanti/logging-ts/) for structured logging
- [**io-ts**](https://github.com/gcanti/io-ts) for runtime type validation
- [**monocle-ts**](https://github.com/gcanti/monocle-ts) for optics support
- [**fp-ts-routing**](https://github.com/gcanti/fp-ts-routing) for declarative route parsing

Among these, [**io-ts**](https://github.com/gcanti/io-ts/) is especially valuable for robust type validation throughout the application, with applications such as:

* [Defining client-side application state](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/Model.ts)
* [Modeling TMDb API data](https://github.com/tetsuo/flixbox/tree/0.0.7/src/tmdb/model)
* [Reporting validation errors](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/Error.ts#L17)
* [Matching URL queries](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/Router.ts#L5)
* [Validating React component props](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/components/Layout.tsx#L77)
* [Ensuring correctness of environment variables](https://github.com/tetsuo/flixbox/blob/0.0.7/src/server/index.ts#L72)

>> **[io-ts](https://github.com/gcanti/io-ts) is highly recommended even for projects that do not fully adopt fp-ts.**

#### Extending fp-ts modules to new effect types

While these modules integrate smoothly within the fp-ts v2 ecosystem, certain scenarios may require explicit type-level configuration.

For instance, when using `logging-ts` with a custom effect type, you must provide an instance of the `Logger` algebra that conforms to that effect. `logging-ts` facilitates this by exposing `getLoggerM`, which abstracts over any monad.

To integrate `logging-ts` with the effects flixbox generates, a new HKT [`LoggerTaskEither`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/logging/TaskEither.ts) is defined and registered in `fp-ts`'s `URItoKind2`, thereby allowing type class instance support for logging within the `TaskEither` context, the most frequently used effect type in the project.

# Client

The client uses [**elm-ts**](https://github.com/gcanti/elm-ts), which provides an fp-ts adaptation of [Elm](https://elm-lang.org/).

Elm shares conceptual similarities with [Redux](https://redux.js.org/understanding/history-and-design/prior-art). Messages in Elm correspond to Redux actions, and the Elm `update` function closely mirrors Redux reducers, responsible for state changes.

Here are the message types used in the flixbox UI:

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

### How it works:

* 📄 **Initial state**: You define an initial application state, the model.
* 🖼️ **View function**: A view function renders visual elements based on the current state.
* 🔁 **Update function**: When user interaction triggers a message (e.g., clicking a link triggers a Navigate message), the update function is called.
  * 📥 It receives the message and the current state as its inputs.
  * ⚙️ It processes the current state and returns a new state and potentially a new message.
* 🔄 **State updates**: The new state is sent to subscribers (like the view function).
* 🌀 **Continuous processing**: New actions are processed until no further actions remain.

> 📄 **See the full implementation in [`app/Effect.ts`](https://github.com/tetsuo/flixbox/blob/0.0.7/src/app/Effect.ts).**

### Optics for immutable state management

The client also uses [**monocle-ts**](https://www.github.com/gcanti/monocle-ts), a port of [Monocle](https://www.optics.dev/Monocle/), allowing composable structures like [`Lens`](https://gcanti.github.io/monocle-ts/modules/Lens.ts.html) and [`Traversal`](https://gcanti.github.io/monocle-ts/modules/Traversal.ts.html) for state updates without mutations.

Consider the following comparison to [Immer.js](https://immerjs.github.io/immer/):

**Immer.js example**:

```javascript
import produce from "immer"

const toggleTodo = produce((draft, id) => {
    const todo = draft.find(todo => todo.id === id)
    todo.done = !todo.done
})

const nextState = toggleTodo(baseState, "Immer")
```

**monocle-ts equivalent**:

```typescript
import * as _ from 'monocle-ts/lib/Traversal'

type Todo = { id: number; done: boolean }

type Todos = ReadonlyArray<Todo>

const toggleTodoDone = (id: number) =>
  pipe(
    _.id<Todos>(),
    _.findFirst(todo => todo.id === id),
    _.prop('done'),
    _.modify(done => !done)
  )

const nextState = toggleTodoDone(42)(baseState)
```
