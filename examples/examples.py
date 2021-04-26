from template_to_ast import Template

template = Template()
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