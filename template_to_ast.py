import re


# Utils


def html_escape(s):
    """ Escape HTML special characters ``&<>`` and quotes ``'"``. """
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;') \
        .replace('"', '&quot;').replace("'", '&#039;')


def html_unescape(s):
    """Unescape HTML special characters."""
    return str(s).replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>') \
        .replace('&quot;', '"').replace('&#039;', "'")


class TemplateError(Exception):
    pass


class TemplateSyntaxError(TemplateError):
    pass


class TemplateContextError(TemplateError):
    pass


TOKEN_PATTERN = re.compile(r'({{.*?}}|{%.*?%}|{#.*?#})')
