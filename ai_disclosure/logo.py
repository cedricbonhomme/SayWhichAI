"""The logo a project file names: an image of the repository, published as it is.

The file comes from a repository the site does not control, and it is served from
the address of the site. A bitmap is only pixels. An SVG file is a document: it may
carry a script, or load something from another server. It is published only when it
is a plain drawing, and it is never repaired: a file that is not one is refused.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"
# Shapes, groups, gradients and text: what a drawing is made of. No script, no style
# sheet, no image, no foreignObject, no animation.
DRAWING = frozenset(
    """svg g defs symbol use title desc path circle ellipse rect line polyline polygon
    text tspan linearGradient radialGradient stop clipPath mask""".split()
)
DECLARATION_RE = re.compile(r"^\ufeff?\s*<\?xml\s[^?]*\?>")
OUTSIDE_RE = re.compile(r"url\(\s*[\"']?(?!#)|image-set\(|src\(|javascript:|data:|@import|expression\(", re.IGNORECASE)


def plain_drawing(image: bytes) -> bool:
    """True when the SVG file holds nothing but a drawing."""
    try:
        # UTF-8 only, so that the checks below read the characters the browser reads.
        text = image.decode("utf-8")
    except UnicodeDecodeError:
        return False
    body = DECLARATION_RE.sub("", text, count=1)
    if "<?" in body:
        return False  # a processing instruction can load a style sheet
    if "<!" in body.replace("<!--", ""):
        return False  # a DOCTYPE or an entity: not needed by a drawing
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return False
    if root.tag != SVG + "svg":
        return False
    for element in root.iter():
        if not isinstance(element.tag, str) or not element.tag.startswith(SVG):
            return False
        if element.tag[len(SVG) :] not in DRAWING:
            return False
        for name, value in element.attrib.items():
            name = name.rsplit("}", 1)[-1].lower()
            if name.startswith("on") or name == "style":
                return False  # colours are given as attributes, CSS is not read
            if "\\" in value:
                return False  # a CSS escape can hide an address
            if name == "href" and not value.strip().startswith("#"):
                return False
            if OUTSIDE_RE.search(value):
                return False
    return True


def publishable(path: str, image: bytes) -> bool:
    return bool(image) and (not path.lower().endswith(".svg") or plain_drawing(image))
