import os
import pathlib
import sys
import typing

from .translator import Translator

PATH_ENV = "HACK_VM_PATHS"


def _compile(trans: Translator, in_file: pathlib.Path, out_file: pathlib.Path):
    with open(in_file) as f:
        vm_src = f.read()
    with open(out_file, "w") as f:
        f.writelines(line + "\n" for line in trans.translate(in_file.stem, vm_src))


def compile_file(in_file: pathlib.Path, paths: typing.Sequence[pathlib.Path]):
    if not in_file.is_file():
        print(f"{in_file!s} is not a regular file.", file=sys.stderr)
        return 2
    if in_file.name.isupper() or in_file.suffix != ".vm":
        print(
            "File name must be of the form '[A-Z][.*]\\.vm'\nThat is:\n"
            "\tHave the .vm extension and\n"
            "\tThe first character of the name be an uppercase.",
            file=sys.stderr,
        )
        return 3
    out_file = in_file.with_suffix(".asm")
    if out_file.exists() and not out_file.is_file():
        print(f"{out_file!s} exists and not a file.", file=sys.stderr)
        return 4
    trans = Translator(paths)
    _compile(trans, in_file, out_file)
    return 0


def get_paths(env: str | None = None, curdir: pathlib.Path | None = None):
    env = PATH_ENV if env is None else env
    path_list = os.getenv(env, "").split(":")
    paths = [] if curdir is None else [curdir]
    for path in path_list:
        if not path:
            continue
        path = pathlib.Path(path)
        if path.exists():
            paths.append(path)
            continue
        raise Exception(f"Path not found: {path!s}")
    return paths


def main(paths_env: str | None = None):
    if len(sys.argv) != 2:
        print(
            f"Usage: python -m hackvm Program.vm\n\t-> Program.asm",
            file=sys.stderr,
        )
        return 1
    in_file = pathlib.Path(sys.argv[1])
    if not in_file.exists():
        print(f"{in_file!s} does not exist.")
    paths = get_paths(paths_env, in_file.parent)
    if in_file.is_file():
        return compile_file(in_file, paths)
    else:
        code = 0
        for file in in_file.glob("[A-Z]*.vm"):
            code |= compile_file(file, paths)
        return code
