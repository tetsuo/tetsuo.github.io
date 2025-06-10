#!/usr/bin/env python3

from bs4 import BeautifulSoup
from dataclasses import dataclass, replace
from concurrent.futures import ThreadPoolExecutor
from markdown2 import markdown
from wand.image import Image
from wand.exceptions import BlobError
from tornado import template, locale
from tornado.locale import Locale
from tornado.template import Loader, Template
from typing import Any
from urllib.parse import urlparse
import os
import re
import json
import glob
import sys
import datetime
import unicodedata
import hashlib


@dataclass
class Settings:
    site_name: str
    title: str
    description: str
    domain: str
    author: str
    author_name: str
    email: str
    ga_id: str
    cover_images: bool
    comments: bool
    styles_id: str
    skip_feeds: bool
    skip_json: bool
    skip_images: bool


@dataclass
class Entry:
    title: str
    cover_title: str
    description: str
    short_description: str
    slug: str
    body: str
    body_feed: str
    images: list[dict[str, Any]]
    tags: list[str]
    published: datetime.datetime
    updated: datetime.datetime
    link: str
    has_playground: bool
    has_code: bool
    playground_runtime: str

    metadata: list[list[str]]

    def to_json(self, include_body=True):
        value = {
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "images": self.images,
            "published": self.published.isoformat(),
            "updated": self.updated.isoformat(),
            "tags": self.tags,
            "link": self.link,
        }

        if include_body:
            value["body"] = self.body_feed

        return value


def add_example_details(soup_root, title, button_label, button_title, body, open_attr=True, autorun=False):
    details = soup_root.new_tag("details", **{
        "class": "Playground-Details js-exampleContainer"
    })
    if open_attr:
        details.attrs["open"] = ""
    if autorun:
        details.attrs["data-autorun"] = ""

    summary = soup_root.new_tag("summary", **{
        "class": "Playground-DetailsHeader"
    })
    summary_span = soup_root.new_tag("span")
    summary_span.append(title)
    summary.append(summary_span)

    toolbar = soup_root.new_tag("div", **{"class": "Playground-DetailsToolbar"})
    buttons_container = soup_root.new_tag("div", **{"class": "Playground-ButtonsContainer"})

    error_p = soup_root.new_tag("p", **{
        "class": "Playground-Error",
        "role": "alert",
        "aria-atomic": "true"
    })
    buttons_container.append(error_p)

    button = soup_root.new_tag("button", **{
        "class": "Playground-RunButton",
        "aria-label": button_label,
        "title": button_title
    })
    button.string = button_label
    buttons_container.append(button)

    toolbar.append(buttons_container)
    summary.append(toolbar)
    details.append(summary)

    body_div = soup_root.new_tag("div", **{"class": "Playground-DetailsBody"})

    textarea = soup_root.new_tag("textarea", **{
        "class": "Playground-Code code",
        "spellcheck": "false",
    })
    textarea.string = body
    body_div.append(textarea)

    pre = soup_root.new_tag("pre")
    output_label = soup_root.new_tag("span", **{"class": "Playground-OutputLabel"})
    output_label.string = "Output:"
    output_span = soup_root.new_tag("span", **{"class": "Playground-Output"})
    pre.append(output_label)
    pre.append(output_span)
    body_div.append(pre)

    details.append(body_div)

    return details


