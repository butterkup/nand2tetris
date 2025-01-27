import typing

from .lexer import Lexer, Token, segment_specs

type Statement = tuple[Token, ...]
push_segment_specs = segment_specs
pop_segment_specs = segment_specs - {Token.Type.CONSTANT}


class Parser:
    __slots__ = "lexer", "stash", "_empty", "labels", "resolve_gotos"

    def __init__(self, lexer: Lexer) -> None:
        self.lexer = lexer
        self.stash: list[Token] = []
        self._empty = False
        self.labels: dict[str, int] = {}
        self.resolve_gotos: dict[str, int] = {}

    reset = __init__

    def get(self) -> Token | None:
        tk = self.stash.pop() if self.stash else self.lexer.lex()
        self._empty = tk is None
        return tk

    def push(self, tk: Token):
        self.stash.append(tk)

    def empty(self) -> bool:
        return bool(self.stash) or self._empty

    def match(self, typ: Token.Type):
        tk = self.get()
        if tk is None:
            return
        if tk.typ == typ:
            return tk
        self.push(tk)

    def expect(self, line: int, typs: Token.Type | typing.Container[Token.Type]):
        typs = (typs,) if isinstance(typs, Token.Type) else typs
        tk = self.get()
        if tk is None or tk.typ not in typs:
            raise Exception(
                f"Line {line}: Expected one of {typs} but got {tk.typ if tk else 'EOF'}"
            )
        return tk

    def push_stmt(self, tk: Token, segspecs: typing.Container[Token.Type]):
        if func := self.match(Token.Type.ID):
            return self.make_stmt(tk, func)
        return self.push_pop_stmt(tk, segspecs)

    def push_pop_stmt(
        self, tk: Token, segspecs: typing.Container[Token.Type]
    ) -> Statement:
        segment = self.expect(tk.line, segspecs)
        index = self.expect(tk.line, Token.Type.INT)
        return self.make_stmt(tk, segment, index)

    def make_stmt(self, *tokens: Token) -> Statement:
        assert tokens, "Empty statement passed in Parser.make_stmt"
        eos = self.get()
        if eos is None or eos.typ == Token.Type.EOS:
            return tokens
        line = tokens[0].line
        stmt = " ".join(map(lambda tk: tk.lexeme, tokens))
        raise Exception(
            f"Line {line}: Expected one of [EOF, NEWLINE] at the end of statement {stmt!r}"
        )

    def register_label(self, label: Token):
        if seen := self.labels.get(label.lexeme):
            raise Exception(f"Line {label.line}: Label already declared in line {seen}")
        if label.lexeme in self.resolve_gotos:
            del self.resolve_gotos[label.lexeme]
        self.labels[label.lexeme] = label.line

    def resolve_goto_label(self, label: Token):
        if label.lexeme not in self.labels:
            self.resolve_gotos[label.lexeme] = label.line

    def report_unresolved_gotos(self):
        if self.resolve_gotos:
            raise Exception(
                "\n".join(
                    f"Goto label {label!r} referenced on line {line} was not found."
                    for label, line in self.resolve_gotos.items()
                )
            )

    def parse(self) -> Statement | None:
        T = Token.Type
        while tk := self.get():
            match tk.typ:
                case T.EOS:
                    ...
                case (
                    T.AND
                    | T.ADD
                    | T.SUB
                    | T.NEG
                    | T.OR
                    | T.NOT
                    | T.EQ
                    | T.GT
                    | T.LT
                    | T.RETURN
                ):
                    return self.make_stmt(tk)
                case T.PUSH:
                    return self.push_stmt(tk, push_segment_specs)
                case T.POP:
                    return self.push_pop_stmt(tk, pop_segment_specs)
                case T.LABEL:
                    label = self.expect(tk.line, Token.Type.ID)
                    self.register_label(label)
                    return self.make_stmt(tk, label)
                case T.CALL:
                    label = self.match(Token.Type.ID)
                    nvars = self.expect(tk.line, Token.Type.INT)
                    if label is None:
                        return self.make_stmt(tk, nvars)
                    return self.make_stmt(tk, label, nvars)
                case T.FUNCTION:
                    label = self.expect(tk.line, Token.Type.ID)
                    nvars = self.expect(tk.line, Token.Type.INT)
                    return self.make_stmt(tk, label, nvars)
                case T.IF_GOTO | T.GOTO:
                    label = self.expect(tk.line, Token.Type.ID)
                    self.resolve_goto_label(label)
                    return self.make_stmt(tk, label)
                case _:
                    raise Exception(f"Line {tk.line}: Unexpected token {tk}")
        self.report_unresolved_gotos()

    def __iter__(self):
        return self

    def __next__(self) -> Statement:
        stmt = self.parse()
        if stmt is None:
            raise StopIteration
        return stmt
