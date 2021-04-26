"""A simple template engine which compiles a template to AST."""
import os
from collections import ChainMap, namedtuple
from operator import eq, ne
from string import digits
from typing import List, Any, Optional, Sequence, MutableMapping

from utils import html_escape


class TemplateError(Exception):
    """Base exception class"""


class TemplateSyntaxError(TemplateError):
    """Exception for bad template syntax"""


class TemplateContextError(TemplateError):
    """Exception about template context"""


class Node:
    def __init__(self) -> None:
        self.children = None

    def render(self, ctx: MutableMapping) -> str:
        raise NotImplementedError

    def render_children(self, ctx: MutableMapping, children: Optional[List['Node']] = None) -> str:
        if children is None:
            children = self.children
        return ''.join(child.render(ctx) for child in children)

    def eval_expr(self, expr: str, ctx: MutableMapping) -> Any:
        expr = expr.strip()

        # If an expression begins with digits, convert it to int or float.
        if expr[0] in digits:
            try:
                if '.' in expr:
                    return float(expr)
                else:
                    return int(expr)
            except ValueError:
                raise TemplateSyntaxError('Invalid syntax {!r}'.format(expr))

        # If an expression begins with ' or ", it should be a str.
        if expr[0] in ('"', "'"):
            return expr[1:-1]

        if '|' in expr:
            ep, *pipes = expr.split('|')
            value = self.eval_expr(ep, ctx)
            for pipe in map(str.strip, pipes):
                func = ctx.get(pipe)
                if not func:
                    raise TemplateContextError('Cannot resolve {!r} in {!r}'.format(pipe, expr))
                value = func(value)
            return value
        elif '.' in expr:
            ep, *attrs = expr.split('.')
            value = ctx[ep]
            for attr in attrs:
                try:
                    value = getattr(value, attr)
                except AttributeError:
                    if isinstance(value, Sequence) and attr.isdigit():
                        value = value[int(attr)]
                    else:
                        value = value[attr]
            return value
        else:
            return ctx[expr]


class RootNode(Node):
    def __init__(self, children: List[Node]) -> None:
        super().__init__()
        self.children = children

    def render(self, ctx: MutableMapping) -> str:
        return self.render_children(ctx)


class TextNode(Node):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text

    def render(self, ctx: MutableMapping) -> str:
        return self.text


class CommentNode(Node):
    def __init__(self, comment: str) -> None:
        super().__init__()
        self.comment = comment

    def render(self, ctx: MutableMapping) -> str:
        return ''


class ExpressionNode(Node):
    def __init__(self, expr: str) -> None:
        super().__init__()
        self.expr = expr

    def render(self, ctx: MutableMapping) -> str:
        return str(self.eval_expr(self.expr, ctx))


class ForNode(Node):
    Loop = namedtuple('Loop', ['length', 'index0', 'index', 'first', 'last'])

    def __init__(self, statement: str, children: List[Node]) -> None:
        super().__init__()
        self.statement = statement
        self.children = children

    def render(self, ctx: MutableMapping) -> str:
        var_name, op, expr = self.statement.partition('in')
        if op != 'in':
            raise TemplateSyntaxError('Cannot understand {!r}'.format(self.statement))
        values = self.eval_expr(expr, ctx)
        length = len(values)

        output = []
        for idx, value in enumerate(values):
            loop = self.Loop(length, idx, idx + 1, idx == 0, idx == length - 1)
            new_ctx = ChainMap({'loop': loop, var_name.strip(): value}, ctx)
            output.append(self.render_children(new_ctx, self.children))
        return ''.join(output)


class IfNode(Node):
    def __init__(self, expr: str, children: List[Node]) -> None:
        super().__init__()
        self.expr = expr
        self.children = children

    def eval_expr(self, expr: str, ctx: MutableMapping) -> Any:
        ee = super().eval_expr
        if '==' in expr:
            lh, _, rh = expr.partition('==')
            return eq(ee(lh, ctx), ee(rh, ctx))
        elif '!=' in expr:
            lh, _, rh = expr.partition('!=')
            return ne(ee(lh, ctx), ee(rh, ctx))
        else:
            return ee(expr, ctx)

    def render(self, ctx: MutableMapping) -> str:
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

    def render(self, ctx: MutableMapping) -> str:
        raise NotImplementedError


class ElseNode(Node):
    def render(self, ctx: MutableMapping) -> str:
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
        curly = reader.find('{', curly)

        if curly == -1 or curly + 1 == reader.remaining():
            return -1
        # If the first { is not the start of a special token,
        # start searching from the character after it.
        if reader[curly + 1] not in ('{', '%', '#'):
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
                raise TemplateSyntaxError("Missing block tag '{{% end %}}' for {!r}".format(in_block))
            else:
                # Append the rest text
                children.append(TextNode(reader.consume()))
                return children
        # If a template directive was found
        else:
            # Append any text before the special token
            children.append(TextNode(reader.consume(curly)))

        directive = reader.consume(2)

        # Expression
        if directive == '{{':
            end = reader.find('}}')
            if end == -1 or reader.find('\n', 0, end) != -1:
                raise TemplateSyntaxError("Missing end tag '}}'")

            contents = reader.consume(end).strip()
            if not contents:
                raise TemplateSyntaxError('Empty expression')

            reader.consume(2)
            children.append(ExpressionNode(contents))
        # Comment
        elif directive == '{#':
            end = reader.find('#}')
            if end == -1 or reader.find('\n', 0, end) != -1:
                raise TemplateSyntaxError("Missing end tag '#}'")

            contents = reader.consume(end).strip()
            reader.consume(2)
            children.append(CommentNode(contents))
        # Block
        elif directive == '{%':
            end = reader.find('%}')
            if end == -1 or reader.find('\n', 0, end) != -1:
                raise TemplateSyntaxError("Missing end tag '%}'")

            contents = reader.consume(end).strip()
            if not contents:
                raise TemplateSyntaxError("Empty block tag '{% %}'")

            reader.consume(2)

            operator, _, suffix = contents.partition(' ')
            # End tag
            if operator.startswith('end'):
                if not in_block:
                    raise TemplateSyntaxError("Extra block tag '{% end %}'")
                return children
            elif operator in ('elif', 'else'):
                node = ElifNode(suffix) if operator == 'elif' else ElseNode()
                children.append(node)
            elif operator in ('if', 'for',):
                # parse inner body recursively
                block_body = parse(reader, operator)
                node_cls = ForNode if operator == 'for' else IfNode
                children.append(node_cls(suffix, block_body))
            else:
                raise TemplateSyntaxError('Unknown operator {!r}'.format(operator))


class Template:
    global_ctx = {'escape': html_escape}
    cache = {}

    def __init__(self, template_root: Optional[str] = None, **options) -> None:
        self.template_root = template_root
        self.options = options

    def render(self, filename: str, **ctx) -> str:
        if self.template_root:
            filename = os.path.join(self.template_root, filename)

        root_node = self.cache.get(filename)
        if root_node is None:
            with open(filename, 'rt') as fp:
                text = fp.read()
            root_node = RootNode(parse(TextReader(text)))
            self.cache[filename] = root_node

        return root_node.render(ChainMap(ctx, self.global_ctx))

    def render_str(self, text: str, **ctx) -> str:
        root_node = RootNode(parse(TextReader(text)))
        return root_node.render(ChainMap(ctx, self.global_ctx))

    @classmethod
    def update_global_ctx(cls, ctx: MutableMapping) -> None:
        cls.global_ctx.update(ctx)