def _convert_playground_blocks(soup: BeautifulSoup, is_feed: bool = False):
    has_playground = False
    runtime = ""

    for bq in soup.find_all("blockquote"):
        text = bq.get_text().strip()
        if not text.lower().startswith("playground:"):
            continue

        has_playground = True

        param_str = text[len("playground:"):].strip()
        params = dict(
            part.strip().split("=", 1)
            for part in param_str.split(";")
            if "=" in part
        )

        runtime = params.get("runtime", runtime)
        title = params.get("title", "Playground")
        button = params.get("button", "Run")
        title_attr = params.get("title_attr", button)
        autorun = params.get("autorun", "false").lower() in ("true", "1", "yes")

        next_el = bq.find_next_sibling()
        if not (next_el and next_el.name == "pre" and next_el.code):
            continue  # No code block found after

        code = next_el.code.get_text()

        if is_feed:
            # Replace blockquote with <p>title</p>, keep code
            p = soup.new_tag("p")
            p.string = title
            bq.replace_with(p)
        else:
            placeholder = soup.new_tag("div")
            bq.insert_before(placeholder)

            details_tag = add_example_details(
                soup_root=soup,
                title=title,
                button_label=button,
                button_title=title_attr,
                body=code,
                open_attr=True,
                autorun=autorun,
            )
            placeholder.append(details_tag)

            next_el.decompose()
            bq.decompose()

    return has_playground, runtime


def _cleanup_blockquotes(soup: BeautifulSoup, is_feed: bool):
    for bq in soup.find_all("blockquote"):
        if bq.parent.name == "blockquote":
            if is_feed:
                # In feed: unwrap outer blockquote
                bq.parent.replace_with(bq)
            else:
                # In HTML: convert to .note
                bq.parent.replace_with(bq)
                bq["class"] = "note"


def _embed_iframe_from_path(soup: BeautifulSoup, img, path: str) -> None:
    parts = path.strip("/").split("/")
    if len(parts) != 2:
        return
    flag_str, filename = parts
    base, ext = os.path.splitext(filename)
    if ext != ".html":
        return

    iframe = soup.new_tag("iframe", attrs={
        "id": f"{base}-iframe",
        "name": base,
        "frameborder": "0",
        "title": img.get("alt"),
        "src": path
    })

    container = soup.new_tag("div", attrs={"id": base})
    if "w" in flag_str:
        container["class"] = container.get("class", []) + ["js-RoutableContent"]
    if "r" in flag_str:
        container["class"] = container.get("class", []) + ["js-ResizableContent"]
    if "f" in flag_str:
        container["data-fullsize"] = ""
        container["style"] = iframe["style"] = "width: 100%"

    container.append(iframe)
    img.parent.parent.replace_with(container)


def _process_body_images(soup: BeautifulSoup, domain: str) -> None:
    for img in soup.find_all("img"):
        src = img.get("src", "")
        filename = os.path.basename(src)
        dirname = os.path.dirname(src)

        if img.parent.name == "p":
            img.parent["class"] = "text-center"

        # Handle image wrapped in a link to .html on own domain
        elif img.parent.name == "a" and img.parent.parent.name == "p":
            href = img.parent.get("href", "")
            parsed = urlparse(href)

            if dirname == "./images" and not parsed.hostname:
                if match := re.search(r"-(\\d{1,3})$", os.path.splitext(src)[0]):
                    img["class"] = f"w-{match.group(1)}"
                img.parent.parent["class"] = "text-center"

            elif dirname == "." and parsed.hostname == domain:
                _embed_iframe_from_path(soup, img, parsed.path)

        # Always rewrite src to /images/
        img["src"] = f"/images/{filename}"
        if img.parent.name == "a":
            img.parent["href"] = img["src"]


def _process_feed_images(soup: BeautifulSoup, domain: str) -> list[dict[str, Any]]:
    images = []

    for img in soup.find_all("img"):
        src = img.get("src", "")
        dirname = os.path.dirname(src)
        if dirname == ".":
            filename = os.path.basename(src)
            img["src"] = f"https://{domain}/images/{filename}"
            continue  # placeholder images are not added as media content

        filename = os.path.basename(src)
        img["src"] = f"https://{domain}/images/{filename}"

        img_path = os.path.join("public", "images", filename)
        if not os.path.exists(img_path):
            print(f"image not found: {img_path}; skipping")
            continue

        try:
            with Image(filename=img_path) as im:
                images.append({
                    "filename": filename,
                    "title": img.get("title", img.get("alt", "")),
                    "width": im.width,
                    "height": im.height,
                    "mimetype": im.mimetype,
                    "filesize": im.length_of_bytes,
                })
        except BlobError as e:
            print(f"unable to read image: {img_path}: {e}")

    return images


