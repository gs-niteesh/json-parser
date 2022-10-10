from enum import Enum
from typing import List

import pprint
import sys

class JSONTokenType(Enum):
    BEGIN_OBJECT    = 1,
    BEGIN_ARRAY     = 2,
    END_ARRAY       = 3,
    END_OBJECT      = 4,
    NAME_SEPERATOR  = 5,
    VALUE_SEPERATOR = 6
    STRINGS         = 7,
    NUMBERS         = 8,
    NULL            = 9,
    TRUE            = 10,
    FALSE           = 11,


class NodeType(Enum):
    JSON_OBJECT = 1,
    JSON_ARRAY  = 2,
    JSON_INT    = 3,
    JSON_STRING = 4,

class Node:
    def __init__(self, type = None, children = []):
        self.type = type
        self.children = children

class JSONToken:
    def __init__(self, value: str, x: int, y: int, tokenType: JSONTokenType):
        self.x = x
        self.y = y
        self.value = value
        self.tokenType = tokenType

    def __repr__(self) -> str:
        return f'{{ type: {self.tokenType}, x: {self.x}, y: {self.y}, value: \'{self.value}\' }}'

    def __str__(self) -> str:
        return f'{{type: {self.tokenType}, x: {self.x}, y: {self.y}, value: {self.value}}}'

class JSONLexer:
    def __init__(self):
        self.x = 1
        self.y = 1
        self.cursor = 0
        self.buffer = []
        self.tokens: List[JSONToken] = []

    @property
    def len(self):
        return len(self.buffer)

    def update_cursor(self, char):
        if char == ' ' or char == '\t':
            self.x += 1
        elif char == '\n' or char == '\r':
            self.x = 1
            self.y += 1

    @property
    def current_char(self) -> str:
        return self.buffer[self.cursor]

    def append_token(self, value: str, tokenType: JSONTokenType):
        token = JSONToken(value, self.x, self.y, tokenType)
        self.tokens.append(token)

    def parse_number(self) -> str:
        number = ''
        while self.cursor < self.len and self.current_char.isdigit():
            number += self.current_char
            self.cursor += 1
        return number

    def parse_strings(self) -> str:
        string = ''
        self.cursor += 1
        while self.cursor < self.len and self.current_char != '"':
            string += self.current_char
            self.cursor += 1

        if self.cursor >= self.len:
            raise Exception('Expected \" but got EOF')
        string += self.current_char
        self.cursor += 1
        return string

    def parse_val(self, value) -> str:
        idx = 0
        string = ''
        while self.cursor < self.len and idx < len(value):
            string += self.current_char
            self.cursor += 1
            idx += 1
        if string != value:
            raise Exception(f'Unexpected token {string} expected {value} at [{self.y}, {self.x}]')
        return string


    def parse_tfn(self) -> str:
        if self.current_char.lower() == 't':
            return self.parse_val('true')
        elif self.current_char.lower() == 'n':
            return self.parse_val('null')
        elif self.current_char.lower() == 'f':
            return self.parse_val('false')
        raise Exception(f'Unexpected value {self.current_char} at [{self.y}, {self.x}]')


    def lex(self, buffer):
        self.buffer = buffer
        while self.cursor < self.len:
            char = self.current_char

            if char.isspace():
                self.update_cursor(char)
                self.cursor += 1
                continue
            elif char == '{':
                self.append_token(char, JSONTokenType.BEGIN_OBJECT)
                self.x += 1
            elif char == '}':
                self.append_token(char, JSONTokenType.END_OBJECT)
                self.x += 1
            elif char == '[':
                self.append_token(char, JSONTokenType.BEGIN_ARRAY)
                self.x += 1
            elif char == ']':
                self.append_token(char, JSONTokenType.END_ARRAY)
                self.x += 1
            elif char == ',':
                self.append_token(char, JSONTokenType.VALUE_SEPERATOR)
                self.x += 1
            elif char == ':':
                self.append_token(char, JSONTokenType.NAME_SEPERATOR)
                self.x += 1
            elif char == '"':
                string = '"' + self.parse_strings()
                self.append_token(string, JSONTokenType.STRINGS)
                self.x += len(string)
                self.cursor -= 1
            elif char.isalpha():
                string = self.parse_tfn()
                if string == 'true':
                    self.append_token(string, JSONTokenType.TRUE)
                elif string == 'false':
                    self.append_token(string, JSONTokenType.FALSE)
                elif string == 'null':
                    self.append_token(string, JSONTokenType.NULL)
                self.x += len(string)
                self.cursor -= 1
            elif char == '-' or char.isdigit():
                import re
                regex = r"^(-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)"
                matches = re.search(regex, self.buffer[self.cursor:])
                if not matches:
                    raise Exception("Expected a valid number token")
                assert len(matches.groups()) == 1
                number = matches.group(1)
                self.append_token(number, JSONTokenType.NUMBERS)
                self.x += len(number)
                self.cursor += len(number) - 1
            self.cursor += 1

        return self.tokens

