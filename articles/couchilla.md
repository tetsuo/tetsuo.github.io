---
title: CommonJS Support for CouchDB Design Documents
cover_title: couchilla
description: CommonJS Support for CouchDB Design Documents
tags: javascript,couchdb,database
published: 2023-01-02T14:55:00
updated: 2024-11-30T00:00:00
---

> [**couchilla**](https://github.com/tetsuo/couchilla) is a bundler for packing design documents for CouchDB.

In [CouchDB](https://couchdb.apache.org/), [design documents](https://docs.couchdb.org/en/stable/ddocs/ddocs.html) are special database entries that contain JavaScript functions, such as _views_ and _updates_. These functions, executed on demand, generate secondary indexes, often termed MapReduce views.

Although CouchDB supports JavaScript and Erlang, design functions themselves are language-independent, which is why CouchDB doesn't include a dedicated tool for creating design documents.

JavaScript support in CouchDB relies on the Mozilla SpiderMonkey engine, which imposes specific module dependency rules and limitations on design function development.

[couchilla](https://github.com/tetsuo/couchilla) addresses this by providing a convenient way to bundle design documents with CommonJS support. It aggregates view and filter functions from a JavaScript directory and produces a design document in JSON format.

## Directory structure

Here's an example of a basic design document directory structure:

```
.
├── filters
│   └── quu.js
├── views
│   ├── foo.map.js
│   └── bar.reduce.js
└── validate_doc_update.js
```

* [View functions](https://docs.couchdb.org/en/stable/ddocs/ddocs.html#view-functions) reside in the `views` directory. Files with `.map.js` (or simply `.js`) are converted into [map functions](https://docs.couchdb.org/en/stable/ddocs/ddocs.html#map-functions).
  * [Reduce functions](https://docs.couchdb.org/en/stable/ddocs/ddocs.html#reduce-and-rereduce-functions) are defined in files with `.reduce.js` extensions.
* [Filter functions](https://docs.couchdb.org/en/stable/ddocs/ddocs.html#filter-functions) belong in the `filters` directory.

## Examples

### Map functions

Emit key/value pairs to store them in a view.

`views/foo.map.js`

```js
export default doc => emit(doc._id, 42)
```

### Reduce functions

Take sum of mapped values:

`views/foo.reduce.js`

```js
export default (keys, values, rereduce) => {
  if (rereduce) {
    return sum(values)
  } else {
    return values.length
  }
}
```

### Filter functions

Filter by field:

`filters/foo.js`

```js
export default (doc, req) => {
  if (doc && doc.title && doc.title.startsWith('C')) {
    return true
  }
  return false
}
```

### Validate document update functions

Log incoming requests and respond with forbidden:

```js
export default (newDoc, oldDoc, userCtx, secObj) => {
  log(newDoc)
  log(oldDoc)
  log(userCtx)
  log(secObj)
  throw { forbidden: 'not able now!' }
}
```

### Builtin reduce functions

You can opt to use [Erlang native functions](https://docs.couchdb.org/en/stable/ddocs/ddocs.html#built-in-reduce-functions) using the `builtin` annotation. For example the `sum` function above can be rewritten using `_sum`.

`views/foo.reduce.js`

```js
/* builtin _sum */
```

During compilation this will be replaced with a call to the builtin [`_sum`](https://docs.couchdb.org/en/stable/ddocs/ddocs.html#sum) function.

### Requiring other modules

All code, including `require()` statements, must be enclosed within the exported default function.

`views/gamma.map.js`

```js
export default doc => {
  const gamma = require('gamma')

  emit(doc._id, gamma(doc.value))
}
```
