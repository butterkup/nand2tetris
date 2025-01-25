import pathlib as pth
import sys

from .lexer import Lexer
from .parser import Parser
from .printer import ASTreePrinter

for file in sys.argv[1:]:
    path = pth.Path(file)
    if path.is_file():
        program = path.read_text()
        printer = ASTreePrinter(2)
        print(f"Parsing file: {path!s}", file=sys.stderr)
        for stmt in Parser(Lexer(program)):
            printer.print(stmt)
        # print(f"Lexing file: {path!s}", file=sys.stderr)
        # for token in Lexer(program):
        #     print(token)
    else:
        print(f"Not a file: {path!s}", file=sys.stderr)