class JSONParser:
    def __init__(self):
        self.tokens = []
        self.cursor = 0

    @property
    def len(self):
        return len(self.tokens)

    @property
    def current_token(self) -> JSONToken:
        return self.tokens[self.cursor]

    def expect_one_of_token(self, tokenList):
        if self.current_token.tokenType not in tokenList:
            msg = f'Expected token one of {tokenList} but got {self.current_token.tokenType}' \
                   ' at [{self.current_token.y}, {self.current_token.x}]'
            raise Exception(msg)

    def expect_token(self, tokenType):
        if self.current_token.tokenType != tokenType:
            msg = f'Expected token {tokenType} but got {self.current_token.tokenType}' \
                  f' at [{self.current_token.y}, {self.current_token.x}]'
            raise Exception(msg)

    def consume_token(self, tokenType):
        if isinstance(tokenType, List):
            self.expect_one_of_token(tokenType)
        else:
            self.expect_token(tokenType)
        self.cursor += 1

    def parse_array(self) -> Node:
        children = []

        self.consume_token(JSONTokenType.BEGIN_ARRAY)
        children.append(self.parse_value())
        while self.current_token.tokenType != JSONTokenType.END_ARRAY and self.cursor < self.len:
            self.consume_token(JSONTokenType.VALUE_SEPERATOR)
            children.append(self.parse_value())
        self.consume_token(JSONTokenType.END_ARRAY)

        return Node(NodeType.JSON_ARRAY, children)

    def parse_object(self) -> str:
        children = []

        self.consume_token(JSONTokenType.BEGIN_OBJECT)
        children.append(self.parse_member())
        while self.current_token.tokenType != JSONTokenType.END_OBJECT and self.cursor < self.len:
            self.consume_token(JSONTokenType.VALUE_SEPERATOR)
            children.append(self.parse_member())
        self.consume_token(JSONTokenType.END_OBJECT)

        return Node(NodeType.JSON_OBJECT, children)

    def parse_member(self) -> str:
        arr = ''

        token = self.current_token
        self.consume_token(JSONTokenType.STRINGS)
        arr += token.value

        token = self.current_token
        self.consume_token(JSONTokenType.NAME_SEPERATOR)
        arr += token.value

        token = self.current_token
        arr += self.parse_value()

        return arr

    def parse_value(self) -> str:
        token = self.current_token
        VALID_TOKEN_TYPES = [JSONTokenType.FALSE, JSONTokenType.TRUE,
                             JSONTokenType.NULL, JSONTokenType.NUMBERS,
                             JSONTokenType.STRINGS, JSONTokenType.BEGIN_OBJECT,
                             JSONTokenType.BEGIN_ARRAY]

        if token.tokenType not in VALID_TOKEN_TYPES:
            raise Exception(f'Unexpected token {token.value} at [{token.y}, {token.x}]')

        match token.tokenType:
            case JSONTokenType.BEGIN_OBJECT:
                return self.parse_object()
            case JSONTokenType.BEGIN_ARRAY:
                return self.parse_array()
            case _:
                self.cursor += 1
                return token.value

    def parse(self, tokens: List[JSONToken]):
        self.tokens = tokens
        value = self.parse_value()
        if self.cursor < self.len:
            token = self.current_token
            raise Exception(f'Expected EOF but got {token.tokenType} at [{token.y}, {token.x}]')
        return value


def parse_file(path):
    with open(path, 'r') as f:
        data = f.read()
        tokens = None
        try:
            tokens = JSONLexer().lex(data)
            JSONParser().parse(tokens)
            print ('Parse Complete')
        except Exception as e:
            pprint.pprint(tokens)
            print (e)
            sys.exit(1)

def parse_value(value):
    lexer = JSONLexer()
    tokens = lexer.lex(value)

    import sys
    if len(sys.argv) >= 2 and sys.argv[1] == 'd':
        pprint.pprint(tokens)

    parser = JSONParser()

    print(parser.parse(tokens))

if __name__ == "__main__":
    path = sys.argv[1]
    parse_file(path)
