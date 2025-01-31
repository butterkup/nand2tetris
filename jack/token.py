import dataclasses as dt
import enum


@dt.dataclass(slots=True)
class Token:
    class Type(enum.StrEnum):
        # Keywords
        STRUCT = enum.auto()
        BREAK = enum.auto()
        CONTINUE = enum.auto()
        RETURN = enum.auto()
        FN = enum.auto()
        FOR = enum.auto()
        WHILE = enum.auto()
        ASSIGN = enum.auto()
        IF = enum.auto()
        ELSE = enum.auto()
        USE = enum.auto()

        # Symbols
        LBRACE = enum.auto()
        RBRACE = enum.auto()
        LPAREN = enum.auto()
        RPAREN = enum.auto()
        LBRACKET = enum.auto()
        RBRACKET = enum.auto()
        COMMA = enum.auto()
        SCOLON = enum.auto()
        COLON = enum.auto()
        SCOPE = enum.auto()
        #  End Of Token stream marker
        EOT = enum.auto()

        # Primaries
        #  Keywords
        NIL = enum.auto()
        TRUE = enum.auto()
        FALSE = enum.auto()
        #  Values
        ID = enum.auto()
        INT = enum.auto()
        STRING = enum.auto()

        # Operators
        DOT = enum.auto()
        EQUAL = enum.auto()
        NEQUAL = enum.auto()
        LESST = enum.auto()
        LESSE = enum.auto()
        GREATT = enum.auto()
        GREATE = enum.auto()
        AND = enum.auto()
        OR = enum.auto()
        NOT = enum.auto()
        AMP = enum.auto()
        BAR = enum.auto()
        TILDE = enum.auto()
        PLUS = enum.auto()
        MINUS = enum.auto()
        STAR = enum.auto()
        SLASH = enum.auto()

    @dt.dataclass(slots=True)
    class Loc:
        line: int
        col: int
        off: int = dt.field(repr=False)

    typ: Type
    start: Loc
    end: Loc
    lexeme: str


KEYWORDS: dict[str, Token.Type] = {
    "struct": Token.Type.STRUCT,
    "fn": Token.Type.FN,
    "for": Token.Type.FOR,
    "while": Token.Type.WHILE,
    "if": Token.Type.IF,
    "else": Token.Type.ELSE,
    "true": Token.Type.TRUE,
    "false": Token.Type.FALSE,
    "use": Token.Type.USE,
    "return": Token.Type.RETURN,
    "break": Token.Type.BREAK,
    "continue": Token.Type.CONTINUE,
    "nil": Token.Type.NIL,
}
