---
title: Query CouchDB with C-like expressions
cover_title: Tango Textual syntax for Mango
description: Query CouchDB with C-like expressions
tags: javascript,couchdb,language
published: 2023-01-02T16:20:00
updated: 2024-08-10T00:00:00
---

> [**tango**](https://github.com/onur1/tango) provides a textual syntax for logical and relational expressions compatible with [Mango selectors](https://docs.couchdb.org/en/stable/api/database/find.html).

As mentioned [in my previous post](./couchilla.md), [couchilla](https://github.com/onur1/couchilla) bundles design documents for creating CouchDB design documents. While MapReduce views are awesome, in most cases, `/db/_find` API offers faster querying using [Mango selector expressions](https://docs.couchdb.org/en/stable/api/database/find.html)  in JSON format. tango introduces a textual syntax for that.

In Mango, the query to find movies directed by Roy Andersson after 2007 is expressed in a tree-like structure resembling a syntax tree.

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

tango introduces this alternative:

```c
director == "Roy Andersson" && year > 2007
```

## Parser algorithm

Parsing a language begins with [lexical analysis](https://en.wikipedia.org/wiki/Lexical_analysis), breaking text into tokens and grouping them into grammatical phrases. A lexer, essentially a state machine, identifies keywords, symbols, and literals character by character.

However, a stream of tokens doesn't give a lot of information to process. A more common internal representation for syntactic structures is AST&mdash; [abstract syntax tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree).

The [Shunting yard algorithm](https://en.wikipedia.org/wiki/Shunting_yard_algorithm), devised [Edsger W. Dijkstra](https://en.wikipedia.org/wiki/Edsger_W._Dijkstra) is a linear time algorithm for parsing expressions using a method known as [operator precedence parsing](https://en.wikipedia.org/wiki/Operator-precedence_parser). It employs a stack for operator management and a queue for outputting Reverse Polish Notation or constructing an AST.

Currently, tango supports standard C comparison operators and parentheses for explicit precedence.

#### Example

```c
(x > y || z == 10) && name == "example"
```

The resulting AST adheres to CouchDB's declarative JSON query language.

```json
{
  "$and": [
    {
      "$or": [
        {
          "x": {
            "$gt": "y"
          }
        },
        {
          "z": {
            "$eq": 10
          }
        }
      ]
    },
    {
      "name": {
        "$eq": "example"
      }
    }
  ]
}
```

Unary operators and the `$in` operator for matching array elements are not yet supported by tango.
