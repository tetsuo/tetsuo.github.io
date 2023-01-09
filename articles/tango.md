---
title: tango
tags: javascript,couch,language
published: 2023-01-02T16:20:00
updated: 2023-01-02T16:20:00
---

> [tango](https://github.com/onur1/tango) implements textual syntax for [Mango selector expressions](https://docs.couchdb.org/en/3.3.x/api/database/find.html) in the style of C.

Currently, it supports the following comparison operators, and parentheses for explicit operator precedence.

|Operator|Relationship tested|
|:-:|:-|
|<|First operand less than second operand|
|>|First operand greater than second operand|
|<=|First operand less than or equal to second operand|
|>=|First operand greater than or equal to second operand|
|==|First operand equal to second operand|
|!=|First operand not equal to second operand|

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

[In my previous post](https://ogu.nz/couchilla.html), I mentioned about [couchilla](https://github.com/onur1/couchilla) which you can use to bundle design documents for creating MapReduce views on your database. The `/db/_find` API is another way of doing this and results in faster queries in most cases.

You can give it a try if you have Docker and NodeJS installed.

Type the following Docker command to start a CouchDB instance and bind port `5984`, the default CouchDB port to your host machine:

```shell
docker run \
  -p 5984:5984 \
  -it --rm \
  -e COUCHDB_USER=admin -e COUCHDB_PASSWORD=pass \
  couchdb:3
```

The default username and password will be `admin`/`pass`.

Create the `_users` database to stop CouchDB from spamming the console with warning messages:

```shell
curl -X PUT "http://admin:pass@localhost:5984/_users"
```

Create `example` database:

```shell
curl -X PUT "http://admin:pass@localhost:5984/example"
```

Create some documents, like movies:

```shell
curl \
  -X POST \
  -H "Content-Type: application/json" \
  "http://admin:pass@localhost:5984/example" \
  -d '{"director": "Roy Andersson", "year": 2007, "name": "Du Levande" }'
```

Add another movie:

```shell
curl \
  -X POST \
  -H "Content-Type: application/json" \
  "http://admin:pass@localhost:5984/example" \
  -d '{"director": "Ruben Ostlund", "year": 2014, "name": "Force Majeure" }'
```

In order to select movies shot by Roy Andersson earlier than 2007, it looks something like this:

```shell
npx @onur1/tango 'director == "Roy Andersson" && year <= 2007'
```

Here's a one-liner with `jq` and `npx` that shows what goes where.

To inspect the Mango output, first type `npx @onur1/tango 'director == "Roy Andersson" && year <= 2007'`, this should output the following Mango expression:

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
        "$lte": 2007
      }
    }
  ]
}
```

Send this to the `/_find` endpoint with a little help from the `jq` tool.

```shell
jq \
  -n -c \
  '{ "selector": $SEL }' --argjson SEL \
  "`npx @onur1/tango 'director == "Roy Andersson" && year <= 2007'`" \
  | curl \
      -s \
      -X POST \
      --data-binary @- \
      -H "Content-Type: application/json" \
      "http://admin:pass@localhost:5984/example/_find"
```

Output:

```json
{
  "docs": [
    {
      "_id": "ad6ec12",
      "_rev": "1-b56b91",
      "director": "Roy Andersson",
      "year": 2007,
      "name": "Du Levande"
    }
  ]
}
```
