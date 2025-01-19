from collections import defaultdict

from .codes import PREDEFINED, USR_SYM_START
from .lexer import Lexer, Token
from .parser import Parser
from .utils import AInstruction, CInstruction


def assemble(
    program: str, /, symbols: dict[str, int] = PREDEFINED, sym_cnt_start: int = USR_SYM_START
) -> str:
    lexer = Lexer(program)
    parser = Parser(lexer)
    inst_codes: list[str] = []
    resolve = defaultdict(list[int])
    while True:
        match parser.parse():
            case AInstruction(
                value=Token(typ=Token.Type.LABEL, lexeme=symbol, line=line)
            ):
                if symbol in symbols:
                    raise Exception("Line", line, ":Symbol redeclared:", symbol)
            case AInstruction(value=Token(typ=Token.Type.INT, lexeme=lexeme)):
                assert len(lexeme) == 15, "len(Token.Type.INT) != 15"
                inst_codes.append("0" + lexeme)
            case AInstruction(value=Token(typ=Token.Type.ID, lexeme=symbol, line=line)):
                if symbol in symbols:
                    value = format(symbols[symbol], "b").rjust(16, "0")
                    inst_codes.append(value)
                elif symbol in parser.labels:
                    value = format(parser.labels[symbol], "b").rjust(16, "0")
                    inst_codes.append(value)
                else:
                    resolve[symbol].append(len(inst_codes))
                    inst_codes.append("0")
            case CInstruction(dest=dest, comp=comp, jump=jump):
                inst_codes.append(f"111{comp:s}{dest:s}{jump:s}")
            case None:
                break
    for symbol, where in resolve.items():
        if symbol in parser.labels:
            value = format(parser.labels[symbol], "b").rjust(16, "0")
        else:
            v = sym_cnt_start
            sym_cnt_start += 1
            value = format(v, "b").rjust(16, "0")
        for here in where:
            inst_codes[here] = value

    def check_inst(c: str) -> str:
        assert len(c) == 16, (c, len(c))
        return c

    return "\n".join(map(check_inst, inst_codes)) + "\n"

