import re
from utils import html_escape, DotSon


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
    def __init__(self, text: str, global_ctx: dict) -> None:
        self.global_ctx = global_ctx
        self.code = code = CodeBuilder()
        self.buffer = buffer = []

        code.add_line('def render(ctx, global_ctx):').indent()
        self.expand_global_context()
        code.add_line('output = []')

        ops_stack = []

        for token in TOKEN_PATTERN.split(text):
            if token.startswith('{#'):
                continue
            elif token.startswith('{{'):
                buffer.append(f'str({token[2:-2].strip()})')
            elif token.startswith('{%'):
                self.flush_buffer()

                statement = token[2:-2].strip().split(maxsplit=1)
                instruction = statement[0]

                if instruction == 'var':
                    code.add_line(statement[1])
                elif instruction == 'if':
                    ops_stack.append('if')
                    code.add_line(f'if {statement[1]}:')
                    code.indent()
                elif instruction == 'elif':
                    if not ops_stack or ops_stack[-1] not in ('if', 'elif'):
                        raise TemplateSyntaxError(f'mismatched loop tag: {token}')
                    ops_stack.append('elif')
                    code.dedent()
                    code.add_line(f'elif {statement[1]}:')
                    code.indent()
                elif instruction == 'else':
                    if not ops_stack or ops_stack[-1] not in ('if', 'elif'):
                        raise TemplateSyntaxError(f'mismatched loop tag: {token}')
                    ops_stack.append('else')
                    code.dedent()
                    code.add_line('else:')
                    code.indent()
                elif instruction == 'for':
                    ops_stack.append('for')
                    code.add_line(f'for {statement[1]}:')
                    code.indent()
                elif instruction.startswith('end'):
                    end_what = instruction[3:]
                    if not ops_stack:
                        raise TemplateSyntaxError(f'too many ends: {token}')
                    if end_what == 'if':
                        while True:
                            start_what = ops_stack.pop()
                            if start_what == 'if':
                                break
                            if start_what in ('elif', 'else'):
                                continue
                            raise TemplateSyntaxError(f'mismatched end tag: {token}')
                    else:
                        start_what = ops_stack.pop()
                        if start_what != end_what:
                            raise TemplateSyntaxError(f'mismatched end tag: {token}')
                    code.dedent()
                else:
                    raise TemplateSyntaxError(f'cannot understand tag: {token}')
            else:
                if token.strip():
                    buffer.append(repr(token))

        if ops_stack:
            raise TemplateSyntaxError(f'unmatched tag: {ops_stack[-1]}')

        self.flush_buffer()
        code.add_line('return "".join(output)')
        code.dedent()

    def flush_buffer(self) -> None:
        if not self.buffer:
            return
        self.code.add_line('output.extend([{}])'.format(', '.join(self.buffer)))
        del self.buffer[:]

    def expand_global_context(self) -> None:
        for name in self.global_ctx:
            self.code.add_line('{} = global_ctx["{}"]'.format(name, name))

    def render(self, ctx: dict) -> str:
        render_fn = self.code.exec()['render']
        return render_fn(DotSon(ctx), DotSon(self.global_ctx))


class Template:
    global_context = {'escape': html_escape}

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
        <h1>hello, {% if ctx.user %}{{ ctx.user }}{% else %}{{ 'guest' }}{% endif %}</h1>
        <h2>{{escape(ctx.post)}}</h2>
        <ul>
        {% for plan in ctx.plans %}
            <li>{{ plan.topic }} --- {{ plan.date }}</li>
        {% endfor %}
        </ul>
        {% if True %}{{ 'foo' }}{% endif %}
    </body>
</html>""".strip()

    template = Template(html)
    print(str(template.compiler.code))
    result = template.render(
        user='jie',
        books=['CSAPP', 'APUE', 'SICP'],
        plans=[
            {'topic': 'marry', 'date': '2021-10-01'},
            {'topic': 'house', 'date': '2021-10-01'},
            {'topic': 'career', 'date': '2021-06-01'},
        ],
        post="<h1>hello world</h1>"
    )
    print(result, file=open('test.html', 'wt'))
