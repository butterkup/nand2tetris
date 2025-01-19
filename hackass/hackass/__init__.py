def __getattr__(name: str):
    if name == "assemble":
        global assemble
        from .assembler import assemble

        return assemble
    raise AttributeError(f"Module {__name__} does not export name {name!r}")

