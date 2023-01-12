#!/usr/bin/env python

from dataclasses import dataclass, replace
from markdown2 import markdown
from tornado import template, locale
from tornado.locale import Locale
from tornado.template import Loader, Template
from typing import Any
import os
import json
import glob
import sys
import datetime


@dataclass
class Entry:
    title: str
    slug: str
    body: str
    body_external: str
    tags: list[str]
    published: datetime.datetime
    updated: datetime.datetime
    link: str

    def to_json(self, include_body=True):
        value = {
            "slug": self.slug,
            "title": self.title,
            "published": self.published.isoformat(),
            "updated": self.updated.isoformat(),
            "tags": self.tags,
            "link": self.link,
        }

        if include_body:
            value["body"] = self.body_external

        return value


def entry_from_markdown(filename: str, domain_name: str) -> Entry:
    with open(filename, "r") as f:
        data = f.read()
        f.close()

    body = markdown(
        data,
        extras=["fenced-code-blocks", "tables", "metadata"]
    )

    # highlightjs-lang disables pygments which is needed for
    # preserving spaces in <code> blocks for atom feeds
    body_external = markdown(
        data,
        extras=["fenced-code-blocks", "tables", "metadata", "highlightjs-lang"]
    )

    slug = os.path.splitext(os.path.basename(filename))[0].lower()

    return Entry(
        slug=slug,
        body=body,
        body_external=body_external,
        tags=body.metadata['tags'].split(','),
        title=body.metadata['title'],
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
    email: str
    ga_id: str
    comments: str
    links: list[str]


@dataclass
class Generator:
    debug: bool
    locale: Locale
    entries_per_page: int
    template_loader: Loader
    entries: list[Entry]
    settings: Settings

    def _generate(
        self,
        t: Template,
        entries: list[Entry],
        name: str,
        extra_args: dict[str, Any] = {},
        include_json_body: bool = False
    ):
        args = {
            "entries": entries,
            "settings": self.settings,
            "debug": self.debug,
            "locale": self.locale,
        }
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
        t = self.template_loader.load("entry.html")

        for entry in self.entries:
            self._generate(t, [entry], entry.slug, include_json_body=True)

        pages: list[list[Entry]] = []

        for i, entry in enumerate(self.entries):
            if i % self.entries_per_page == 0:
                pages.append([])
            pages[len(pages) - 1].append(entry)

        pages_len = len(pages)

        t = self.template_loader.load("entries.html")

        for i, page in enumerate(pages):
            page_num = i + 1
            self._generate(t, page, str(page_num), extra_args={
                           "more": page_num != pages_len, "page": page_num})

        index_entries = pages[0] if pages_len > 0 else []

        self._generate(
            t, index_entries, "index",
            extra_args={
                "more": pages_len > 1,
                "page": 1
            }
        )

        entries_by_tag: dict[str, list[Entry]] = {}

        for entry in self.entries:
            for tag in entry.tags:
                if tag not in entries_by_tag:
                    entries_by_tag[tag] = []
                entries_by_tag[tag].append(entry)

        t = self.template_loader.load("tag.html")

        for tag in entries_by_tag:
            self._generate(
                t, entries_by_tag[tag], tag,
                extra_args={"_tag": tag}
            )

        t = self.template_loader.load("atom.xml")

        b = t.generate(**{
            "entries": [replace(e, body=e.body_external) for e in index_entries],
            "settings": self.settings,
            "_tag": None
        })

        with open("public/feed.xml", "wb") as f:
            f.write(b)

        for tag in entries_by_tag:
            b = t.generate(**{
                "entries": [replace(e, body=e.body_external) for e in entries_by_tag[tag]],
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

        sitemap_entries: list[str] = []
        sitemap_entries.extend([str(i+2) for i in list(range(pages_len-1))])
        sitemap_entries.extend(list(entries_by_tag.keys()))
        sitemap_entries.extend([e.slug for e in self.entries])

        b = t.generate(**{"settings": self.settings,
                       "entries": sitemap_entries})

        with open("public/sitemap.xml", "wb") as f:
            f.write(b)


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
            email=c['email'],
            ga_id=c['analyticsId'],
            comments=c['showComments'],
            links=c['links'],
        )
    ).run()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
