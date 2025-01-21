import pathlib
import typing as ty

from .codegen import CodeGen, Symbols, label_generator
from .lexer import Lexer
from .parser import Parser


class Translator:
    def __init__(
        self,
        paths: ty.Sequence[pathlib.Path] | None = None,
        *,
        prefix: str | None = None,
        names: Symbols | None = None,
    ):
        self.prefix = "__vm_symbol_" if prefix is None else prefix
        self.names = Symbols() if names is None else names
        self.paths = paths or ()
        self.reset()

    def reset(self):
        self.not_found = set[str]()
        labgen = label_generator(self.prefix)
        self.codegen = CodeGen(self.names, labgen)

    def resolve(self, name: str) -> pathlib.Path | None:
        filename = f"{name}.vm"
        for path in self.paths:
            if path.is_dir():
                for file in path.iterdir():
                    if file.name == filename:
                        return file
            elif path.is_file() and path.name == filename:
                return path

    def resolve_refs(self):
        for name in self.codegen.referenced:
            if name in self.not_found:
                continue
            if found := self.resolve(name):
                return name, found
        return None, None

    def _translate(self, nm: str, program: str):
        lexer = Lexer(program)
        parser = Parser(lexer)
        yield from self.codegen.gen(parser, nm)

    def translate(self, nm: str, program: str):
        yield from self.codegen.program_setup()
        yield from self._translate(nm, program)
        while True:
            name, found = self.resolve_refs()
            if found is None:
                break
            with open(found) as file:
                program = file.read()
            try:
                yield from self._translate(found.stem, program)
                if name in self.codegen.referenced:
                    self.not_found.add(name)
            except Exception as e:
                e.add_note(f"Error encountered while processing: {found!s}")
                raise
        if self.codegen.referenced:
            raise Exception(
                "Unresolved functions\n"
                + "\n".join(
                    f"{name} used in {nm} line {line}"
                    for name, (nm, line) in self.codegen.referenced.items()
                )
            )
        yield from self.codegen.program_teardown()

