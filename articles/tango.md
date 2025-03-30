---
title: Querying CouchDB with human-readable syntax
cover_title: Querying CouchDB with human-readable syntax
description: Tango provides a textual syntax for logical and relational expressions compatible with Mango selectors
tags: javascript,couchdb,lang,database
published: 2023-01-02T16:20:00
updated: 2025-03-30T13:37:00
---

> [**tango**](https://github.com/tetsuo/tango) provides a textual syntax for logical and relational expressions compatible with [Mango selectors](https://docs.couchdb.org/en/stable/api/database/find.html).

In my [previous post](./couchilla.md), I introduced [couchilla](https://github.com/tetsuo/couchilla), a lightweight command-line tool for bundling CouchDB design documents. While MapReduce views are powerful, the [`/db/_find`](https://docs.couchdb.org/en/stable/api/database/find.html) API typically provides faster querying in most cases by using Mango selector expressions in JSON format. tango introduces a textual syntax for these queries.

For example, in Mango, a query to find movies directed by Roy Andersson after 2007 is expressed in a JSON structure resembling a syntax tree:

```json
{
  "$and": [
    {
      "director": {
        "$eq": "Roy Andersson"
      }
    },
    {
      "year": {
        "$gt": 2007
      }
    }
  ]
}
```

With tango, this can instead be written as:

```c
director == "Roy Andersson" && year > 2007
```

This syntax includes standard C comparison operators and supports parentheses to specify explicit precedence. At present, tango does not support unary operators or the `$in` operator for matching elements within arrays.

The [Shunting Yard algorithm](https://en.wikipedia.org/wiki/Shunting_yard_algorithm), as [implemented here](https://github.com/tetsuo/tango/blob/master/parse.js) and devised by [Edsger W. Dijkstra](https://en.wikipedia.org/wiki/Edsger_W._Dijkstra), is a linear-time algorithm for parsing expressions using a technique known as [operator precedence parsing](https://en.wikipedia.org/wiki/Operator-precedence_parser). It uses a stack to manage operators and a queue to output expressions in Reverse Polish Notation or to construct an Abstract Syntax Tree (AST).
