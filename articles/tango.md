---
title: Querying CouchDB with human-readable syntax
cover_title: Querying CouchDB with human-readable syntax
description: Tango provides a textual syntax for logical and relational expressions, parsing them directly into Mango selectors
tags: javascript,couchdb,tool
published: 2023-01-02T16:20:00
updated: 2025-05-30T13:37:00
---

> [**tango**](https://github.com/tetsuo/tango) provides a C-like syntax for logical and relational expressions, parsing them directly into [Mango selectors](https://docs.couchdb.org/en/stable/api/database/find.html).

In my [previous post](/couchdb-design-document-bundler.html), I introduced [couchilla](https://github.com/tetsuo/couchilla), a command-line tool for bundling CouchDB design documents. While MapReduce views are powerful, the [`/{db}/_find`](https://docs.couchdb.org/en/stable/api/database/find.html) API typically provides faster querying in most cases by using Mango selector expressions.

For instance, in Mango, you'd express a query for "movies directed by Roy Andersson after 2007" with this JSON structure:

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

... which is, as you can see, a hand-written AST. With tango, you could write this instead:

```c
director == "Roy Andersson" && year > 2007
```

This syntax includes standard C operators and supports parentheses to specify explicit precedence. At present, tango does not support unary operators or the `$in` operator for matching elements within arrays.

> 📄 **See the lexer implementation in [`scan.js`](https://github.com/tetsuo/tango/blob/master/scan.js).**

### To parse Tango is to turn it into Mango

The [shunting yard algorithm](https://en.wikipedia.org/wiki/Shunting_yard_algorithm) is a linear-time method for parsing expressions using [operator precedence parsing](https://en.wikipedia.org/wiki/Operator-precedence_parser). It employs a stack to manage operators and a queue to construct an abstract syntax tree—which, in this context, becomes a Mango expression.

> 📄 **See the parser implementation in [`parse.js`](https://github.com/tetsuo/tango/blob/master/parse.js#L40).**
