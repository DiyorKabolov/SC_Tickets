import os
import re
patterns = [
    re.compile(p) for p in [
        rb'\xc3\xa2\xe2\x80\x9c',
        rb'\xc3\xa2\xe2\x80\x99',
        rb'\xc3\xa2\xe2\x80\x9d',
        rb'\xc3\xa2\xe2\x80\x93',
        rb'\xc3\xa2\xe2\x80\xb0',
        rb'\xc3\xa2\xe2\x80\xb2',
        rb'\xc3\xa2\xe2\x80\xb6',
        rb'\xc3\xa2\xe2\x80\x94',
        rb'\xc3\xa2\xe2\x80\xae',
        rb'\xc3\xa2\xe2\x80\xa6',
        rb'\xc3\xa2\xe2\x80\x98',
        rb'\xc3\xa2\xe2\x80\x9a',
        rb'\xc3\xa2\xe2\x80\x9e',
        rb'\xc3\xa2\xe2\x80\xa0',
        rb'\xc3\x82',
        rb'\xc3\x84',
        rb'\xc3\x89',
        rb'\xc3\x8d',
    ]
]
for root, dirs, files in os.walk('.'):
    for name in files:
        if not name.lower().endswith(('.py', '.txt', '.md', '.html', '.jinja2', '.css', '.js')):
            continue
        path = os.path.join(root, name)
        try:
            data = open(path, 'rb').read()
        except Exception as e:
            print('ERR', path, e)
            continue
        lines = data.splitlines()
        for i, line in enumerate(lines, 1):
            if any(pat.search(line) for pat in patterns):
                print(f'{path}:{i}: {line.decode("utf-8", errors="replace")}')