MD_EXTRAS = ["footnotes", "fenced-code-blocks", "tables", "metadata"]

def entry_from_markdown(filename: str, domain: str, settings: Settings) -> Entry:
    with open(filename, "r") as f:
        raw = f.read()

    html = markdown(raw, extras=["header-ids"] + MD_EXTRAS)

    # highlightjs-lang disables pygments which is needed for
    # preserving spaces in <code> blocks for atom feeds
    html_feed = markdown(raw, extras=MD_EXTRAS + ["highlightjs-lang"])

    soup = BeautifulSoup(html, "html.parser")
    soup_feed = BeautifulSoup(html_feed, "html.parser")

    metadata = html.metadata
    title = metadata["title"]
    cover_title = metadata.get("cover_title", title)
    short_desc = metadata["description"]
    published = datetime.datetime.fromisoformat(metadata["published"])
    updated = datetime.datetime.fromisoformat(metadata["updated"])
    tags = [tag.strip() for tag in metadata["tags"].split(",")]

    # Required blockquote
    bq = soup.find("blockquote", recursive=False)
    if not bq:
        raise RuntimeError("must have a blockquote")
    description = bq.get_text().strip()

    # Check playground blocks
    has_pg, runtime = _convert_playground_blocks(soup, is_feed=False)
    _convert_playground_blocks(soup_feed, is_feed=True)

    # Process images
    _process_body_images(soup, domain)
    images = [] if settings.skip_images else _process_feed_images(soup_feed, domain)

    # Configure links
    _fix_anchors(soup_feed, domain, feed=True)
    _fix_anchors(soup, domain, feed=False)

    # Extract metadata
    metadata_flags = _extract_metadata_and_widgets(soup)

    # Clean up blockquotes inside blockquotes
    _cleanup_blockquotes(soup_feed, True)
    _cleanup_blockquotes(soup, False)

    slug = re.sub(r"[^\w]+", "-", unicodedata.normalize("NFKD", title)).strip("-").lower()

    # Count <pre><code> blocks that were not playgrounds
    has_code = any(
        pre.find("code") for pre in soup.find_all("pre")
    )

    return Entry(
        slug=slug,
        title=title,
        cover_title=cover_title,
        description=description,
        short_description=short_desc,
        body=str(soup),
        body_feed=str(soup_feed),
        images=images,
        tags=tags,
        published=published,
        updated=updated,
        link=f"https://{domain}/{slug}.html",
        metadata=metadata_flags,
        has_playground=has_pg,
        has_code=has_code,
        playground_runtime=runtime,
    )


def _fix_anchors(soup: BeautifulSoup, domain: str, feed: bool):
    if feed:
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("/") and a["href"].endswith(".html"):
                a["href"] = f"https://{domain}{a['href']}"
    else:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not (href.startswith("#") or href.endswith(".html")):
                a["rel"] = "noopener"

        seen_ids = set()

        # Modify h1–h3 headings with unique IDs and add link
        for h in soup.find_all(["h1", "h2", "h3"]):
            if h.get("id"):
                original_id = h["id"]
                new_id = f"/{original_id}"

                counter = 1
                unique_id = new_id
                while unique_id in seen_ids:
                    unique_id = f"{new_id}-{counter}"
                    counter += 1

                h["id"] = unique_id
                seen_ids.add(unique_id)

                link = soup.new_tag("a", href="#" + unique_id)
                h.append(link)

                classes = h.get("class", [])
                classes.append("js-Bookmark")
                h["class"] = classes

        # Strip IDs from the rest of headers
        for h in soup.find_all("h4", "h5"):
            h.attrs.pop("id", None)


