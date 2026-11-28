import html
import re
from html.parser import HTMLParser
import unicodedata

INSTRUCTION = re.compile(
    r"ignore\s+(?:all\s+)?(?:previous|prior)\s+instructions|(?:^|\s)(?:system|assistant|developer)\s*:|<\|[^>]+\|>|</?(?:tool_call|untrusted_data)\b|\b(?:tool_call|function_call)\s*[:(]",
    re.I,
)


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        if (
            tag in {"script", "style", "template", "noscript"}
            or "hidden" in attr
            or "display:none" in (attr.get("style") or "").replace(" ", "").lower()
        ):
            self.hidden.append(tag)

    def handle_endtag(self, tag):
        if self.hidden and self.hidden[-1] == tag:
            self.hidden.pop()

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean(raw):
    visible = "".join(ch for ch in raw if unicodedata.category(ch) != "Cf")
    suspect = visible != raw or bool(INSTRUCTION.search(html.unescape(visible)))
    parser = VisibleText()
    parser.feed(visible)
    text = " ".join(" ".join(parser.parts).split())
    if suspect or INSTRUCTION.search(text):
        return "[instruction-like content removed]", True
    return text, False


def wrapped(value, source):
    return f'<untrusted_data source="{html.escape(source, quote=True)}">{html.escape(value)}</untrusted_data>'
