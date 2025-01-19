import dataclasses as dt
from .codes import JumpCodes, CompCodes, DestCodes
from .lexer import Token

@dt.dataclass(slots=True, frozen=True)
class AInstruction:
    value: Token


@dt.dataclass(slots=True, frozen=True)
class CInstruction:
    dest: DestCodes
    comp: CompCodes
    jump: JumpCodes


class EOSsentinelType: ...


EOSsentinel = EOSsentinelType()