def _extract_metadata_and_widgets(soup: BeautifulSoup) -> list[list[str]]:
    metadata = []
    for div in soup.find_all("div", recursive=False):
        if not div.get("id"):
            continue
        meta = [div["id"]]
        if "js-ResizableContent" in div.get("class", []):
            meta.append("resize")
            handle = soup.new_tag("div", **{"class": "js-ResizableContent__handle"})
            div.insert_after(handle)
        if "js-RoutableContent" in div.get("class", []):
            meta.append("route")
        if div.get("data-fullsize") is not None:
            meta.append("full-size")
        metadata.append(meta)

    for bq in soup.find_all("blockquote"):
        if bq.parent.name == "blockquote":
            bq.parent.replace_with(bq)
            bq["class"] = "note"

    return metadata


@dataclass
class Generator:
    debug: bool
    locale: Locale
    entries_per_page: int
    template_loader: Loader
    entries: list[Entry]
    settings: Settings

    def _get_template_args(self):
        return {
            "settings": self.settings,
            "debug": self.debug,
            "locale": self.locale,
        }

    def _generate(
        self,
        t: Template,
        entries: list[Entry],
        name: str,
        extra_args: dict[str, Any] = {},
        include_json_body: bool = False
    ):
        args = {"entries": entries}
        args.update(self._get_template_args())
        args.update(extra_args)

        b = t.generate(**args)

        with open("public/%s.html" % name, "wb") as f:
            f.write(b)

        if not self.settings.skip_json:
            json_obj = {
                "entries": [
                    entry.to_json(include_body=include_json_body)
                    for entry in entries
                ]
            }

            with open("public/%s.json" % name, "w") as f:
                json.dump(json_obj, f)

    def run(self) -> None:
        templates = {
            "entry": self.template_loader.load("entry.html"),
            "index": self.template_loader.load("index.html"),
            "tag": self.template_loader.load("tag.html"),
            "atom": self.template_loader.load("atom.xml"),
            "sitemap": self.template_loader.load("sitemap.xml"),
            "opensearch": self.template_loader.load("opensearch.xml"),
            "manifest": self.template_loader.load("manifest.webmanifest"),
            "resume": self.template_loader.load("resume.html"),
        }

        entries_by_tag: dict[str, list[Entry]] = {}

        for entry in self.entries:
            for tag in entry.tags:
                if tag not in entries_by_tag:
                    entries_by_tag[tag] = []
                entries_by_tag[tag].append(entry)

        pages: list[list[Entry]] = []

        for i, entry in enumerate(self.entries):
            if i % self.entries_per_page == 0:
                pages.append([])
            pages[len(pages) - 1].append(entry)

        pages_len = len(pages)

        index_entries = pages[0] if pages_len > 0 else []

        sitemap_entries: list[str] = []
        sitemap_entries.extend([str(i+2) for i in list(range(pages_len-1))])
        sitemap_entries.extend(list(entries_by_tag.keys()))
        sitemap_entries.extend([e.slug for e in self.entries])

        keywords = sorted(list(entries_by_tag.keys()),
                          key=lambda key: len(entries_by_tag[key]))[:20]

        t = templates["entry"]

        for entry in self.entries:
            resizable_ids: list[str] = []
            router_ids: list[str] = []
            fullsize_ids: list[str] = []

            for mm in entry.metadata:
                if len(mm) < 1:
                    continue
                sid = mm[0]
                if mm.count('resize') > 0:
                    resizable_ids.append(sid)
                if mm.count('route') > 0:
                    router_ids.append(sid+"-iframe")
                if mm.count('full-size') > 0:
                    fullsize_ids.append(sid)

            self._generate(t, [entry], entry.slug, include_json_body=True,
                           extra_args={
                "resizable_ids": resizable_ids,
                "router_ids": router_ids,
                "fullsize_ids": fullsize_ids,
            })

        t = templates["index"]

        for i, page in enumerate(pages):
            page_num = i + 1
            self._generate(t, page, str(page_num), extra_args={
                           "more": page_num != pages_len,
                           "page": page_num,
                           "keywords": keywords
                           })

        self._generate(
            t, index_entries, "index",
            extra_args={
                "more": pages_len > 1,
                "page": 1,
                "keywords": keywords
            }
        )

        t = templates["tag"]

        for tag in entries_by_tag:
            self._generate(
                t, entries_by_tag[tag], tag,
                extra_args={
                    "_tag": tag,
                    "keywords": [tag] + [x for x in keywords if x != tag]
                }
            )

        if not self.settings.skip_feeds:
            t = templates["atom"]

            b = t.generate(**{
                "entries": [replace(e, body=e.body_feed) for e in index_entries],
                "settings": self.settings,
                "_tag": None
            })

            with open("public/feed.xml", "wb") as f:
                f.write(b)

            for tag in entries_by_tag:
                b = t.generate(**{
                    "entries": [replace(e, body=e.body_feed) for e in entries_by_tag[tag]],
                    "settings": self.settings,
                    "_tag": tag
                })

                with open(f"public/{tag}.xml", "wb") as f:
                    f.write(b)

        t = templates["opensearch"]

        b = t.generate(**{"settings": self.settings})

        with open("public/opensearch.xml", "wb") as f:
            f.write(b)

        t = templates["sitemap"]

        b = t.generate(**{"settings": self.settings,
                       "entries": sitemap_entries})

        with open("public/sitemap.xml", "wb") as f:
            f.write(b)

        t = templates["manifest"]

        b = t.generate(**{"settings": self.settings})

        with open("public/manifest.webmanifest", "wb") as f:
            f.write(b)

        with open("public/robots.txt", "w") as f:
            f.write("User-agent: *\nAllow: /\n")

        t = templates["resume"]

        b = t.generate(**dict({"keywords": keywords},
                       **self._get_template_args()))

        with open("public/resume.html", "wb") as f:
            f.write(b)

        # TODO: create cover images here if settings.cover_images == True


