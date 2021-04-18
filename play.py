import re


class TemplateError(Exception):
    pass


class TemplateSyntaxError(TemplateError):
    pass


class TemplateContextError(TemplateError):
    pass


TOKEN_PATTERN = re.compile(r'({{.*?}}|{%.*?%}|{#.*?#})')


class CodeBuilder:
    INDENT_STEP = 4

    def __init__(self, indent: int = 0) -> None:
        self.code = []
        self.indent_level = indent

    def add_line(self, line: str) -> 'CodeBuilder':
        self.code.append(' ' * self.indent_level)
        self.code.append(line)
        self.code.append('\n')
        return self

    def indent(self) -> 'CodeBuilder':
        self.indent_level += self.INDENT_STEP
        return self

    def dedent(self) -> 'CodeBuilder':
        self.indent_level -= self.INDENT_STEP
        return self

    def __str__(self) -> str:
        return ''.join(str(c) for c in self.code)

    def exec(self) -> dict:
        if self.indent_level != 0:
            raise TemplateSyntaxError('Wrong indent')
        source = str(self)
        namespace = {}
        exec(source, None, namespace)
        return namespace


class Compiler:
    def __init__(self, text: str, context: dict) -> None:
        self.context = context
        self.code = code = CodeBuilder()
        self.buffer = buffer = []

        code.add_line('def render(ctx):').indent()
        code.add_line('output=[]')

        ops_stack = []

        for token in TOKEN_PATTERN.split(text):
            if token.startswith('{#'):
                continue
            elif token.startswith('{{'):
                buffer.append(f'ctx.{token[2:-2].strip()}')
            elif token.startswith('{%'):
                self.flush_buffer()

                statement = token[2:-2].strip().split()
                instruction = statement[0]

                if instruction == 'if':
                    ops_stack.append('if')
                    code.add_line(f'if ctx.{statement[1]}:')
                    code.indent()
                elif instruction == 'for':
                    ops_stack.append('for')
                    code.add_line('for {} in {}:'.format(statement[1], f'ctx.{statement[3]}'))
                    code.indent()
                elif instruction.startswith('end'):
                    end_what = instruction[3:]
                    if not ops_stack:
                        raise TemplateSyntaxError(f'find too many ends: {token}')

                    start_what = ops_stack.pop()
                    if start_what != end_what:
                        raise TemplateSyntaxError(f'mismatched end tag: {token}')

                    code.dedent()
                else:
                    raise TemplateSyntaxError(f'cannot understand tag: {token}')
            else:
                if token.strip():
                    buffer.append(repr(token))

        self.flush_buffer()
        code.dedent()
        code.add_line('return "".join(output)')

    def flush_buffer(self):
        if not self.buffer:
            return
        self.code.add_line('output.extend([{}])'.format(', '.join(self.buffer)))
        del self.buffer[:]

    def eval_expr(self, expr: str) -> str:
        pass

    def render(self, ctx: dict) -> str:
        render_fn = self.code.exec()['render']
        return render_fn(ctx)


class Template:
    global_context = {}

    def __init__(self, text: str) -> None:
        self.compiler = Compiler(text, self.global_context)

    @classmethod
    def update_global_context(cls, ctx: dict) -> None:
        cls.global_context.update(ctx)

    def render(self, **ctx) -> str:
        return self.compiler.render(ctx)


if __name__ == '__main__':
    html = """
<html>
    <head><title>hello</title></head>
    <body>
        <h1>hello, {{ user.name }}</h1>
        <ul>
        {% for book in books %}
            {% if book %}
            <li>{{ book.title }}</li>
            {% endif %}
        {% endfor %}
        </ul>
    </body>
</html>""".strip()

    compiler = Compiler(html, {})
    print(compiler.code.__str__())
