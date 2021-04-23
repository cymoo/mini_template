from pprint import pprint
from typing import List


class TemplateError(Exception):
    pass


class TemplateSyntaxError(TemplateError):
    pass


class TemplateContextError(TemplateError):
    pass


class Node:
    def __init__(self):
        pass

    def before_render(self):
        pass

    def render(self, ctx: dict) -> str:
        raise NotImplementedError

    def after_render(self):
        pass


class RootNode(Node):
    def __init__(self, children: List[Node]) -> None:
        super().__init__()
        self.children = children

    def render(self, ctx: dict) -> str:
        return ''.join(child.render(ctx) for child in self.children)


class TextNode(Node):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

    def render(self, ctx: dict) -> str:
        return self.value

    def __repr__(self):
        return '<{}: {!r}>'.format(self.__class__.__name__, self.value[0:min(20, len(self.value))] + '...')


class CommentNode(Node):
    def __init__(self, comment: str) -> None:
        super().__init__()
        self.comment = comment

    def render(self, ctx: dict) -> str:
        return ''


class ExprNode(Node):
    def __init__(self, expr: str) -> None:
        super().__init__()
        self.expr = expr

    def render(self, ctx: dict) -> str:
        return str(eval(self.expr))

    def eval_expr(self):
        pass

    def __repr__(self) -> str:
        return '<{}: {}>'.format(self.__class__.__name__, self.expr)


class BlockNode(Node):
    def __init__(self, statement: str, children: List[Node]) -> None:
        super().__init__()
        self.statement = statement
        self.children = children

    def render(self, ctx: dict) -> str:
        return ''

    def __repr__(self):
        return '<{}: {}>'.format(self.__class__.__name__, self.statement)


class IfNode(BlockNode):
    pass


class ElifNode(BlockNode):
    pass


class ElseNode(BlockNode):
    pass


class ForNode(BlockNode):
    pass


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


def parse(reader: TextReader, in_block=None) -> List[Node]:
    # body = _ChunkList([])
    children = []
    while True:
        # Find next template directive
        curly = 0
        while True:
            curly = reader.find("{", curly)
            if curly == -1 or curly + 1 == reader.remaining():
                # EOF
                if in_block:
                    raise TemplateSyntaxError("Missing {%% end %%} block for %s" % in_block)
                # body.chunks.append(_Text(reader.consume()))
                children.append(TextNode(reader.consume()))
                # return body
                return children
            # If the first curly brace is not the start of a special token,
            # start searching from the character after it
            if reader[curly + 1] not in ("{", "%", "#"):
                curly += 1
                continue
            # When there are more than 2 curlies in a row, use the
            # innermost ones.  This is useful when generating languages
            # like latex where curlies are also meaningful
            if (curly + 2 < reader.remaining() and
                    reader[curly + 1] == '{' and reader[curly + 2] == '{'):
                curly += 1
                continue
            break

        # Append any text before the special token
        if curly > 0:
            # body.chunks.append(_Text(reader.consume(curly)))
            children.append(TextNode(reader.consume(curly)))

        start_brace = reader.consume(2)

        # Expression
        if start_brace == "{{":
            end = reader.find("}}")
            if end == -1 or reader.find("\n", 0, end) != -1:
                raise TemplateSyntaxError("Missing end expression }}")
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                raise TemplateSyntaxError("Empty expression")
            # body.chunks.append(_Expression(contents))
            children.append(ExprNode(contents))
            continue

        # Comment
        # ...

        # Block
        assert start_brace == "{%", start_brace
        end = reader.find("%}")
        if end == -1 or reader.find("\n", 0, end) != -1:
            raise TemplateSyntaxError("Missing end block %}")
        contents = reader.consume(end).strip()
        reader.consume(2)
        if not contents:
            raise TemplateSyntaxError("Empty block tag ({% %})")
        operator, space, suffix = contents.partition(" ")
        # End tag
        # if operator == "end":
        if operator.startswith("end"):
            if not in_block:
                raise TemplateSyntaxError("Extra {% end %} block")
            return children
        elif operator in ("try", "if", 'elif', 'else', "for", "while"):
            # parse inner body recursively
            block_body = parse(reader, operator)
            block = BlockNode(contents, block_body)
            # body.chunks.append(block)
            children.append(block)
            # continue
        else:
            raise TemplateSyntaxError("unknown operator: %r" % operator)


class Template:
    def __init__(self, **options):
        self.options = options

    def render(self, text: str, **ctx):
        pass


if __name__ == '__main__':
    with open('./example1.html', 'rt') as fp:
        content = fp.read()

    result = RootNode(parse(TextReader(content)))
    pprint(result.children)
