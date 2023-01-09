from tornado import template, locale
from markdown2 import markdown
import os
import json
import glob
import sys
import datetime


def read_markdown(file):
    with open(file, "r") as f:
        body = f.read()
        f.close()

    md = markdown(
        body,
        extras=["fenced-code-blocks", "tables", "metadata"]
    )

    entry = md.metadata

    entry.update({
        "slug": os.path.splitext(file)[0].lower(),
        "body_html": md,
        "tags": entry['tags'].split(','),
        "published": datetime.datetime.fromisoformat(entry['published']),
        "updated": datetime.datetime.fromisoformat(entry['updated']),
    })

    return entry


def write_pages(entries, config, template_loader):
    t = template_loader.load("entries.html")

    pages = []

    for i, entry in enumerate(entries):
        if i % config['entries_per_page'] == 0:
            pages.append([])
        pages[len(pages) - 1].append(entry)

    pages_len = len(pages)

    for i, page in enumerate(pages):
        page_num = i + 1
        args = {
            "entries": page,
            "more": page_num != pages_len,
            "page": page_num,
        }
        args.update(config)

        b = t.generate(**args)

        with open("public/%d.html" % page_num, "wb") as f:
            f.write(b)

        if i == 0:
            with open("public/index.html", "wb") as f:
                f.write(b)


def write_tags(entries, config, template_loader):
    t = template_loader.load("tag.html")

    tags = {}

    for entry in entries:
        for tag in entry['tags']:
            if tag not in tags:
                tags[tag] = []
            tags[tag].append(entry)

    for tag in tags:
        tag_entries = tags[tag]
        args = {
            "entries": tag_entries,
            "_tag": tag,
        }
        args.update(config)

        b = t.generate(**args)

        with open("public/%s.html" % tag, "wb") as f:
            f.write(b)


def write_entries(entries, config, template_loader):
    t = template_loader.load("entry.html")

    for entry in entries:
        args = {
            "entries": [entry],
        }
        args.update(config)

        b = t.generate(**args)

        with open("public/%s.html" % entry['slug'], "wb") as f:
            f.write(b)


def write_opensearch_xml(config, template_loader):
    t = template_loader.load("opensearch.xml")

    b = t.generate(**config)

    with open("public/opensearch.xml", "wb") as f:
        f.write(b)


def main(args=None):
    if args is None:
        args = sys.argv

    args = args[1:]

    config_file = "config.json"

    if len(args) > 0:
        config_file = args[0]

    with open(config_file) as f:
        config = json.load(f)

    template_loader = template.Loader(config['templatePath'], autoescape=None)

    config = {
        "debug": config['debug'],
        "locale": locale.get(config['locale']),
        "entries_per_page": config['entriesPerPage'],
        "settings": {
            "site_name": config['siteName'],
            "domain": config['domain'],
            "title": config['title'],
            "description": config['description'],
            "author": config['twitterId'],
            "email": config['email'],
            "ga_id": config['analyticsId'],
            "comments": config['showComments'],
            "links": config['links']
        },
    }

    entries = [read_markdown(file) for file in glob.glob("*.md")]
    entries.sort(key=lambda e: e['published'], reverse=True)

    write_entries(entries, config, template_loader)
    write_pages(entries, config, template_loader)
    write_tags(entries, config, template_loader)
    write_opensearch_xml(config, template_loader)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
