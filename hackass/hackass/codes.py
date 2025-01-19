import enum

USR_SYM_START: int = 16

PREDEFINED: dict[str, int] = dict(
    R0=0,
    R1=1,
    R2=2,
    R3=3,
    R4=4,
    R5=5,
    R6=6,
    R7=7,
    R8=8,
    R9=9,
    R10=10,
    R11=11,
    R12=12,
    R13=13,
    R14=14,
    R15=15,
    SCREEN=0x4000,
    KBD=0x6000,
)


class JumpCodes(enum.StrEnum):
    NULL = "000"
    JGT = "001"
    JEQ = "010"
    JGE = "011"
    JLT = "100"
    JNE = "101"
    JLE = "110"
    JMP = "111"


class CompCodes(enum.StrEnum):
    ZERO = "0101010"
    ONE = "0111111"
    NEG_ONE = "0111010"
    D = "0001100"
    A = "0110000"
    M = "1110000"
    NOT_D = "0001101"
    NOT_A = "0110001"
    NOT_M = "1110001"
    NEG_D = "0001111"
    NEG_A = "0110011"
    NEG_M = "1110011"
    DpONE = "0011111"
    ApONE = "0110111"
    MpONE = "1110111"
    DmONE = "0001110"
    AmONE = "0110010"
    MmONE = "1110010"
    DpA = "0000010"
    DpM = "1000010"
    DmA = "0010011"
    DmM = "1010011"
    AmD = "0000111"
    MmD = "1000111"
    DaA = "0000000"
    DaM = "1000000"
    DoA = "0010101"
    DoM = "1010101"


class DestCodes(enum.StrEnum):
    NULL = "000"
    M = "001"
    D = "010"
    DM = "011"
    A = "100"
    AM = "101"
    AD = "110"
    ADM = "111"

