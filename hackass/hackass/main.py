import pathlib
import sys


def compile(input_file: pathlib.Path, output_file: pathlib.Path):
    from .assembler import assemble

    with open(input_file) as f:
        prog = f.read()
    code = assemble(prog)
    with open(output_file, "w") as f:
        f.write(code)


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m hackass program.asm\n  -> program.hack", file=sys.stderr)
        return 1
    input_file = pathlib.Path(sys.argv[1])
    if not input_file.exists():
        print(f"Cannot find input file: {input_file!s}", file=sys.stderr)
        return 2
    if input_file.suffix != ".asm":
        print(f"InputFile must be a .asm but got ext={input_file.suffix!r}", file=sys.stderr)
        return 3
    output_file = input_file.with_suffix(".hack")
    if output_file.exists() and not output_file.is_file():
        print(f"OutputFile is not a file: {output_file}", file=sys.stderr)
        return 4
    compile(input_file, output_file)

