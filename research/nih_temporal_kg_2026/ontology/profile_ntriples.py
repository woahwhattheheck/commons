from __future__ import annotations

try:  # package import
    from .profile_vocab import *
except ImportError:  # direct script / cwd import
    from profile_vocab import *

def _escape_literal(value: str) -> str:
    out: list[str] = []
    for char in value:
        code = ord(char)
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append('\\"')
        elif char == "\t":
            out.append("\\t")
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\b":
            out.append("\\b")
        elif char == "\f":
            out.append("\\f")
        elif 0x20 <= code <= 0x7E:
            out.append(char)
        elif code <= 0xFFFF:
            if 0xD800 <= code <= 0xDFFF:
                raise OntologyProfileError("surrogate code points are forbidden")
            out.append(f"\\u{code:04X}")
        elif code <= 0x10FFFF:
            out.append(f"\\U{code:08X}")
        else:  # pragma: no cover - Python strings cannot exceed Unicode max
            raise OntologyProfileError("invalid Unicode scalar")
    return "".join(out)


def _unescape_literal(value: str) -> str:
    out: list[str] = []
    index = 0
    simple = {'t': "\t", 'n': "\n", 'r': "\r", 'b': "\b", 'f': "\f", '"': '"', '\\': '\\'}
    while index < len(value):
        char = value[index]
        if char != "\\":
            if ord(char) < 0x20:
                raise OntologyProfileError("raw control character in literal")
            out.append(char)
            index += 1
            continue
        index += 1
        if index >= len(value):
            raise OntologyProfileError("truncated literal escape")
        marker = value[index]
        if marker in simple:
            out.append(simple[marker])
            index += 1
            continue
        if marker in {"u", "U"}:
            width = 4 if marker == "u" else 8
            digits = value[index + 1:index + 1 + width]
            if len(digits) != width or not re.fullmatch(r"[0-9A-F]{%d}" % width, digits):
                raise OntologyProfileError("Unicode escapes must be uppercase fixed-width hex")
            code = int(digits, 16)
            if code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
                raise OntologyProfileError("invalid Unicode scalar escape")
            out.append(chr(code))
            index += 1 + width
            continue
        raise OntologyProfileError(f"unknown literal escape \\{marker}")
    decoded = "".join(out)
    if _escape_literal(decoded) != value:
        raise OntologyProfileError("literal escape form is not canonical")
    return decoded


def iri(value: str) -> Term:
    return Term("iri", _validate_iri(value), None)


def literal(value: str, datatype: str = XSD_STRING) -> Term:
    if not isinstance(value, str):
        raise OntologyProfileError("literal value must be a string")
    return Term("literal", value, _validate_iri(datatype))


def _render_term(term: Term) -> str:
    if term.kind == "iri":
        if term.datatype is not None:
            raise OntologyProfileError("IRI term must not carry datatype")
        return f"<{_validate_iri(term.value)}>"
    if term.kind == "literal":
        if term.datatype is None:
            raise OntologyProfileError("profile literals require explicit datatype")
        return f'"{_escape_literal(term.value)}"^^<{_validate_iri(term.datatype)}>'
    raise OntologyProfileError("unknown RDF term kind")


def _render_triple(triple: Triple) -> str:
    return f"<{_validate_iri(triple.subject)}> <{_validate_iri(triple.predicate)}> {_render_term(triple.object)} ."


def _parse_object(raw: str) -> Term:
    if raw.startswith("<"):
        if not raw.endswith(">") or raw.count("<") != 1 or raw.count(">") != 1:
            raise OntologyProfileError("malformed IRI object")
        return iri(raw[1:-1])
    if not raw.startswith('"'):
        if raw.startswith("_:"):
            raise OntologyProfileError("blank nodes are forbidden")
        raise OntologyProfileError("profile object must be an IRI or typed literal")
    index = 1
    escaped = False
    closing = -1
    while index < len(raw):
        char = raw[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            closing = index
            break
        index += 1
    if closing < 0:
        raise OntologyProfileError("unterminated literal")
    suffix = raw[closing + 1:]
    if not suffix.startswith("^^<") or not suffix.endswith(">"):
        raise OntologyProfileError("profile literals require one explicit datatype")
    datatype = _validate_iri(suffix[3:-1])
    value = _unescape_literal(raw[1:closing])
    term = literal(value, datatype)
    if _render_term(term) != raw:
        raise OntologyProfileError("literal serialization is not canonical")
    return term


def parse_ntriples(text: str) -> tuple[Triple, ...]:
    if not isinstance(text, str):
        raise OntologyProfileError("N-Triples input must be text")
    if not text or not text.endswith("\n"):
        raise OntologyProfileError("N-Triples must be nonempty and end with one newline")
    if "\r" in text:
        raise OntologyProfileError("N-Triples must use LF line endings")
    lines = text.splitlines()
    if any(not line for line in lines):
        raise OntologyProfileError("blank lines are forbidden")
    if lines != sorted(lines):
        raise OntologyProfileError("N-Triples lines must be lexicographically sorted")
    if len(lines) != len(set(lines)):
        raise OntologyProfileError("duplicate triples are forbidden")
    triples: list[Triple] = []
    for line_no, line in enumerate(lines, start=1):
        match = re.fullmatch(r"<([^>]*)> <([^>]*)> (.+) \.", line)
        if match is None:
            raise OntologyProfileError(f"line {line_no}: noncanonical N-Triples syntax")
        subject = _validate_iri(match.group(1))
        predicate = _validate_iri(match.group(2))
        object_term = _parse_object(match.group(3))
        triple = Triple(subject, predicate, object_term)
        if _render_triple(triple) != line:
            raise OntologyProfileError(f"line {line_no}: serialization is not canonical")
        triples.append(triple)
    return tuple(triples)


def render_ntriples(triples: Iterable[Triple]) -> str:
    lines = sorted({_render_triple(triple) for triple in triples})
    if not lines:
        raise OntologyProfileError("profile graph must not be empty")
    return "\n".join(lines) + "\n"


def _t(subject: str, predicate: str, object_term: Term) -> Triple:
    return Triple(_validate_iri(subject), _validate_iri(predicate), object_term)


def _type(subject: str, class_iri: str) -> Triple:
    return _t(subject, RDF_TYPE, iri(class_iri))

__all__ = tuple(name for name in globals() if not name.startswith("__"))
