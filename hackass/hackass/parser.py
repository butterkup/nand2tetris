import typing

from .codes import CompCodes, DestCodes, JumpCodes
from .lexer import Lexer, Token
from .utils import AInstruction, CInstruction, EOSsentinel, EOSsentinelType


class Parser:
    class _State:
        def __init__(self, lexer: Lexer):
            self._empty = False
            self.lexer = lexer
            self.stash: list[Token] = []

        def get(self) -> Token | None:
            tk = self.stash.pop() if self.stash else self.lexer.lex()
            self._empty = tk is None
            return tk

        def put(self, tk: Token):
            self.stash.append(tk)

        def empty(self):
            return self.stash or self._empty

    def __init__(self, lexer: Lexer):
        self.src = Parser._State(lexer)
        self.count = 0
        self.eos = EOSsentinel
        self.line = -1
        self.labels: dict[str, int] = {}

    reset = __init__

    def match(self, typ: Token.Type):
        tk = self.src.get()
        if tk is not None:
            if tk.typ == typ:
                return tk
            self.src.put(tk)

    def _parse(self):
        T = Token.Type
        tk = self.src.get()
        if tk is None:
            return
        self.line = tk.line
        match tk.typ:
            case T.K0:
                return CompCodes.ZERO
            case T.K1:
                return CompCodes.ONE
            case T.DASH:
                if self.match(T.K1):
                    return CompCodes.NEG_ONE
                elif self.match(T.A):
                    return CompCodes.NEG_A
                elif self.match(T.D):
                    return CompCodes.NEG_D
                elif self.match(T.M):
                    return CompCodes.NEG_M
                raise Exception(
                    "Line:", tk.line, "Expected 1 or A or M or D after unary -"
                )
            case T.NOT:
                if self.match(T.D):
                    return CompCodes.NOT_D
                elif self.match(T.A):
                    return CompCodes.NOT_A
                elif self.match(T.M):
                    return CompCodes.NOT_M
                raise Exception("Line:", tk.line, "Expected A or D or M after !")
            case T.A:
                if self.match(T.D):
                    if self.match(T.M):
                        if self.match(T.ASSIGN):
                            return DestCodes.ADM
                        raise Exception("Line:", tk.line, "Expected = after ADM")
                    if self.match(T.ASSIGN):
                        return DestCodes.AD
                    raise Exception("Line:", tk.line, "Expected = after AD")
                if self.match(T.M):
                    if self.match(T.ASSIGN):
                        return DestCodes.AM
                    raise Exception("Line:", tk.line, "Expected = after AM")
                elif self.match(T.ASSIGN):
                    return DestCodes.A
                elif self.match(T.PLUS):
                    if self.match(T.K1):
                        return CompCodes.ApONE
                    raise Exception("Line:", tk.line, "Expected 1 after A+")
                elif self.match(T.DASH):
                    if self.match(T.K1):
                        return CompCodes.AmONE
                    elif self.match(T.D):
                        return CompCodes.AmD
                    raise Exception("Line:", tk.line, "Expected 1 or D after A-")
                else:
                    return CompCodes.A
            case T.D:
                if self.match(T.M):
                    if self.match(T.ASSIGN):
                        return DestCodes.DM
                    raise Exception("Line:", tk.line, "Expected = after DM")
                elif self.match(T.ASSIGN):
                    return DestCodes.D
                elif self.match(T.PLUS):
                    if self.match(T.K1):
                        return CompCodes.DpONE
                    elif self.match(T.A):
                        return CompCodes.DpA
                    elif self.match(T.M):
                        return CompCodes.DpM
                    raise Exception("Line:", tk.line, "Expcted 1 or A or M after D+")
                elif self.match(T.DASH):
                    if self.match(T.K1):
                        return CompCodes.DmONE
                    elif self.match(T.A):
                        return CompCodes.DmA
                    elif self.match(T.M):
                        return CompCodes.DmM
                    raise Exception("Line:", tk.line, "Expected 1 or A or M after D-")
                elif self.match(T.AND):
                    if self.match(T.A):
                        return CompCodes.DaA
                    elif self.match(T.M):
                        return CompCodes.DaM
                    raise Exception("Line:", tk.line, "Expected A or M after D&")
                elif self.match(T.OR):
                    if self.match(T.A):
                        return CompCodes.DoA
                    elif self.match(T.M):
                        return CompCodes.DoM
                    raise Exception("Line:", tk.line, "Expected A or M after D|")
                else:
                    return CompCodes.D
            case T.M:
                if self.match(T.ASSIGN):
                    return DestCodes.M
                elif self.match(T.PLUS):
                    if self.match(T.K1):
                        return CompCodes.MpONE
                    raise Exception("Line:", tk.line, "Expected 1 after M+")
                elif self.match(T.DASH):
                    if self.match(T.K1):
                        return CompCodes.MmONE
                    elif self.match(T.D):
                        return CompCodes.MmD
                    raise Exception("Line:", tk.line, "Expected 1 or D after M-")
                else:
                    return CompCodes.M
            case T.SEMI:
                if jmp := self.match(T.JUMP):
                    return typing.cast(JumpCodes, jmp.lexeme)
                raise Exception("Line:", tk.line, "Expected JUMP spec after ;")
            case T.EOS:
                return self.eos
            case T.INT | T.LABEL | T.ID:
                return AInstruction(tk)
            case _:
                raise Exception("Line:", tk.line, "Unexpected token", tk)

    def _parse_inst(self) -> None | EOSsentinelType | AInstruction | CInstruction:
        code = self._parse()
        if code is None:
            return None
        elif code is self.eos:
            return self.eos
        elif isinstance(code, AInstruction):
            inst = code
            code = self._parse()
        else:
            dest = DestCodes.NULL
            if isinstance(code, DestCodes):
                dest = code
                code = self._parse()
            if isinstance(code, CompCodes):
                comp = code
                code = self._parse()
            else:
                raise Exception(
                    "Line:",
                    self.line,
                    ":Missing mandatory comp part of C instruction",
                    dest,
                    code,
                )
            jump = JumpCodes.NULL
            if isinstance(code, JumpCodes):
                jump = code
                code = self._parse()
            inst = CInstruction(dest, comp, jump)
        if code is not None and code is not self.eos:
            raise Exception(
                "Line:",
                self.line,
                ":Expected eof or newline at the end of instruction",
                inst,
            )
        return inst

    def parse(self) -> AInstruction | CInstruction | None:
        while True:
            inst = self._parse_inst()
            if inst is None:
                break
            if isinstance(inst, EOSsentinelType):
                continue
            if isinstance(inst, AInstruction):
                if inst.value.typ == Token.Type.LABEL:
                    if self.count >= 0x8000:
                        raise Exception(
                            "Line",
                            inst.value.line,
                            ":Label value cannot fit into 15bits:",
                            self.count,
                        )
                    self.labels[inst.value.lexeme] = self.count
                    self.count -= 1 # Don't count label instructions
            self.count += 1
            return inst

