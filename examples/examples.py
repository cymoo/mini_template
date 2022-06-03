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


if __name__ == '__main__':
    test_ast_template()
