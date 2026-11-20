import pytest

from ai_disclosure.logo import plain_drawing, publishable

NS = 'xmlns="http://www.w3.org/2000/svg"'


def test_a_drawing_is_published():
    image = f"""<svg {NS} viewBox="0 0 10 10">
      <!-- a comment -->
      <defs><linearGradient id="g"><stop offset="0%" stop-color="#fff"/></linearGradient></defs>
      <g transform="rotate(-25)"><path d="M0 0L5 5" stroke="url(#g)"/></g>
      <circle cx="5" cy="5" r="2" fill="#F4F7FF"/>
    </svg>"""
    assert plain_drawing(image.encode())


@pytest.mark.parametrize(
    "inside",
    [
        "<script>alert(1)</script>",
        '<circle r="1" onclick="alert(1)"/>',
        '<a href="https://example.org"><circle r="1"/></a>',
        '<use href="https://example.org/a.svg#x"/>',
        '<image href="https://example.org/a.png"/>',
        "<style>circle { fill: red }</style>",
        '<foreignObject><p xmlns="http://www.w3.org/1999/xhtml">x</p></foreignObject>',
        '<circle r="1" fill="url(https://example.org/a.svg#g)"/>',
        '<circle r="1" style="background: url(\'https://example.org\')"/>',
        '<animate attributeName="r" to="5"/>',
        '<p xmlns="http://www.w3.org/1999/xhtml">x</p>',
    ],
)
def test_more_than_a_drawing_is_refused(inside):
    assert not plain_drawing(f"<svg {NS}>{inside}</svg>".encode())


def test_what_is_not_an_svg_drawing_is_refused():
    assert not plain_drawing(b"<html><body/></html>")
    assert not plain_drawing(b"not xml")
    assert not plain_drawing(f'<!DOCTYPE svg [<!ENTITY a "b">]><svg {NS}/>'.encode())


def test_a_bitmap_is_published_as_it_is():
    assert publishable("logo.png", b"\x89PNG")
    assert not publishable("logo.png", b"")
    assert not publishable("logo.SVG", b"<svg><script/></svg>")
