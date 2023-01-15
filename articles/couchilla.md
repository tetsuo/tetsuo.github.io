---
title: couchilla
description: Bundler for packing CouchDB design documents
tags: javascript,couchdb,database
published: 2023-01-02T14:55:00
updated: 2023-01-02T14:55:00
---

> [couchilla](https://github.com/onur1/couchilla) is a bundler for packing design documents for CouchDB.

[Design documents](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html) are a special type of database entry that you can insert to [CouchDB](https://couchdb.apache.org/), they contain functions such as view and update functions. These functions are executed when requested and create secondary indexes, i.e. MapReduce views.

CouchDB ships with JavaScript and Erlang support, but design functions are language-agnostic. So understandably, the distribution doesn't include a secondary tool to create a design document.

The JavaScript support is based on the [Mozilla Spidermonkey](https://firefox-source-docs.mozilla.org/js/index.html) engine and it has somewhat strict module dependency rules and other limitations that you need to be aware of while writing your design functions.

A couple of years ago, while working at [wearereasonablepeople](https://wearereasonablepeople.nl), I wrote the [couchify](https://github.com/wearereasonablepeople/couchify) tool for bundling design documents with CommonJS support. It takes map/reduce/filter/etc. functions from a directory of JavaScript files and outputs a design document JSON. couchilla is a rewrite of that module.

## Directory structure

An example directory structure looks like this:

```
.
├── filters
│   └── quu.js
├── views
│   ├── foo.map.js
│   └── bar.reduce.js
└── validate_doc_update.js
```

* Files that contain [view functions](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html#view-functions) are located in the `views` folder.
  * Files with `.map.js` (or only `.js`) extensions are transformed into [map functions](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html#map-functions).
  * Files with `.reduce.js` extensions are transformed into [reduce functions](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html#reduce-and-rereduce-functions).
* Files that contain [filter functions](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html#filter-functions) are located in the `filters` folder.

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

You can opt to use [Erlang native functions](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html#built-in-reduce-functions) using the `builtin` annotation. For example the `sum` function above can be rewritten using `_sum`.

`views/foo.reduce.js`

```js
/* builtin _sum */
```

During compilation this will be replaced with a call to the builtin [`_sum`](https://docs.couchdb.org/en/3.3.x/ddocs/ddocs.html#sum) function of CouchDB.

### CommonJS

All code should be inside the exported default function, including your `require()` calls.

`views/gamma.map.js`

```js
export default doc => {
  const gamma = require('gamma')

  emit(doc._id, gamma(doc.value))
}
```
