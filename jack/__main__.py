import pathlib as pth
import sys

from .lexer import Lexer

for file in sys.argv[1:]:
    path = pth.Path(file)
    if path.is_file():
        program = path.read_text()
        print(f"Lexing file: {path!s}", file=sys.stderr)
        for token in Lexer(program):
            print(token)
    else:
        print(f"Not a file: {path!s}", file=sys.stderr)

