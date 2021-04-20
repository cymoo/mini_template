import re


class TemplateError(Exception):
    pass


class TemplateSyntaxError(TemplateError):
    pass


class TemplateContextError(TemplateError):
    pass


TOKEN_PATTERN = re.compile(r'({{.*?}}|{%.*?%}|{#.*?#})')


class Compiler:
    def __init__(self, text: str, ctx: dict) -> None:
        pass

    def render(self, ctx) -> str:
        pass


class Template:
    global_context = {}

    def __init__(self, text: str) -> None:
        self.compiler = Compiler(text, self.global_context)

    @classmethod
    def update_global_context(cls, ctx: dict) -> None:
        cls.global_context.update(ctx)

    def render(self, **ctx) -> str:
        return self.compiler.render(ctx)
