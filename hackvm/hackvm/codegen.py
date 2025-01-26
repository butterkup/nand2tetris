import dataclasses as dt
import itertools
import typing as ty

from .lexer import Token
from .parser import Statement


@dt.dataclass(slots=True)
class Symbols:
    stack: int = 0  # SP
    local: int = 1  # LCL
    argument: int = 2  # ARG
    stack_base: int = 256  # Base address for the stack to start from

    temp: int = 3  # TEMP R[3-12]
    static: int = 16  # STATIC [16-255]
    # Free Registers, for compiler use.
    free_1: int = 13
    free_2: int = 14
    free_3: int = 15

    # constant must be zero so that index + constant == index
    constant: int = 0


_bin_op_tbl: dict[Token.Type, str] = {
    Token.Type.ADD: "+",
    Token.Type.SUB: "-",
    Token.Type.AND: "&",
    Token.Type.OR: "|",
}

_cmp_op_tbl: dict[Token.Type, str] = {
    Token.Type.EQ: "JEQ",
    Token.Type.LT: "JLT",
    Token.Type.GT: "JGT",
}


def label_generator(prefix: str, start: int = 0, /):
    "Unique infinite label source"
    return map(lambda i: f"{prefix}{i}", itertools.count(start))


class CodeGen:
    "All state of this class are readonly."

    def __init__(self, names: Symbols, labgen: ty.Iterator[str]):
        self.names = names
        self.stack = f"@{names.stack}"
        self.local = f"@{names.local}"
        self.argument = f"@{names.argument}"
        self.free_1 = f"@{names.free_1}"
        self.free_2 = f"@{names.free_2}"
        self.free_3 = f"@{names.free_3}"
        self.static = f"@{names.static}"
        self.labgen = labgen
        self.functions: dict[str, tuple[str, int]] = {}
        self.referenced: dict[str, tuple[str, int]] = {}
        # Mimimize setup/teardown by jumping to this locations
        self.call_lbl = self.label() + "___CALL"
        self.return_lbl = self.label() + "___RETURN"
        self.function_lbl = self.label() + "___FUNCTION"
        self.push_this_lbl = self.label() + "___PUSH_THIS"

    def decrement_SP(self):
        yield self.stack
        yield "M=M-1"

    def increment_SP(self):
        yield self.stack
        yield "M=M+1"

    def set_A_to_SP0(self):
        yield self.stack
        yield "A=M"

    def load_stack_0_into_D(self):
        yield from self.set_A_to_SP0()
        yield "D=M"

    def set_A_to_SP1(self):
        yield self.stack
        yield "A=M-1"

    def load_stack_1_into_D(self):
        yield from self.set_A_to_SP1()
        yield "D=M"

    def load_D_into_SP1(self):
        yield self.stack
        yield "A=M-1"
        yield "M=D"

    def load_D_into_SP0(self):
        yield self.stack
        yield "A=M"
        yield "M=D"

    def pop_stack_into_D_and_set_A_to_SP(self):
        """
        SP = SP - 1
        D = RAM[SP]
        A = SP - 1

        therefore M == RAM[SP - 1]
        """
        yield from self.decrement_SP()
        yield from self.load_stack_0_into_D()
        yield from self.set_A_to_SP1()

    def binary_arithmetic_cmd(self, op: str):
        yield from self.pop_stack_into_D_and_set_A_to_SP()
        yield f"M=D{op}M"

    def unary_not_cmd(self):
        yield from self.set_A_to_SP1()
        yield "M=!M"

    def unary_neg_cmd(self):
        yield from self.unary_not_cmd()
        yield "M=M+1"

    def label(self) -> str:
        return next(self.labgen)

    def comparison_op_cmd(self, jmp: str):
        yield from self.pop_stack_into_D_and_set_A_to_SP()
        yield f"D=D-M"
        yield "M=-1"
        label = self.label()
        yield f"@{label}"
        yield f"D;{jmp}"
        yield from self.set_A_to_SP1()
        yield "M=0"
        yield f"({label})"

    @staticmethod
    def set_AD_to_BASE_i(base: str, i: str):
        yield f"@{base}"
        yield "D=M"
        yield f"@{i}"
        yield "AD=D+A"

    def push_cmd(self, segment: str, index: str):
        yield from self.set_AD_to_BASE_i(segment, index)
        yield "D=M"
        yield from self.push_D_into_stack()

    def push_at_cmd(self, constant: int):
        yield f"@{constant}"
        yield "D=A"
        yield from self.push_D_into_stack()

    def pop_cmd(self, segment: str, index: str):
        yield from self.decrement_SP()
        yield from self.set_AD_to_BASE_i(segment, index)
        yield self.free_1
        yield "M=D"
        yield from self.load_stack_0_into_D()
        yield self.free_1
        yield "A=M"
        yield "M=D"

    def pop_at_cmd(self, loc: int):
        yield from self.decrement_SP()
        yield from self.load_stack_0_into_D()
        yield f"@{loc}"
        yield "M=D"

    def section_function_lbl(self):
        "API: free_1=nvars, D=body_addr"
        yield f"({self.function_lbl})"
        # Save return_addr into free_3
        yield self.free_3
        yield "M=D"
        # Iterate nvars times while pushing 0's to the stack
        yield self.free_1
        yield "D=M"
        start_nvars_setup = self.label()
        yield f"({start_nvars_setup})"
        end_nvars_setup = self.label()
        yield f"@{end_nvars_setup}"
        yield "D;JEQ"
        yield self.stack
        yield "A=M"
        yield "M=0"
        yield self.stack
        yield "M=M+1"
        yield "D=D-1"
        yield f"@{start_nvars_setup}"
        yield "0;JMP"
        yield f"({end_nvars_setup})"
        yield self.free_3
        yield "A=M"
        yield "0;JMP"

    def function_cmd(self, name: str, nvars: str):
        yield f"({name})"
        yield f"@{nvars}"
        yield "D=A"
        yield self.free_1
        yield "M=D"
        body = f"{self.label()}.{name}"
        yield f"@{body}"
        yield "D=A"
        yield f"@{self.function_lbl}"
        yield "0;JMP"
        yield f"({body})"

    def if_goto_cmd(self, goto: str):
        yield from self.decrement_SP()
        yield from self.load_stack_0_into_D()
        label = self.label()
        yield f"@{label}"
        yield "D;JEQ"
        yield f"@{goto}"
        yield "0;JMP"
        yield f"({label})"

    def push_D_into_stack(self):
        yield from self.load_D_into_SP0()
        yield from self.increment_SP()

    @staticmethod
    def load_from_src_into_D(src: int):
        yield f"@{src}"
        yield "D=M"

    def push_src_into_stack(self, src: int):
        yield from self.load_from_src_into_D(src)
        yield from self.push_D_into_stack()

    def push_frame(self):
        "Expect return address in register D"
        yield from self.push_D_into_stack()
        yield from self.push_src_into_stack(self.names.local)
        yield from self.push_src_into_stack(self.names.argument)

    def section_call_lbl(self):
        "API: D=return_address, free_1=function, free_2=nvars"
        yield f"({self.call_lbl})"
        yield from self.push_frame()
        # LCL=SP
        yield self.stack
        yield "D=M"
        yield self.local
        yield "M=D"
        # Calculate D=SP-nvars-3
        yield self.stack
        yield "D=M"
        yield self.free_2
        yield "D=D-M"
        yield "@3"
        yield "D=D-A"
        # ARG=D
        yield self.argument
        yield "M=D"
        # Jump to function
        yield self.free_1
        yield "A=M"
        yield "0;JMP"

    def call_cmd(self, function: str, nvars: str):
        yield f"@{function}"
        yield "D=A"
        yield self.free_1
        yield "M=D"

        yield f"@{nvars}"
        yield "D=A"
        yield self.free_2
        yield "M=D"

        ret = self.label()
        yield f"@{ret}"
        yield "D=A"
        yield f"@{self.call_lbl}"
        yield "0;JMP"
        yield f"({ret})"

    def pop_stack_into_dest(self, dest: int):
        yield from self.load_stack_1_into_D()
        yield f"@{dest}"
        yield "M=D"
        yield from self.decrement_SP()

    def pop_frame(self):
        "Leave return address in names.free_3"
        yield from self.pop_stack_into_dest(self.names.argument)
        yield from self.pop_stack_into_dest(self.names.local)
        yield from self.load_stack_1_into_D()
        yield self.free_3
        yield "M=D"

    def section_return_lbl(self):
        yield f"({self.return_lbl})"
        # save the result into free_1
        yield from self.load_stack_1_into_D()
        yield self.free_1
        yield "M=D"

        # set ARG into free_2
        yield self.argument
        yield "D=M"
        yield self.free_2
        yield "M=D"

        # remove all locals by setting SP to LCL
        yield self.local
        yield "D=M"
        yield self.stack
        yield "M=D"

        # set the frame back to callers ctx and return address into free_3
        yield from self.pop_frame()

        # set SP=free_2
        yield self.free_2
        yield "D=M"
        yield self.stack
        yield "M=D"

        # set RAM[SP]=free_1
        yield self.free_1
        yield "D=M"
        yield from self.push_D_into_stack()

        # jump to the return address in free_3
        yield self.free_3
        yield "A=M"
        yield "0;JMP"

    def return_cmd(self):
        yield f"@{self.return_lbl}"
        yield "0;JMP"

    def get_name(self, name: str):
        return getattr(self.names, name)

    def program_setup(self):
        yield from ("@16", "D=A", self.stack, "M=D")

    def program_teardown(self):
        yield "\n\n// VM INSTRUCTION HELPERS: [call, return, function]"
        yield from self.section_call_lbl()
        yield from self.section_return_lbl()
        yield from self.section_function_lbl()

    def scoped_function_cmd(self, nm: str, ident: Token, nvars: Token):
        if ident.lexeme in self.functions:
            info = self.functions[ident.lexeme]
            raise Exception(
                f"Line {ident.line}: Function {ident.lexeme!r} has already "
                f"been defined in {info[0]!r} line {info[1]}"
            )
        if ident.lexeme in self.referenced:
            del self.referenced[ident.lexeme]
        self.functions[ident.lexeme] = nm, ident.line
        return self.function_cmd(ident.lexeme, nvars.lexeme)

    def scoped_call_cmd(self, nm: str, ident: Token, nvars: Token):
        if ident.lexeme not in self.functions:
            self.referenced[ident.lexeme] = nm, ident.line
        return self.call_cmd(ident.lexeme, nvars.lexeme)

    def scoped_label_cmd(self, nm: str, ident: Token):
        mangled = self.mangle_label(nm, ident.lexeme)
        if mangled in self.functions:
            info = self.functions[mangled]
            raise Exception(
                f"Line {ident.line}: Mangled label ({ident.lexeme!r} -> {mangled!r}) "
                f"conflits with function {mangled!r} defined in {info[0]} line {info[1]}"
            )
        yield f"({mangled})"

    def _load_THISpI_into_D(self, index: str, *this: str):
        "AD=RAM[A]+index"
        yield f"@{index}"
        yield "D=A"
        yield from this
        yield "AD=D+M"

    def _pop_member(self):
        "API: D=this+I"
        yield self.free_1
        yield "M=D"
        yield from self.load_stack_1_into_D()
        yield self.free_1
        yield "A=M"
        yield "M=D"
        yield from self.decrement_SP()

    def pop_member(self, index: str):
        yield from self.decrement_SP()
        yield from self._load_THISpI_into_D(index, self.stack, "A=M")
        yield from self._pop_member()

    def pop_member_this(self, index: str):
        yield from self._load_THISpI_into_D(index, self.argument, "A=M")
        yield from self._pop_member()

    def push_member(self, index: str):
        yield from self._load_THISpI_into_D(index, self.stack, "A=M-1")
        yield "D=M"
        yield from self.load_D_into_SP1()

    def push_member_this(self, index: str):
        yield from self._load_THISpI_into_D(index, self.argument, "A=M")
        yield "D=M"
        yield from self.load_D_into_SP0()
        yield from self.increment_SP()

    @staticmethod
    def mangle_label(nm: str, label: str):
        return f"{nm}.{label}"

    def gen(self, stmts: ty.Iterable[Statement], nm: str) -> ty.Iterator[str]:
        T = Token.Type
        for stmt in stmts:
            yield f"\n// {nm}[{stmt[0].line}]   " + " ".join(tk.lexeme for tk in stmt)
            match stmt:
                case (Token(typ=T.AND | T.OR | T.ADD | T.SUB),):
                    yield from self.binary_arithmetic_cmd(_bin_op_tbl[stmt[0].typ])
                case (Token(typ=T.EQ | T.LT | T.GT),):
                    yield from self.comparison_op_cmd(_cmp_op_tbl[stmt[0].typ])
                case (Token(typ=T.NOT),):
                    yield from self.unary_not_cmd()
                case (Token(typ=T.NEG),):
                    yield from self.unary_neg_cmd()
                case (Token(typ=T.LABEL), ident):
                    yield from self.scoped_label_cmd(nm, ident)
                case (Token(typ=T.FUNCTION), ident, nvars):
                    yield from self.scoped_function_cmd(nm, ident, nvars)
                case (Token(typ=T.IF_GOTO), ident):
                    yield from self.if_goto_cmd(self.mangle_label(nm, ident.lexeme))
                case (Token(typ=T.GOTO), ident):
                    yield from (f"@{self.mangle_label(nm, ident.lexeme)}", f"0;JMP")
                case (Token(typ=T.RETURN),):
                    yield from self.return_cmd()
                case (Token(typ=T.CALL), ident, nvars):
                    yield from self.scoped_call_cmd(nm, ident, nvars)

                case (Token(typ=T.PUSH), Token(typ=T.MEMBER), index):
                    yield from self.push_member(index.lexeme)
                case (Token(typ=T.PUSH), Token(typ=T.THIS), index):
                    yield from self.push_member_this(index.lexeme)
                case (Token(typ=T.POP), Token(typ=T.MEMBER), index):
                    yield from self.pop_member(index.lexeme)
                case (Token(typ=T.POP), Token(typ=T.THIS), index):
                    yield from self.pop_member_this(index.lexeme)

                case (
                    Token(typ=T.PUSH),
                    Token(typ=T.STATIC | T.TEMP | T.CONSTANT) as t,
                    index,
                ):
                    value = self.get_name(t.lexeme) + int(index.lexeme)
                    yield from self.push_at_cmd(value)
                case (Token(typ=T.PUSH), Token(typ=T.LOCAL | T.ARGUMENT) as t, index):
                    segment = self.get_name(t.lexeme)
                    yield from self.push_cmd(segment, index.lexeme)

                case (
                    Token(typ=T.POP),
                    Token(typ=T.STATIC | T.TEMP) as t,
                    index,
                ):
                    value = self.get_name(t.lexeme) + int(index.lexeme)
                    yield from self.pop_at_cmd(value)
                case (Token(typ=T.POP), Token(typ=T.ARGUMENT | T.LOCAL) as t, index):
                    target = self.get_name(t.lexeme)
                    yield from self.pop_cmd(target, index.lexeme)

                case _:
                    raise Exception(
                        f"Line {stmt[0].line}: Cannot translate statement {' '.join(map(lambda t: t.lexeme, stmt))!r}"
                    )
