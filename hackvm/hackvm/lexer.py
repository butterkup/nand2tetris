import dataclasses as dt
import enum


@dt.dataclass(slots=True)
class Token:
    class Type(enum.StrEnum):
        ID = enum.auto()
        INT = enum.auto()
        AND = enum.auto()
        OR = enum.auto()
        ADD = enum.auto()
        SUB = enum.auto()
        NEG = enum.auto()
        NOT = enum.auto()
        LT = enum.auto()
        GT = enum.auto()
        EQ = enum.auto()
        PUSH = enum.auto()
        POP = enum.auto()
        STATIC = enum.auto()
        CONSTANT = enum.auto()
        LOCAL = enum.auto()
        ARGUMENT = enum.auto()
        POINTER = enum.auto()
        THAT = enum.auto()
        TEMP = enum.auto()
        THIS = enum.auto()
        EOS = enum.auto()
        LABEL = enum.auto()
        FUNCTION = enum.auto()
        GOTO = enum.auto()
        IF_GOTO = enum.auto()
        CALL = enum.auto()
        RETURN = enum.auto()

    lexeme: str
    typ: Type
    line: int


keywords: dict[str, Token.Type] = {
    "add": Token.Type.ADD,
    "neg": Token.Type.NEG,
    "sub": Token.Type.SUB,
    "not": Token.Type.NOT,
    "or": Token.Type.OR,
    "and": Token.Type.AND,
    "lt": Token.Type.LT,
    "eq": Token.Type.EQ,
    "gt": Token.Type.GT,
    "static": Token.Type.STATIC,
    "temp": Token.Type.TEMP,
    "local": Token.Type.LOCAL,
    "argument": Token.Type.ARGUMENT,
    "constant": Token.Type.CONSTANT,
    "this": Token.Type.THIS,
    "push": Token.Type.PUSH,
    "pop": Token.Type.POP,
    "label": Token.Type.LABEL,
    "call": Token.Type.CALL,
    "function": Token.Type.FUNCTION,
    "return": Token.Type.RETURN,
    "goto": Token.Type.GOTO,
    "if-goto": Token.Type.IF_GOTO,
}

segment_specs: set[Token.Type] = {
    Token.Type.STATIC,
    Token.Type.LOCAL,
    Token.Type.THIS,
    Token.Type.ARGUMENT,
    Token.Type.THAT,
    Token.Type.POINTER,
    Token.Type.TEMP,
    Token.Type.CONSTANT,
}


class Lexer:
    def __init__(self, program: str):
        self.end: int = len(program)
        self.program = program
        self.current: int = 0
        self.start: int = 0
        self.line: int = 1

    reset = __init__

    def empty(self) -> bool:
        return self.current >= self.end

    def lexeme(self) -> str:
        return self.program[self.start : self.current]

    def peek(self) -> str:
        return self.program[self.current]

    def advance(self):
        self.current += 1

    def consume(self):
        self.start = self.current

    def match(self, char: str) -> bool:
        if not self.empty() and self.peek() == char:
            self.advance()
            return True
        return False

    def make_token(self, typ: Token.Type) -> Token:
        lexeme = self.lexeme()
        self.consume()
        return Token(lexeme, typ, self.line)

    def make_ctoken(self, typ: Token.Type):
        self.advance()
        return self.make_token(typ)

    @staticmethod
    def isidch(char: str) -> bool:
        return char.isalnum() or char in "._-"

    def consume_id(self):
        while not self.empty():
            char = self.peek()
            if not self.isidch(char):
                break
            self.advance()
        typ = keywords.get(self.lexeme(), Token.Type.ID)
        return self.make_token(typ)

    def consume_int(self):
        while not self.empty():
            if not self.peek().isdigit():
                break
            self.advance()
        if int(literal := self.lexeme()) > 0x7FFF:
            self.report(f"Integer literal {literal!r} surpasses {0x7fff}")
        return self.make_token(Token.Type.INT)

    def consume_comment(self):
        while not self.empty():
            if self.peek() == "\n":
                break
            self.advance()
        self.consume()

    def report(self, err: str):
        raise Exception(f"Line {self.line}: {err}")

    def lex(self) -> Token | None:
        T = Token.Type
        while not self.empty():
            char = self.peek()
            match char:
                case "/":
                    if self.match("/"):
                        self.consume_comment()
                    else:
                        self.report("Expected pair // but found a lonely /")
                case "\n":
                    self.line += 1
                    return self.make_ctoken(T.EOS)
                case " " | "\t":
                    while not self.empty():
                        if self.peek() not in " \t":
                            break
                        self.advance()
                    self.consume()
                case _:
                    if char.isdigit():
                        return self.consume_int()
                    elif self.isidch(char):
                        return self.consume_id()
                    self.report(f"Unexpected character {char!r}")

    def __iter__(self):
        return self

    def __next__(self) -> Token:
        tk = self.lex()
        if tk is None:
            raise StopIteration
        return tk
