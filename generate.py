#!/usr/bin/env python3

from bs4 import BeautifulSoup
from dataclasses import dataclass, replace
from markdown2 import markdown
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color
from textwrap import wrap
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


def entry_from_markdown(filename: str, domain_name: str) -> Entry:
    with open(filename, "r") as f:
        data = f.read()
        f.close()

    body = markdown(
        data,
        extras=[
            "header-ids",
            "footnotes",
            "fenced-code-blocks",
            "tables",
            "metadata"
        ]
    )

    # highlightjs-lang disables pygments which is needed for
    # preserving spaces in <code> blocks for atom feeds
    body_feed = markdown(
        data,
        extras=["footnotes", "fenced-code-blocks",
                "tables", "metadata", "highlightjs-lang",]
    )

    slug = os.path.splitext(os.path.basename(filename))[0].lower()

    soup_body_feed = BeautifulSoup(body_feed, features="html.parser")
    soup_body = BeautifulSoup(body, features="html.parser")

    description = body.metadata['description']

    first_blockquote = soup_body.find("blockquote", recursive=False)
    if first_blockquote.name == "blockquote":
        description = first_blockquote.get_text().strip()
    else:
        raise RuntimeError("must have a blockquote")

    imgs_body_feed = soup_body_feed.find_all("img")
    imgs_body = soup_body.find_all("img")

    for img in imgs_body:
        img_src = img.get('src')
        img_filename = os.path.basename(img_src)
        dirname = os.path.dirname(img_src)
        if img.parent.name == "a" and img.parent.parent.name == "p":
            anchor_url = urlparse(img.parent.get('href'))

            if './images' == dirname and anchor_url.hostname == None:
                img_w = re.findall('-(\d{1,3})$', os.path.splitext(img_src)[0])
                img.parent.parent['class'] = 'ta-center'
                if len(img_w) > 0:
                    img['class'] = 'i-' + img_w[0]
            if '.' == dirname and anchor_url.hostname == domain_name:
                url_parts = anchor_url.path[1:].split('/')
                if len(url_parts) != 2:
                    continue
                url_type = url_parts[0]
                url_filename = os.path.splitext(url_parts[1])
                if url_filename[1] != ".html":
                    continue
                url_id = url_filename[0]

                iframe_tag = soup_body.new_tag("iframe")
                iframe_tag.attrs['id'] = url_id + "-iframe"
                iframe_tag.attrs['name'] = url_id
                iframe_tag.attrs['frameborder'] = "0"
                iframe_tag.attrs['title'] = img.get('alt')
                iframe_tag.attrs['src'] = anchor_url.path

                div_tag = soup_body.new_tag("div")
                div_tag.attrs['id'] = url_id
                if 'w' in url_type:
                    div_tag.attrs['data-routable'] = ""
                if 'r' in url_type:
                    div_tag.attrs['data-resizable'] = ""
                    div_tag.attrs['class'] = "resizeable-widget"

                div_tag.append(iframe_tag)

                img.parent.parent.replaceWith(div_tag)

        img['src'] = '/images/' + img_filename
        img.parent['href'] = img['src']

    images: list[dict[str, Any]] = []
    for img in imgs_body_feed:
        img_filename = os.path.basename(img['src'])
        dirname = os.path.dirname(img.get('src'))
        if '.' == dirname:
            continue
        img['src'] = "https://" + domain_name + "/images/" + img_filename
        with Image(filename="public/images/" + img_filename) as f:
            width = f.width
            height = f.height
            mimetype = f.mimetype
            filesize = f.length_of_bytes
        images.append({
            "filename": img_filename,
            "title": img.get("title", img.get("alt", "")),
            "width": width,
            "height": height,
            "mimetype": mimetype,
            "filesize": filesize
        })

    anchors_body_feed = soup_body_feed.find_all("a")
    anchors_body = soup_body.find_all("a")

    for a in anchors_body_feed:
        if a['href'].startswith("./") and a['href'].endswith(".md"):
            a['href'] = "https://" + domain_name + \
                "/" + a['href'][2:-3] + ".html"

    for a in anchors_body:
        if a['href'].startswith("./") and a['href'].endswith(".md"):
            a['href'] = "/" + a['href'][2:-3] + ".html"
        elif not a['href'].startswith("#"):
            a['target'] = "_blank"

    headlines = soup_body.find_all(["h1", "h2"])

    for h in headlines:
        if h['id'] is not None:
            headline_a = soup_body.new_tag("a")
            headline_a.attrs['class'] = 'bookmark'
            h['id'] = "/" + h['id']
            headline_a.attrs['href'] = '#' + h['id']
            h.append(headline_a)

    for h in soup_body.find_all(["h3", "h4", "h5"]):
        del h['id']

    for h in soup_body_feed.find_all(["h1", "h2", "h3", "h4", "h5"]):
        del h['id']

    div_containers_body = soup_body.find_all("div", recursive=False)

    def get_div_container_metadata(el):
        if el.get('id') is None:
            return []

        metadata: list[str] = [el.get('id')]

        if el.get('data-resizable') is not None:
            metadata.append("resize")
        if el.get('data-routable') is not None:
            metadata.append("route")

        return metadata

    mm = list(map(get_div_container_metadata, div_containers_body))

    for div in div_containers_body:
        if div.get('data-resizable') is not None:
            resize_tag = soup_body.new_tag("div")
            resize_tag.attrs['class'] = 'resize-handle'
            div.insert_after(resize_tag)

    cover_title = body.metadata['title']
    if 'cover_title' in body.metadata:
        cover_title = body.metadata['cover_title']

    blockquotes = soup_body.find_all("blockquote")

    for blockquote in blockquotes:
        if blockquote.parent.name == "blockquote":
            blockquote.parent.replace_with(blockquote)
            blockquote.attrs['class'] = "note"

    return Entry(
        slug=slug,
        body=str(soup_body),
        body_feed=str(soup_body_feed),
        description=description,
        metadata=mm,
        short_description=body.metadata['description'],
        images=images,
        tags=body.metadata['tags'].split(','),
        title=body.metadata['title'],
        cover_title=cover_title,
        published=datetime.datetime.fromisoformat(body.metadata['published']),
        updated=datetime.datetime.fromisoformat(body.metadata['updated']),
        link="https://" + domain_name + "/" + slug + ".html",
    )


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
    images: bool
    comments: bool
    links: list[str]


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

        json_obj = {"entries": [
            entry.to_json(include_body=include_json_body) for entry in entries
        ]}

        with open("public/%s.json" % name, "w") as f:
            json.dump(json_obj, f)

    def run(self) -> None:
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

        t = self.template_loader.load("entry.html")

        for entry in self.entries:
            resizable_ids: list[str] = []
            router_ids: list[str] = []

            for mm in entry.metadata:
                if len(mm) < 1:
                    continue
                sid = mm[0]
                if mm.count('resize') > 0:
                    resizable_ids.append(sid)
                if mm.count('route') > 0:
                    router_ids.append(sid+"-iframe")

            self._generate(t, [entry], entry.slug, include_json_body=True,
                           extra_args={
                "resizable_ids": resizable_ids,
                "router_ids": router_ids,
            })

        t = self.template_loader.load("index.html")

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

        t = self.template_loader.load("tag.html")

        for tag in entries_by_tag:
            self._generate(
                t, entries_by_tag[tag], tag,
                extra_args={
                    "_tag": tag,
                    "keywords": [tag] + [x for x in keywords if x != tag]
                }
            )

        t = self.template_loader.load("atom.xml")

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

            with open("public/%s.xml" % tag, "wb") as f:
                f.write(b)

        t = self.template_loader.load("opensearch.xml")

        b = t.generate(**{"settings": self.settings})

        with open("public/opensearch.xml", "wb") as f:
            f.write(b)

        t = self.template_loader.load("sitemap.xml")

        b = t.generate(**{"settings": self.settings,
                       "entries": sitemap_entries})

        with open("public/sitemap.xml", "wb") as f:
            f.write(b)

        t = self.template_loader.load("manifest.webmanifest")

        b = t.generate(**{"settings": self.settings})

        with open("public/manifest.webmanifest", "wb") as f:
            f.write(b)

        with open("public/robots.txt", "w") as f:
            f.write("User-agent: *\nAllow: /\n")

        t = self.template_loader.load("about.html")

        b = t.generate(**dict({"keywords": keywords},
                       **self._get_template_args()))

        with open("public/about.html", "wb") as f:
            f.write(b)

        if self.settings.images:
            for entry in self.entries:
                create_cover_image(entry.cover_title, entry.short_description,
                                   "public/" + entry.slug + ".png")

            create_cover_image(
                "ogunz", self.settings.description, "public/index.png"
            )