def get_hex_digest_short(text: str) -> str:
    hex_digest = hashlib.sha1(text.encode()).hexdigest()
    return hex_digest[:4]


def main(args=None):
    if args is None:
        args = sys.argv

    args = args[1:]

    config_file = "config.json"

    if len(args) > 0:
        config_file = args[0]

    with open(config_file) as f:
        cfg = json.load(f)

    styles_id = ""
    if cfg['debug'] != True:
        with open("styles.scss", "r") as f:
            data = f.read()
            styles_id = get_hex_digest_short(data)

    settings = Settings(
        site_name=cfg["siteName"],
        domain=cfg["domain"],
        title=cfg["title"],
        description=cfg["description"],
        author="@" + cfg["twitterId"],
        author_name=cfg["authorName"],
        email=cfg["email"],
        ga_id=cfg["analyticsId"],
        comments=cfg["showComments"],
        cover_images=cfg["coverImages"],
        styles_id=styles_id,
        skip_feeds=cfg.get("skipFeeds", False),
        skip_json=cfg.get("skipJSON", False),
        skip_images=cfg.get("skipImages", False), # skip processing images for feeds
    )

    files = glob.glob(cfg["contentPath"])

    with ThreadPoolExecutor(max_workers=10) as executor:
        entries = list(executor.map(
            lambda f: entry_from_markdown(f, cfg["domain"], settings),
            files
        ))

    entries.sort(key=lambda e: e.published, reverse=True)

    Generator(
        debug=cfg['debug'],
        locale=locale.get(cfg['locale']),
        entries_per_page=cfg['entriesPerPage'],
        entries=entries,
        template_loader=template.Loader(cfg['templatePath'], autoescape=None),
        settings=settings,
    ).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
