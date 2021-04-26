"""A simple template engine which compiles a template to Python."""

import re
from utils import html_escape, DotSon


FRAGMENT_PATTERN = re.compile(r'({{.*?}}|{%.*?%}|{#.*?#})')


class CodeWriter:
    INDENT_STEP = 4

    def __init__(self, indents: int = 0) -> None:
        self.code = []
        self.indents = indents

    def add_line(self, line: str) -> 'CodeWriter':
        self.code.append(' ' * self.indents)
        self.code.append(line)
        self.code.append('\n')
        return self

    def indent(self) -> 'CodeWriter':
        self.indents += self.INDENT_STEP
        return self

    def dedent(self) -> 'CodeWriter':
        self.indents -= self.INDENT_STEP
        return self

    def __str__(self) -> str:
        return ''.join(str(c) for c in self.code)


class Template:
    global_ctx = {'escape': html_escape}

    def __init__(self, **options) -> None:
        self.options = options

    @classmethod
    def set_global_ctx(cls, ctx: dict) -> None:
        cls.global_ctx.update(ctx)

    def render(self, text: str, **ctx):
        # NOTE: We should compile once for a template and cache the compiled code somewhere
        code = compile(str(self.parse(text)), '<string>', 'exec')

        namespace = self.global_ctx.copy()
        namespace.update(ctx)
        namespace = {key: DotSon(value) for key, value in namespace.items()}

        exec(code, namespace)
        return namespace['render']()

    @staticmethod
    def parse(text: str) -> 'CodeWriter':
        code = CodeWriter()
        buffer = []

        def flush_buffer():
            if not buffer:
                return
            code.add_line('output.extend([{}])'.format(', '.join(buffer)))
            del buffer[:]

        code.add_line('def render():').indent()
        code.add_line('output = []')

        for fragment in FRAGMENT_PATTERN.split(text):
            if fragment.startswith('{#'):
                continue
            elif fragment.startswith('{{'):
                expr = fragment[2:-2].strip()
                buffer.append(f'str({expr})')
            elif fragment.startswith('{%'):
                flush_buffer()

                statement = fragment[2:-2].strip().strip(':')
                instruction = statement.split(maxsplit=1)[0]

                if instruction == 'if':
                    code.add_line(statement + ':')
                    code.indent()
                elif instruction in ('else', 'elif'):
                    code.dedent()
                    code.add_line(statement + ':')
                    code.indent()
                elif instruction == 'for':
                    code.add_line(statement + ':')
                    code.indent()
                elif instruction.startswith('end'):
                    code.dedent()
                else:
                    raise SyntaxError(f'cannot understand tag: {fragment}')
            else:
                if fragment.strip():
                    buffer.append(repr(fragment))

        flush_buffer()
        code.add_line('return "".join(output)')
        code.dedent()

        return code
