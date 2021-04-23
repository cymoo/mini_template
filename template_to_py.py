"""A simple toy template engine"""

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

    def __init__(self,
                 escape_html: bool = True,
                 dot_notation: bool = True,
                 **options) -> None:
        self.escape_html = escape_html
        self.dot_notation = dot_notation
        self.options = options

    def render(self, text: str, **ctx):
        code = self.compile(text, self.escape_html)
        namespace = self.global_ctx.copy()
        namespace.update(ctx)

        if self.dot_notation:
            namespace = {key: DotSon(value) for key, value in namespace.items()}

        exec(str(code), namespace)
        return namespace['render']()

    @staticmethod
    def compile(text: str, escape_html: bool = True) -> 'CodeWriter':
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
                if escape_html:
                    buffer.append(f'escape(str({expr}))')
                else:
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
