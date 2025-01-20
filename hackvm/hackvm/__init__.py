def __getattr__(name: str):
    if name == "Translator":
        global Translator
        from .translator import Translator

        return Translator
    raise AttributeError(f'Module {__name__} does not export {name!r}')
