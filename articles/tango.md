---
title: Parsing logical expressions with the Shunting yard algorithm
cover_title: tango
description: Parsing logical expressions with the Shunting yard algorithm
tags: javascript,couchdb,language
published: 2023-01-02T16:20:00
updated: 2023-01-02T16:20:00
---

> [**tango**](https://github.com/onur1/tango) implements textual syntax for logical/relational expressions compatible with [Mango selectors](https://docs.couchdb.org/en/stable/api/database/find.html).

[In my previous post](./couchilla.md), I mentioned about [couchilla](https://github.com/onur1/couchilla) which you can use to bundle design documents for creating map/reduce views on CouchDB.

The `/db/_find` API is another way of querying a database and results in faster responses in most cases. You interface with it using [Mango selector expressions](https://docs.couchdb.org/en/stable/api/database/find.html) in JSON syntax.

For example, the following query retrieves movies directed by Roy Andersson which are released after 2007.

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

This looks very much like a _syntax tree_, isn't it? It is a tree-like object that contains syntactic structure of a simple logical expression, such as the following C expression written in infix form.

```c
director == "Roy Andersson" && year > 2007
```

Actually, this could be a nice addition to my HTML template language as an embedded sub-language for selecting items within section blocks. I already use CouchDB in my frontend server stack, it's not a bad idea to bake the logic for building query expressions into the template language itself.

## Parser algorithm

A language parser starts with [lexical analysis](https://en.wikipedia.org/wiki/Lexical_analysis) which is tokenizing a stream of text and grouping tokens into grammatical phrases. There is really nothing special with a lexer, you simply implement a state machine which identifies keywords, symbols and literals character by character. At worst you will need to deal with [look-ahead](https://en.wikipedia.org/wiki/Look-ahead_(backtracking)). For example, an arithmetic expression such as `1 + 2` should yield a number literal, followed by an operator token and another number literal.

However, a stream of tokens doesn't give a lot of information to process. A more common internal representation for syntactic structures is AST&mdash;[abstract syntax tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree).

The [Shunting yard algorithm](https://en.wikipedia.org/wiki/Shunting_yard_algorithm) I used in tango is invented by [Edsger W. Dijkstra](https://en.wikipedia.org/wiki/Edsger_W._Dijkstra); it's a linear time algorithm which implements a parsing method known as [operator precedence parsing](https://en.wikipedia.org/wiki/Operator-precedence_parser).

Simply told: the algorithm works by employing a stack and a queue, the stack is for maintaining operator tokens based on their order of operations precedence, and the queue is for outputting the same expression in RPN (Reverse Polish Notation) or to produce an AST instead.

Currently, tango supports the standard C comparison operators only, and parentheses for explicit operator precedence.

#### Example

```c
(x > y || z == 10) && name == "example"
```

Parsing this expression outputs an AST which conforms to the declarative JSON querying language found in CouchDB.

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

There are other features of Mango which are not supported in here such as the `$in` operator for matching array elements. Also note that, tango doesn't support unary operators.
