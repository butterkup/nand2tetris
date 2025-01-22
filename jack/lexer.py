import typing

from .token import KEYWORDS, Token


class _Lexer_helper:
    "One time use object. Do not modify any state, very sensitive."
    __slots__ = (
        "program",
        "lex_off",
        "lex_lineno",
        "lex_column",
        "offset",
        "lineoff",
        "lineno",
    )

    def __init__(self, program: str):
        self.program = program
        self.lex_off = 0
        self.lex_lineno = 0
        self.lex_column = 0
        self.offset = 0
        self.lineoff = 0
        self.lineno = 1

    def empty(self) -> bool:
        return self.offset == len(self.program)

    __bool__ = empty

    def lexeme(self) -> str:
        return self.program[self.lex_off : self.offset]

    def curloc(self) -> Token.Loc:
        return Token.Loc(
            line=self.lineno, col=self.offset - self.lineoff, off=self.offset
        )

    def lexloc(self) -> Token.Loc:
        return Token.Loc(line=self.lex_lineno, col=self.lex_column, off=self.lex_off)

    def consume(self):
        self.lex_off = self.offset
        self.lex_column = self.offset - self.lineoff
        self.lex_lineno = self.lineno

    def make_token(self, typ: Token.Type) -> Token:
        start = self.lexloc()
        end = self.curloc()
        lexeme = self.lexeme()
        self.consume()
        return Token(typ=typ, start=start, end=end, lexeme=lexeme)

    def peek(self) -> str:
        return self.program[self.offset]

    def advance(self, ignore_line: bool = False):
        curr = self.peek()
        self.offset += 1
        if not ignore_line and curr == "\n":
            self.lineoff = self.offset
            self.lineno += 1

    def report(self, err: str, loc: Token.Loc | None = None):
        loc = self.curloc() if loc is None else loc
        raise Exception(f"{loc}: {err}")

    def consume_string(self) -> Token:
        self.advance()
        while not self.empty():
            char = self.peek()
            if char == '"':
                break
            self.advance()
        else:
            self.report("Unterminated string literal.", self.lexloc())
        self.advance()
        return self.make_token(Token.Type.STRING)

    def isidch(self):
        ch = self.peek()
        return ch.isalnum() or ch == "_"

    def consume_id(self) -> Token:
        while not self.empty():
            if not self.isidch():
                break
            self.advance()
        typ = KEYWORDS.get(self.lexeme(), Token.Type.ID)
        return self.make_token(typ)

    def consume_int(self) -> Token:
        while not self.empty():
            ch = self.peek()
            if ch.isdigit():
                self.advance()
            elif ch.isalpha():
                self.report(f"Expected a digit, got {self.peek()}")
            else:
                break
        return self.make_token(Token.Type.INT)

    def make_ctoken(self, typ: Token.Type) -> Token:
        self.advance()
        return self.make_token(typ)

    def match(self, char: str):
        if not self.empty() and self.peek() == char:
            self.advance()
            return True

    def match_nxt(self, char: str):
        self.advance()
        return self.match(char)

    def consume_multi_comment(self):
        while not self.empty():
            if self.peek() == "*" and self.match_nxt("/"):
                break
            self.advance()
        else:
            self.report("Unterminated comment.", self.lexloc())
        self.consume()

    def consume_single_comment(self):
        while not self.empty():
            if self.peek() == "\n":
                break
            self.advance()
        self.consume()

    def consume_spaces(self, spaces: str):
        while not self.empty():
            if self.peek() not in spaces:
                break
            self.advance()
        self.consume()

    def lex(self) -> Token:
        T = Token.Type
        while not self.empty():
            match self.peek():
                case '"':
                    return self.consume_string()
                case "+":
                    return self.make_ctoken(T.PLUS)
                case ".":
                    return self.make_ctoken(T.DOT)
                case "/":
                    self.advance()
                    if self.match("/"):
                        self.consume_single_comment()
                    elif self.match("*"):
                        self.consume_multi_comment()
                    else:
                        return self.make_token(T.SLASH)
                case "*":
                    return self.make_ctoken(T.STAR)
                case "-":
                    return self.make_ctoken(T.MINUS)
                case "[":
                    return self.make_ctoken(T.LBRACKET)
                case "]":
                    return self.make_ctoken(T.RBRACKET)
                case "(":
                    return self.make_ctoken(T.LPAREN)
                case ")":
                    return self.make_ctoken(T.RPAREN)
                case "{":
                    return self.make_ctoken(T.LBRACE)
                case "}":
                    return self.make_ctoken(T.RBRACE)
                case "~":
                    return self.make_ctoken(T.TILDE)
                case ":":
                    return self.make_ctoken(T.COLON)
                case ";":
                    return self.make_ctoken(T.SCOLON)
                case ",":
                    return self.make_ctoken(T.COMMA)
                case "|":
                    return self.make_token(T.OR if self.match_nxt("|") else T.BAR)
                case "&":
                    return self.make_token(T.AND if self.match_nxt("&") else T.AMP)
                case "=":
                    return self.make_token(T.EQUAL if self.match_nxt("=") else T.ASSIGN)
                case "<":
                    return self.make_token(T.LESSE if self.match_nxt("=") else T.LESS)
                case ">":
                    return self.make_token(T.GREATE if self.match_nxt("=") else T.GREAT)
                case "!":
                    return self.make_token(T.NEQUAL if self.match_nxt("=") else T.NOT)
                case " " | "\t" | "\n":
                    self.consume_spaces(" \t\n")
                case char:
                    if char.isdigit():
                        return self.consume_int()
                    if self.isidch():
                        return self.consume_id()
                    self.report(f"Unrecognized character {char!r}")
        return self.make_token(T.EOT)


def Lexer(program: str) -> typing.Generator[Token, None, None]:
    "Actual Lexer, simply a generator that hides all nuances of the actual lexer."
    lexer = _Lexer_helper(program)
    while True:
        tk = lexer.lex()
        yield tk
        if tk.typ == Token.Type.EOT:
            return

