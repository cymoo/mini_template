"""A simple template engine which compiles a template to AST."""

from pprint import pprint
from typing import List, Any, Optional
from collections import ChainMap, namedtuple


class TemplateError(Exception):
    """Base exception class"""


class TemplateSyntaxError(TemplateError):
    """Exception of bad template syntax"""


class TemplateContextError(TemplateError):
    """Exception about template context """


class Node:
    def __init__(self):
        self.children = None

    def render(self, ctx: dict) -> str:
        raise NotImplementedError

    def render_children(self, ctx: dict, children: Optional[List['Node']] = None) -> str:
        return ''.join(child.render(ctx) for child in (children or self.children or []))

    def eval_expr(self, expr: str, ctx: dict) -> Any:
        if '|' in expr:
            ep, *pipes = expr.split('|')
            value = self.eval_expr(ep.strip(), ctx)
            for pipe in map(str.strip, pipes):
                func = ctx.get(pipe)
                if not func:
                    raise TemplateSyntaxError(f'Missing pipe function: {pipe}')
                value = func(value)
            return value
        elif '.' in expr:
            ep, *attrs = expr.split('.')
            value = ctx.get(ep)
            if not value:
                raise TemplateSyntaxError(f'Cannot resolve: "{ep}"')
            for attr in attrs:
                try:
                    value = getattr(value, attr)
                except AttributeError:
                    value = value[attr]
            return value
        else:
            return ctx.get(expr)


class RootNode(Node):
    def __init__(self, children: List[Node]) -> None:
        super().__init__()
        self.children = children

    def render(self, ctx: dict) -> str:
        return self.render_children(ctx)


class TextNode(Node):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def render(self, ctx: dict) -> str:
        return self.text

    def __repr__(self):
        return '<{}: {!r}>'.format(self.__class__.__name__, self.text[0:min(20, len(self.text))] + '...')


class CommentNode(Node):
    def __init__(self, comment: str) -> None:
        super().__init__()
        self.comment = comment

    def render(self, ctx: dict) -> str:
        return ''


class ExpressionNode(Node):
    def __init__(self, expr: str) -> None:
        super().__init__()
        self.expr = expr

    def render(self, ctx: dict) -> str:
        return str(self.eval_expr(self.expr, ctx))

    def __repr__(self) -> str:
        return '<{}: {}>'.format(self.__class__.__name__, self.expr)


class ForNode(Node):
    Loop = namedtuple('Loop', ['length', 'index0', 'index', 'first', 'last'])

    def __init__(self, statement: str, children: List[Node]) -> None:
        super().__init__()
        self.statement = statement
        self.children = children

    def render(self, ctx: dict) -> str:
        _, var_name, _, expr = self.statement.split()
        values = self.eval_expr(expr, ctx)
        length = len(values)

        output = []
        for idx, value in enumerate(values):
            loop = self.Loop(length, idx, idx + 1, idx == 0, idx == length - 1)
            new_ctx = ChainMap({'loop': loop, var_name: value})
            output.append(self.render_children(new_ctx, self.children))
        return ''.join(output)


class IfNode(Node):
    def __init__(self, expr: str, children: List[Node]) -> None:
        super().__init__()
        self.expr = expr
        self.children = children

    def render(self, ctx: dict) -> str:
        matched = self.eval_expr(self.expr, ctx)
        matched_children = []

        for child in self.children:
            if matched:
                if isinstance(child, (ElifNode, ElseNode)):
                    break
                else:
                    matched_children.append(child)
            else:
                if isinstance(child, ElifNode):
                    matched = self.eval_expr(child.expr, ctx)
                elif isinstance(child, ElseNode):
                    matched = True

        return self.render_children(ctx, matched_children)


class ElifNode(Node):
    def __init__(self, expr: str) -> None:
        super().__init__()
        self.expr = expr

    def render(self, ctx: dict) -> str:
        raise NotImplementedError


class ElseNode(Node):
    def render(self, ctx: dict) -> str:
        raise NotImplementedError


