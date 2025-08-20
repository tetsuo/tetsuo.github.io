---
title: Retro JSX syntax
cover_title: Retro JSX syntax
description: Retro JSX syntax
tags: go
published: 2025-06-05T00:00:00
updated: 2025-08-19T13:37:00
---

> restache extends plain HTML with curly braces and compiles to modern JSX, letting you write React components like it's 2013.

## Example: Dashboard

The [`tetsuo/dashboard`](https://github.com/tetsuo/dashboard) repository provides an example setup with [ESBuild](https://esbuild.github.io/) and a set of basic UI components demonstrating the current capabilities 👉 **[view it online](https://tetsuo.github.io/dashboard/)**.

---

## Try it yourself

> playground: title=Here's an example; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.3-dev.wasm

```
<ul>
  {#fruits}
    <li>{name}</li>
  {/fruits}
</ul>
```

## restache v0 draft

restache extends HTML5 with Mustache-like syntax to support variables, conditionals, and loops.

### Variables

**Variables** provide access to data in the current scope using dot notation.

> playground: title=Accessing component props; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.3-dev.wasm

```
<article class="fruit-card" data-fruit-id={id}>
  <h3>{name}, eaten at {ateAt}</h3>
  <p>{color} on the outside, {flavor.profile} on the inside</p>
  <img src={image.src} alt={image.altText} />
</article>
```

They can only appear within text nodes or as full attribute values inside a tag.

```
✅ can insert variable {here}, or <img href={here}>.
```

---

### When

> playground: title=Renders block when expression is truthy; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True

```
{?loggedIn}
  <welcome-banner user={user} />
{/loggedIn}
```

---

### Unless

> playground: title=Renders block when expression is falsy; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True

```
{^hasPermission}
  <p>You do not have access to this section.</p>
{/hasPermission}
```

---

### Range

> playground: title=Iterates over a list value; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True

```
<ul>
  {#fruits}
    <li>
      {name}
      <ul>
        {#vitamins}
          <li>{name}</li>
        {/vitamins}
      </ul>
    </li>
  {/fruits}
</ul>
```

**Range blocks** create a new lexical scope. Inside the block, `{name}` refers to the local object in context; outer scope variables are not accessible.

---

⚠️ Control structures must wrap [well-formed elements](https://en.wikipedia.org/wiki/Well-formed_element) (or other well-formed control constructs), and cannot appear inside tags.

---

### Comments

> playground: title=There are two types of comments; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True

```
<!-- Comment example -->

<span>{! TODO: fix bugs } hi</span>
```

Standard HTML comments are removed from the generated output.

restache comments compile into JSX comments.

---

## Generating JSX

restache transpiler generates a React JSX component from each input and handles JSX-specific quirks where necessary.

### Fragment wrapping

> playground: title=Multiple root elements are wrapped in a Fragment; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.2.0.wasm

```
<h1>{title}</h1>
<p>{description}</p>
```

- This also applies within control blocks.
- If you only have one root element, then a Fragment is omitted.

### Case conversion

React requires component names to start with a capital letter and prop names to use camelCase. In contrast, HTML tags and attribute names are not case-sensitive.

To ensure compatibility, restache applies the following transformations:

- Elements written in kebab-case (e.g. `<my-button>`) are automatically converted to PascalCase (`MyButton`) in the output.
- Similarly, kebab-case attributes (like `disable-padding`) are converted to camelCase (`disablePadding`).

> playground: title=kebab-case 🔜 React case; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.3-dev.wasm

```
<search-bar
  hint-text="Type to search..."
  data-max-items="10"
  aria-label="Site search"
/>
```

ℹ️ _Attributes starting with `data-` or `aria-` are **preserved as-is**, in line with React's conventions._

### Attribute name normalization

> playground: title=Certain attributes are automatically renamed for React compatibility; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.2.0.wasm

```
<form enctype="multipart/form-data" accept-charset="UTF-8">
  <input name="username" popovertarget="hint">
  <textarea maxlength="200" autocapitalize="sentences"></textarea>
  <button formaction="/submit" formtarget="_blank">Submit</button>
</form>

<video controlslist="nodownload">
  <source src="video.mp4" srcset="video-480.mp4 480w, video-720.mp4 720w">
</video>
```

Attribute renaming only occurs when the attribute is valid for the tag. For instance, `formaction` isn't renamed on `<img>` since it isn't valid there.

However, some attributes are renamed globally, regardless of which element they're used on. These include:

- All standard event handler attributes (`onclick`, `onchange`, etc.), which are converted to their camelCased React equivalents (e.g. `onClick`, `onChange`)
- Common HTML aliases and reserved keywords like `class` and `for`, which are renamed to `className` and `htmlFor`
- Certain accessibility- and editing-related attributes, such as `spellcheck` and `tabindex`

_See [`table.go`](https://github.com/tetsuo/restache/blob/v0.x/table.go) for the full list._

### Implicit key insertion in loops

When rendering lists, restache inserts a `key` prop automatically, assigning it to the top-level element or to a wrapping Fragment if there are multiple root elements.

> playground: title=Key is passed to the root element inside a loop; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.3-dev.wasm

```
{#images}
  <img src={src}>
{/images}
```

> playground: title=If there are multiple roots, it goes on the Fragment; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.3-dev.wasm

```
{#items}
  <h1>{title}</h1>
  <h3>{description}</h3>
{/items}
```

> playground: title=Manually set key when there's single root; button=Run; title_attr=Ctrl/Cmd + Enter; autorun=True; runtime=restache-0.3-dev.wasm

```
{#images}
  <img key={id} src={src}>
{/images}
```

---

## Importing other components

> **restache supports an implicit module system where custom elements (i.e., tags that are not part of the HTML spec) are automatically resolved to file-based components.**

Component imports are inferred from the tag names. The following examples show how different components are resolved:

| HTML               | JSX              | Import path                |
| ------------------ | ---------------- | -------------------------- |
| `<my-button>`      | `<MyButton>`     | `./MyButton`               |
| `<ui:card-header>` | `<UiCardHeader>` | `./ui/CardHeader`          |
| `<main>`           | `<main>`         | Not resolved, standard tag |
| `<ui:div>`         | `<UiDiv>`        | `./ui/div`                 |

### Component resolution

Any tag that isn't a known HTML element is treated as a component.

When the parser encounters such a tag, it follows these steps:

#### 1. Check for namespace

restache first determines whether the tag uses a namespace. Namespaced tags contain a prefix and a component name (e.g., `<ui:button>`).

#### 2. Standard custom tags

If the tag **does not** contain a namespace (e.g., `<my-button>`):

- restache first looks for an exact match in the build configuration's `tagMappings`.
- If no mapping is found, it falls back to searching in the current directory.
  For example, `<my-button>` could resolve to either `./my-button` or `./MyButton`.

#### 3. Namespaced tags

If the tag **does** contain a namespace (e.g., `<ui:button>`):

- restache first checks the `tagPrefixes` configuration. If a prefix (e.g., `ui`) is defined, it uses the mapped path.
  For example, if `mui` is mapped to `@mui/material`, then `<mui:app-bar>` resolves to `@mui/material/AppBar`.

- If no mapping is found, it attempts to resolve the component from a subdirectory:
  e.g., `<ui:button>` → `ui/Button.js`, `ui/button.jsx`, `ui/button.tsx`, etc.

ℹ️ **Note:** Standard HTML tags are not resolved as components, even if identically named files exist in the current directory.
However, **namespacing can override this behavior**. For example, `<ui:div>` will resolve to `./ui/div` (or `./ui/Div`), even though `<div>` is a native HTML element.

---

## ESBuild integration

restache includes an ESBuild plugin that makes integration simple and easy in Go:

- Register `.html` loader and pass it to the plugin
- Plugin uses restache compiler to convert to `.jsx`
- No runtime library needed; everything is transpiled ahead of time

> The [`dashboard`](https://github.com/tetsuo/dashboard) project includes a working build script ([`build.go`](https://github.com/tetsuo/dashboard/blob/master/build.go)).

There's currently no support for Node.JS environment, but planned.

---

## Roadmap

### Integration with React hooks

Currently, most logic must live in a `.jsx` file next to the corresponding `.html` file.

The long-term plan is to introduce a minimal set of expressions into the language itself so that common hooks like `useState`, `useContext`, and `useSelector` from Redux can be inferred from markup and compiled automatically.

---

### Relational and logical expressions

Support for predicates inside range blocks is planned for v1.

```
{#products: price < 100 && inStock}
  <product-card />
{/products}
```

This could be compiled as a filter, and potentially mapped to things like backend queries (e.g. MongoDB, CouchDB, Algolia, ...) as well.

---

### Smarter code generation

Before adding expressions, there's still a lot that can be optimized with the syntax that's already in place.

Consider pattern matching. Since restache doesn't support expressions beyond dot notation, patterns have to be represented structurally. For example, using an object with a mutually exclusive key set:

```js
{
  home: {...},
  settings: undefined,
  products: undefined
}
```

Then in the template:

```
{?home}    <home />    {/home}
{?settings}<settings />{/settings}
{?products}<products />{/products}
```

Compiles to:

```js
if (props.home) <Home />
if (props.settings) <Settings />
```

This results in an `O(n)` operation instead of an `O(1)` equality check like `switch(route)`, but the difference is negligible unless you're dealing with many conditions.

Future versions of restache will generate `if/else` or `switch` statements when keyed unions are used, along with other optimizations such as merging adjacent `{?x}` and `{^x}` blocks into a single conditional.

---

### More codegen targets

Plans include:

* Emitting a real JavaScript AST instead of raw JSX strings
* Supporting things other than React
* Option to emit TSX

When TypeScript is used and type information is available at build time, more advanced optimizations may be possible. But even without that, structural inference allows detecting optionals and iterables, which can be used to emit a generic type for the component.
