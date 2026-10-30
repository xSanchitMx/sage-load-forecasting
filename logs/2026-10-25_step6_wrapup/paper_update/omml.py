"""Tiny LaTeX-subset -> OMML (Word equation) converter for the paper update."""
import re
from lxml import etree

MNS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XMLNS = "http://www.w3.org/XML/1998/namespace"


def m(tag, parent=None):
    el = etree.Element(f"{{{MNS}}}{tag}") if parent is None else etree.SubElement(parent, f"{{{MNS}}}{tag}")
    return el


def _wrpr(parent):
    rpr = etree.SubElement(parent, f"{{{WNS}}}rPr")
    f = etree.SubElement(rpr, f"{{{WNS}}}rFonts")
    f.set(f"{{{WNS}}}ascii", "Cambria Math"); f.set(f"{{{WNS}}}hAnsi", "Cambria Math")
    return rpr


def run(text, style="i"):
    """style: i (italic math), p (upright), nor (normal text)."""
    r = m("r")
    if style == "nor":
        rp = m("rPr", r); m("nor", rp)
    elif style == "p":
        rp = m("rPr", r); s = m("sty", rp); s.set(f"{{{MNS}}}val", "p")
    _wrpr(r)
    t = m("t", r); t.text = text
    if text != text.strip() or " " in text:
        t.set(f"{{{XMLNS}}}space", "preserve")
    return r


def _ctrl(pr):
    c = m("ctrlPr", pr); _wrpr(c)


GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "varepsilon": "ε", "epsilon": "ϵ",
         "theta": "θ", "lambda": "λ", "mu": "μ", "pi": "π", "sigma": "σ", "tau": "τ", "omega": "ω",
         "ell": "ℓ", "Phi": "Φ", "Theta": "Θ"}
SYMS = {"top": "⊤", "leftarrow": "←", "in": "∈", "dots": "…", "cdot": "·", "le": "≤", "ge": "≥",
        "times": "×", "infty": "∞", "quad": " ", ",": " ", "{": "{", "}": "}", "mid": "|",
        " ": "\u2005", "approx": "≈", "neq": "≠", "to": "→", "pm": "±", "lbrace": "{", "rbrace": "}"}
FUNCS = {"exp", "min", "max", "arg", "ln", "log", "argmin"}
ACCENTS = {"hat": "̂", "tilde": "̃", "bar": "̅"}

TOK = re.compile(r"\\[a-zA-Z]+|\\.|[{}_^]|\s+|.")


class Parser:
    def __init__(self, src):
        self.t = [x for x in TOK.findall(src)]
        self.i = 0

    def peek(self):
        while self.i < len(self.t) and self.t[self.i].isspace():
            self.i += 1
        return self.t[self.i] if self.i < len(self.t) else None

    def next(self):
        tok = self.peek(); self.i += 1; return tok

    def group(self):
        if self.peek() == "{":
            self.next(); seq = self.seq("}"); self.next(); return seq
        return self.atom_list()

    def atom_list(self):
        a = self.atom()
        return a if isinstance(a, list) else [a]

    def raw_group(self):
        assert self.next() == "{"
        depth, out = 1, ""
        while True:
            tk = self.t[self.i]; self.i += 1
            if tk == "{": depth += 1
            elif tk == "}":
                depth -= 1
                if depth == 0: return out
            out += tk

    def seq(self, stop=None):
        items = []
        while self.peek() is not None and self.peek() != stop:
            tk = self.peek()
            if tk == "\\sum":
                self.next()
                sub = sup = None
                while self.peek() in ("_", "^"):
                    if self.next() == "_": sub = self.group()
                    else: sup = self.group()
                body = self.seq(stop)
                items.append(nary("∑", sub, sup, body))
                break
            items.append(self.script(self.atom()))
        return items

    def atom(self):
        tk = self.next()
        if tk == "{":
            s = self.seq("}"); self.next(); return s
        if tk == "\\frac":
            return frac(self.group(), self.group())
        if tk[1:] in ACCENTS and tk.startswith("\\"):
            return acc(ACCENTS[tk[1:]], self.group())
        if tk == "\\text":
            return run(self.raw_group(), "nor")
        if tk in ("\\left", "\\right"):
            return self.atom()
        if tk.startswith("\\"):
            name = tk[1:]
            if name in GREEK: return run(GREEK[name], "i")
            if name in SYMS: return run(SYMS[name], "p")
            if name in FUNCS: return run("arg min" if name == "argmin" else name, "p")
            raise ValueError(f"unknown command {tk}")
        if tk.isalpha():
            return run(tk, "i")
        return run(tk, "p")

    def script(self, base):
        sub = sup = None
        while self.peek() in ("_", "^"):
            if self.next() == "_": sub = self.group()
            else: sup = self.group()
        if sub is None and sup is None:
            return base
        b = base if isinstance(base, list) else [base]
        if sub is not None and sup is not None:
            el = m("sSubSup"); _ctrl(m("sSubSupPr", el))
            _fill(m("e", el), b); _fill(m("sub", el), sub); _fill(m("sup", el), sup); return el
        if sub is not None:
            el = m("sSub"); _ctrl(m("sSubPr", el)); _fill(m("e", el), b); _fill(m("sub", el), sub); return el
        el = m("sSup"); _ctrl(m("sSupPr", el)); _fill(m("e", el), b); _fill(m("sup", el), sup); return el


def _fill(parent, items):
    for it in (items if isinstance(items, list) else [items]):
        if isinstance(it, list):
            _fill(parent, it)
        else:
            parent.append(it)


def frac(a, b):
    el = m("f"); _ctrl(m("fPr", el)); _fill(m("num", el), a); _fill(m("den", el), b); return el


def acc(ch, a):
    el = m("acc"); pr = m("accPr", el); c = m("chr", pr); c.set(f"{{{MNS}}}val", ch); _ctrl(pr)
    _fill(m("e", el), a); return el


def nary(ch, sub, sup, body):
    el = m("nary"); pr = m("naryPr", el)
    c = m("chr", pr); c.set(f"{{{MNS}}}val", ch)
    ll = m("limLoc", pr); ll.set(f"{{{MNS}}}val", "undOvr")
    if sub is None:
        h = m("subHide", pr); h.set(f"{{{MNS}}}val", "1")
    if sup is None:
        h = m("supHide", pr); h.set(f"{{{MNS}}}val", "1")
    _ctrl(pr)
    _fill(m("sub", el), sub or []); _fill(m("sup", el), sup or []); _fill(m("e", el), body)
    return el


def omath(src):
    om = m("oMath")
    _fill(om, Parser(src).seq())
    return om
