from tree_sitter import Node, Parser, Language, TreeCursor

Language.build_library(
    'build/json-language.so',
    ['tree-sitter-json']
)

JSON_LANGUAGE = Language('build/json-language.so', 'json')

parser = Parser()
parser.set_language(JSON_LANGUAGE)

def read_file(path):
    data = ''
    with open(path, 'r') as f:
        data = f.read()
    return data

tree = parser.parse(bytes(read_file('test.json'), encoding='utf-8'))

cursor = tree.walk()

def visit(cursor: TreeCursor, indent = 0):
    node = cursor.node
    print (f'{" " * indent}(type: {node.type}, value: {node.text})\n')
    if cursor.goto_first_child():
        visit(cursor, indent + 4)
        cursor.goto_parent()
    while cursor.goto_next_sibling():
        visit(cursor, indent)


visit(cursor)