from template_to_py import Template as Template1

ctx = {
    'user': 'neo',
    'msg': 'Keep calm and carry on!',
    'books': [
        {'rank': 1, 'title': 'APUE'},
        {'rank': 2, 'title': 'CSAPP'},
        {'rank': 3, 'title': 'SICP'},
        {'rank': 4, 'title': 'UNP'},
    ]
}
tpl1 = Template1()
with open('./example.html', 'rt') as fp:
    text = fp.read()

print(tpl1.render(text, **ctx))