class TextReader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def find(self, target: str, start: int = 0, end: int = None) -> int:
        pos = self.pos
        start += pos
        if end is None:
            index = self.text.find(target, start)
        else:
            end += pos
            index = self.text.find(target, start, end)
        if index != -1:
            index -= pos
        return index

    def consume(self, count: int = None) -> str:
        if count is None:
            count = self.remaining()
        new_pos = self.pos + count
        s = self.text[self.pos:new_pos]
        self.pos = new_pos
        return s

    def remaining(self) -> int:
        return len(self.text) - self.pos

    def __len__(self) -> int:
        return self.remaining()

    def __getitem__(self, key) -> str:
        if key < 0:
            return self.text[key]
        else:
            return self.text[self.pos + key]

    def __str__(self) -> str:
        return self.text[self.pos:]


def find_curly(reader: TextReader) -> int:
    # Find the next template directive: {{, {# or {%.
    curly = 0
    while True:
        curly = reader.find("{", curly)

        if curly == -1 or curly + 1 == reader.remaining():
            return -1
        # If the first { is not the start of a special token,
        # start searching from the character after it.
        if reader[curly + 1] not in ("{", "%", "#"):
            curly += 1
            continue
        # When there are more than 2 { in a row, use the innermost ones.
        if (
            curly + 2 < reader.remaining() and
            reader[curly + 1] == '{' and
            reader[curly + 2] == '{'
        ):
            curly += 1
            continue

        return curly


def parse(reader: TextReader, in_block=None) -> List[Node]:
    children: List[Node] = []
    while True:
        curly = find_curly(reader)
        # If it's end of file
        if curly == -1:
            if in_block:
                raise TemplateSyntaxError("Missing {%% end %%} block for %s" % in_block)
            else:
                # Append the rest text
                children.append(TextNode(reader.consume()))
                return children
        # If a template directive was found
        else:
            # Append any text before the special token
            children.append(TextNode(reader.consume(curly)))

        start_brace = reader.consume(2)

        # Expression
        if start_brace == "{{":
            end = reader.find("}}")
            if end == -1 or reader.find("\n", 0, end) != -1:
                raise TemplateSyntaxError("Missing end tag for expression }}")
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                raise TemplateSyntaxError("Empty expression")
            children.append(ExpressionNode(contents))
        # Comment
        elif start_brace == "{#":
            end = reader.find("#}")
            if end == -1 or reader.find("\n", 0, end) != -1:
                raise TemplateSyntaxError("Missing end tag for comment }}")
            contents = reader.consume(end).strip()
            reader.consume(2)
            children.append(CommentNode(contents))
        # Block
        elif start_brace == "{%":
            end = reader.find("%}")
            if end == -1 or reader.find("\n", 0, end) != -1:
                raise TemplateSyntaxError("Missing end tag for block %}")
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                raise TemplateSyntaxError("Empty block tag ({% %})")
            operator, space, suffix = contents.partition(" ")
            # End tag
            if operator.startswith("end"):
                if not in_block:
                    raise TemplateSyntaxError("Extra {% end %} block")
                return children
            elif operator in ('elif', 'else'):
                if operator == 'elif':
                    children.append(ElifNode(suffix))
                else:
                    children.append(ElseNode())
            elif operator in ('if', 'for',):
                # parse inner body recursively
                block_body = parse(reader, operator)
                if operator == 'for':
                    block = ForNode(contents, block_body)
                else:
                    block = IfNode(suffix, block_body)
                children.append(block)
            else:
                raise TemplateSyntaxError("Unknown operator: %r" % operator)


class Template:
    def __init__(self, **options):
        self.options = options

    def render(self, text: str, **ctx):
        root = RootNode(parse(TextReader(text)))
        pprint(root.children)
        return root.render(ctx)


if __name__ == '__main__':
    with open('./example1.html', 'rt') as fp:
        content = fp.read()

    context = {
        'user': 'neo',
        'msg': 'Keep calm and carry on!',
        'books': [
            {'rank': 1, 'title': 'APUE'},
            {'rank': 2, 'title': 'CSAPP'},
            {'rank': 3, 'title': 'SICP'},
            {'rank': 4, 'title': 'UNP'},
        ],
        'upper': str.upper,
    }
    template = Template()
    print(template.render(content, **context))
