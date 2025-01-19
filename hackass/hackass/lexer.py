import enum
import dataclasses as dt
from .codes import JumpCodes


@dt.dataclass(slots=True)
class Token:
    class Type(enum.IntEnum):
        A = enum.auto()
        D = enum.auto()
        M = enum.auto()
        INT = enum.auto()
        K0 = enum.auto()
        K1 = enum.auto()
        ID = enum.auto()
        DASH = enum.auto()
        PLUS = enum.auto()
        NOT = enum.auto()
        ASSIGN = enum.auto()
        SEMI = enum.auto()
        LABEL = enum.auto()
        EOS = enum.auto()
        JUMP = enum.auto()
        OR = enum.auto()
        AND = enum.auto()

    lexeme: str
    typ: Type
    line: int


class Lexer:
    def __init__(self, program: str):
        self.prog = program
        self.end = len(program)
        self.curr = 0
        self.start = 0
        self.line = 1
        self.labels: set[str] = set()

    reset = __init__

    def empty(self) -> bool:
        return self.curr >= self.end

    def get(self) -> str:
        return self.prog[self.curr]

    def consume(self):
        self.start = self.curr

    def advance(self):
        self.curr += 1

    def lexeme(self):
        return self.prog[self.start : self.curr]

    def make_token(self, typ: Token.Type):
        lexeme = self.lexeme()
        self.consume()
        return Token(lexeme, typ, self.line)

    def consume_number(self):
        while not self.empty():
            char = self.get()
            if not char.isdigit():
                break
            self.advance()
        lexeme = self.lexeme()
        self.consume()
        return lexeme

    def consume_id(self):
        while not self.empty():
            char = self.get()
            if not (char.isalnum() or char in "$.:_"):
                break
            self.advance()
        return self.make_token(Token.Type.ID)

    def discard_comment(self):
        while not self.empty():
            if self.get() == "\n":
                break
            self.advance()
        self.consume()

    def a_instruction(self):
        self.advance()
        self.consume()
        if self.empty():
            raise Exception(
                "Line", self.line, ":Expected anargument for the A-instruction after @"
            )
        if self.get().isdigit():
            number = int(self.consume_number())
            if number > 0x7FFF:
                raise Exception(f"Expected an integer <={0x7fff} for the A-instruction")
            return Token(format(number, "b").rjust(15, "0"), Token.Type.INT, self.line)
        return self.consume_id()

    def label_symbol(self):
        self.advance()
        self.consume()
        if self.empty():
            raise Exception("Line", self.line, ":Expected ID after (")
        char = self.get()
        if char.isdigit():
            raise Exception("Line", self.line, ":ID cannot start with a digit")
        id = self.consume_id()
        if not id.lexeme:
            raise Exception("Line", self.line, ":Expected ID after (:", id)
        if self.empty() or self.get() != ")":
            raise Exception("Line", self.line, ":Missing closing ) to match opened (")
        self.advance()
        self.consume()
        if id.lexeme in self.labels:
            raise Exception("Line", self.line, ":Label redeclared:", id.lexeme)
        else:
            self.labels.add(id.lexeme)
        id.typ = Token.Type.LABEL
        return id

    def make_ctoken(self, typ: Token.Type):
        self.advance()
        return self.make_token(typ)

    def match(self, char: str):
        if self.get() == char:
            self.advance()
            return True
        return False

    def match_next(self, char: str):
        self.advance()
        return self.match(char)

    def safe(self, n: int):
        return n + self.curr < self.end

    def jump(self):
        self.advance()
        exp = Exception(
            "Line",
            self.line,
            ":Invalid jump spec, expected one of: JEQ, JNE, JLT, JGT, JLE, JGE, JMP",
        )
        if not self.safe(2):
            raise exp
        if self.match("E"):
            if self.match("Q"):
                target = JumpCodes.JEQ
            else:
                raise exp
        elif self.match("L"):
            if self.match("T"):
                target = JumpCodes.JLT
            elif self.match("E"):
                target = JumpCodes.JLE
            else:
                raise exp
        elif self.match("G"):
            if self.match("T"):
                target = JumpCodes.JGT
            elif self.match("E"):
                target = JumpCodes.JGE
            else:
                raise exp
        elif self.match("N"):
            if self.match("E"):
                target = JumpCodes.JNE
            else:
                raise exp
        elif self.match("M"):
            if self.match("P"):
                target = JumpCodes.JMP
            else:
                raise exp
        else:
            raise exp
        self.consume()
        return Token(target, Token.Type.JUMP, self.line)

    def lex(self) -> Token | None:
        T = Token.Type
        while not self.empty():
            char = self.get()
            match char:
                case "/":
                    self.advance()
                    if self.empty() or self.get() != "/":
                        raise Exception(
                            "Line", self.line, ":Expected / after / for comment."
                        )
                    self.discard_comment()
                case "@":
                    return self.a_instruction()
                case "(":
                    return self.label_symbol()
                case "A":
                    return self.make_ctoken(T.A)
                case "M":
                    return self.make_ctoken(T.M)
                case "D":
                    return self.make_ctoken(T.D)
                case "=":
                    return self.make_ctoken(T.ASSIGN)
                case ";":
                    return self.make_ctoken(T.SEMI)
                case "!":
                    return self.make_ctoken(T.NOT)
                case "-":
                    return self.make_ctoken(T.DASH)
                case "+":
                    return self.make_ctoken(T.PLUS)
                case "&":
                    return self.make_ctoken(T.AND)
                case "|":
                    return self.make_ctoken(T.OR)
                case " " | "\t":
                    self.advance()
                    self.consume()
                case "\n":
                    tk = self.make_ctoken(T.EOS)
                    self.line += 1
                    return tk
                case "J":
                    return self.jump()
                case "1":
                    return self.make_ctoken(T.K1)
                case "0":
                    return self.make_ctoken(T.K0)
                case _:
                    raise Exception(
                        "Line", self.line, ":Unexpected character '" + char + "'"
                    )

