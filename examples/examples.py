import os
from template_to_ast import Template as AstTemplate
from template_to_py import Template as PyTemplate


def test_py_template():
    template = PyTemplate()
    text = """
    <h1>Hi, {% if user %}{{ user }}{% else %}traveler{% end %}</h1>
    <p>Fruit:</p>
    <ul>
      {% for item in fruit %}
      <li>{{ item }}</li>
      {% end %}
    </ul>
    """.strip()

    template.render(
        text,
        user='neo',
        fruit=['apple', 'banana']
    )


def test_ast_template():
    template = AstTemplate(os.path.dirname(__file__))
    result = template.render(
        './example.html',
        user={'name': 'neo', 'locations': ['shanghai', 'hangzhou']},
        msg='Keep calm and carry on!',
        books=[
            {'author': 'Harold Abelson', 'title': 'SICP'},
            {'author': 'Richard Stevens', 'title': 'APUE'},
            {'author': 'Randal E.Bryant', 'title': 'CS:APP'},
            {'author': 'Richard Stevens', 'title': 'UNP'},
        ],
        html_content='<script>alert("attack!")</script>'
    )
    print(result)


def test_ast_template1():
    tpl_str = """
    I am {{ name }}.
    
    {% if color == 'red' %} 
        Free your mind!
    {% else %}
        The story ends.
    {% endif %}
    
    {% for msg in messages %}
        {{ msg }}
    {% endfor %} 
    
    {% for item in ['hello', 'world'] %}
        {{loop.index}} - {{ item }}
    {% endfor %} 
    
    
    {% for item in [{'a': 1}, {'a': 3}] %}
        {{ item.a }}
    {% endfor %}
    
    {% for item in ['hello', 'world'] %}
        {{ loop.index }}: {{ item }}
        {% if loop.last %} ... {% endif %}
    {% endfor %}
    
    obj: {{ obj.a.b }}
    
    {% if !color %}
       ...
    {% endif %}
    """
    template = AstTemplate()
    result = template.render_str(
        tpl_str,
        name='Neo',
        color='red',
        messages=['Wake up, Neo...', 'The matrix has you...', 'Follow the white rabbit.'],
        obj={'a': {'b': 1}}
    )
    print(result)


if __name__ == '__main__':
    test_ast_template1()
