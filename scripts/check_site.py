"""Check generated local links and every native atlas/browser asset."""

import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in {"a", "img", "script", "link"}:
            attributes = dict(attrs)
            value = attributes.get("href") or attributes.get("src")
            if value:
                self.links.append(value)


def check_site(root: Path) -> None:
    """Fail on broken local links, root-absolute URLs or missing atlas data."""
    errors = []
    checked = 0
    for page in root.rglob("*.html"):
        # Theme templates are resources, not rendered browser pages.
        if "_static" in page.relative_to(root).parts:
            continue
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for link in parser.links:
            url = urlsplit(link)
            if url.scheme or url.netloc or not url.path:
                continue
            path = unquote(url.path)
            if path.startswith("/"):
                errors.append(f"{page}: root-absolute URL breaks project hosting: {link}")
            elif not (page.parent / path).exists():
                errors.append(f"{page}: missing local target: {link}")
            checked += 1
    atlas = root / "atlas"
    catalog = json.loads((atlas / "data/catalog.json").read_text())
    for layer in catalog["layers"]:
        for key in ("image", "values", "download"):
            path = atlas / layer[key].lstrip("/")
            if not path.is_file():
                errors.append(f"{layer['id']}: missing {key}: {path}")
            elif key == "values" and path.stat().st_size != layer["width"] * layer["height"] * 4:
                errors.append(f"{layer['id']}: binary values do not match the native grid")
    if errors:
        raise ValueError("\n".join(errors))
    print(f"Checked {checked} local links and {len(catalog['layers'])} complete atlas layers.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", default="docs/_build/html")
    check_site(Path(parser.parse_args().directory).resolve())