def main(args=None):
    if args is None:
        args = sys.argv

    args = args[1:]

    config_file = "config.json"

    if len(args) > 0:
        config_file = args[0]

    with open(config_file) as f:
        c = json.load(f)

    entries = [
        entry_from_markdown(f, c['domain'])
        for f in glob.glob(c['articlesPath'])
    ]
    entries.sort(key=lambda e: e.published, reverse=True)

    Generator(
        debug=c['debug'],
        locale=locale.get(c['locale']),
        entries_per_page=c['entriesPerPage'],
        entries=entries,
        template_loader=template.Loader(c['templatePath'], autoescape=None),
        settings=Settings(
            site_name=c['siteName'],
            domain=c['domain'],
            title=c['title'],
            description=c['description'],
            author='@'+c['twitterId'],
            author_name=c['authorName'],
            email=c['email'],
            ga_id=c['analyticsId'],
            comments=c['showComments'],
            images=c['buildImages'],
            links=c['links'],
        )
    ).run()


def create_cover_image(title: str, desc: str, outfile: str):
    with Drawing() as ctx:
        with Image(width=940, height=529, background=Color("#aaa")) as img:
            ctx.fill_color = "#0000ff"
            ctx.font = "public/assets/Code_Pro_Demo-webfont.ttf"
            ctx.font_size = 50
            ctx.text(40, 142, title)
            ctx.fill_color = "#fff"
            ctx.font_size = 50
            mutable_message = word_wrap(img, ctx, desc, 880, 300)
            ctx.text(40, 240, mutable_message)  # + "."
            ctx.fill_color = "#0000ff"
            ctx.circle((68, 450), (68, 476))
            ctx.fill_color = "#fff"
            ctx.circle((133, 450), (133, 476))
            ctx.fill_color = "orange"
            ctx.circle((198, 450), (198, 476))
            ctx.font_size = 80
            ctx.draw(img)
            img.save(filename=outfile)


def word_wrap(image, ctx, text, roi_width, roi_height):
    """Break long text to multiple lines, and reduce point size
    until all text fits within a bounding box."""
    mutable_message = text
    iteration_attempts = 100

    def eval_metrics(txt):
        """Quick helper function to calculate width/height of text."""
        metrics = ctx.get_font_metrics(image, txt, True)
        return (metrics.text_width, metrics.text_height)

    def shrink_text():
        """Reduce point-size & restore original text"""
        ctx.font_size = ctx.font_size - 0.75
        mutable_message = text

    while ctx.font_size > 0 and iteration_attempts:
        iteration_attempts -= 1
        width, height = eval_metrics(mutable_message)
        if height > roi_height:
            shrink_text()
        elif width > roi_width:
            columns = len(mutable_message)
            while columns > 0:
                columns -= 1
                mutable_message = '\n'.join(wrap(mutable_message, columns))
                wrapped_width, _ = eval_metrics(mutable_message)
                if wrapped_width <= roi_width:
                    break
            if columns < 1:
                shrink_text()
        else:
            break
    if iteration_attempts < 1:
        raise RuntimeError("Unable to calculate word_wrap for " + text)

    return mutable_message


if __name__ == "__main__":
    sys.exit(main(sys.argv))
