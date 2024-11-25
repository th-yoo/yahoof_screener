from enum import Enum, auto

class TokenType(Enum):
    # Define token types as enumeration members
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()
    AND = '&&'
    OR = '||'
    #BETWEEN = 'BETWEEN'
    EQUAL = '=='
    LESS = '<' 
    GREATER = '>'
    LPAREN = '('
    RPAREN = ')'
    LBRACKET = '['
    RBRACKET = ']'
    COLON = ':'
    EOF = auto()


class Token:
    def __init__(self, token_type, value=None):
        self.type = token_type
        self.value = value
        if self.value is None:
            self.value = self.type.value

class Scanner:
    def __init__(self, text):
        self.text = text
        self.pos = 0

    def scan_tokens(self):
        tokens = []
        while self.pos < len(self.text):
            if self.text[self.pos].isspace():
                self.pos += 1
                continue
            elif self.text[self.pos].isdigit() or self.text[self.pos] == '.':
                tokens.append(self.scan_number())
            elif self.text[self.pos] == '"':
                tokens.append(self.scan_string())
            elif self.text[self.pos].isalpha():
                tokens.append(self.scan_identifier())
            elif self.text[self.pos:self.pos+2] == '&&':
                tokens.append(Token(TokenType.AND))
                self.pos += 2
            elif self.text[self.pos:self.pos+2] == '||':
                tokens.append(Token(TokenType.OR))
                self.pos += 2
            elif self.text[self.pos] == '[':
                tokens.append(Token(TokenType.LBRACKET))
                self.pos += 1
            elif self.text[self.pos] == ']':
                tokens.append(Token(TokenType.RBRACKET))
                self.pos += 1
            elif self.text[self.pos] == ':':
                tokens.append(Token(TokenType.COLON, ':'))
                self.pos += 1
            elif self.text[self.pos:self.pos + 2] == '==':
                tokens.append(Token(TokenType.EQUAL))
                self.pos += 2
            elif self.text[self.pos] == '<':
                tokens.append(Token(TokenType.LESS))
                self.pos += 1
            elif self.text[self.pos] == '>':
                tokens.append(Token(TokenType.GREATER))
                self.pos += 1
            elif self.text[self.pos] == '(':
                tokens.append(Token(TokenType.LPAREN))
                self.pos += 1
            elif self.text[self.pos] == ')':
                tokens.append(Token(TokenType.RPAREN))
                self.pos += 1
            else:
                raise ValueError(f"Unexpected character: {self.text[self.pos]}")
        tokens.append(Token(TokenType.EOF, ''))
        return tokens

    def scan_number(self):
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isdigit() or self.text[self.pos] == '.'):
            self.pos += 1
            
        suffix = ''
        if self.pos < len(self.text) and self.text[self.pos].upper() in ('K', 'M', 'B', 'T'):
            suffix = self.text[self.pos].upper()
            self.pos += 1
        
        # Convert the number to a float
        num_str = self.text[start:self.pos]
        number = float(num_str[:-1]) if suffix else float(num_str)
        
        # Scale the number based on the suffix
        if suffix == 'K':
            number *= 1_000
        elif suffix == 'M':
            number *= 1_000_000
        elif suffix == 'B':
            number *= 1_000_000_000
        elif suffix == 'T':
            number *= 1_000_000_000_000
            
        return Token(TokenType.NUMBER, number)

    def scan_string(self):
        self.pos += 1  # Skip opening quote
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] != '"':
            self.pos += 1
        if self.pos == len(self.text):
            raise ValueError("Unterminated string")
        value = self.text[start:self.pos]
        self.pos += 1  # Skip closing quote
        return Token(TokenType.STRING, value)

    def scan_identifier(self):
        start = self.pos
        while self.pos < len(self.text) and (self.text[self.pos].isalnum() or self.text[self.pos] == '_'):
            self.pos += 1
        return Token(TokenType.IDENTIFIER, self.text[start:self.pos])


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0

    def parse(self):
        return self.to_dict(self.or_expr())

    def to_dict(self, expr):
        if isinstance(expr, tuple):
            operator = expr[0]
            if operator in ('or', 'and', 'btwn'):
                return {
                    "operator": operator,
                    "operands": [self.to_dict(operand) for operand in expr[1:]]
                }
            elif operator in (
                TokenType.EQUAL,
                TokenType.LESS,
                TokenType.GREATER,
            ):
                return {
                    "operator": self.operator_to_string(operator),
                    "operands": [self.to_dict(expr[1]), self.to_dict(expr[2])]
                }
        elif isinstance(expr, (int, float)):
            return expr
        elif isinstance(expr, str):
            return expr if expr[0] != '"' else expr[1:-1]  # Remove quotes for string literals
        return expr  # For identifiers

    def operator_to_string(self, token_type):
        mnemonic = {
            TokenType.EQUAL:    'eq',
            TokenType.LESS:     'lt',
            TokenType.GREATER:  'gt',
        }
        return mnemonic[token_type]

    def or_expr(self):
        expr = self.and_expr()
        while self.match(TokenType.OR):
            right = self.and_expr()
            expr = ('or', expr, right)
        return expr

    def and_expr(self):
        expr = self.comparison_expr()
        while self.match(TokenType.AND):
            right = self.comparison_expr()
            expr = ('and', expr, right)
        return expr

    def comparison_expr(self):
        expr = self.between_expr()
        while self.match(TokenType.EQUAL, TokenType.LESS, TokenType.GREATER):
            operator = self.previous().type
            right = self.between_expr()
            expr = (operator, expr, right)
        return expr

    def between_expr(self):
        expr = self.primary()
        if self.match(TokenType.LBRACKET):  # Check for opening bracket
            operator = self.previous().type
            lower = self.primary()
            self.consume(TokenType.COLON, "Expect ':' in BETWEEN expression.")
            upper = self.primary()
            self.consume(TokenType.RBRACKET, "Expect ']' after BETWEEN expression.")
            return ('btwn', expr, lower, upper)
        return expr

    def primary(self):
        if self.match(TokenType.NUMBER):
            return float(self.previous().value)
        if self.match(TokenType.STRING):
            return self.previous().value
        if self.match(TokenType.IDENTIFIER):
            return self.previous().value
        if self.match(TokenType.LPAREN):
            expr = self.or_expr()
            self.consume(TokenType.RPAREN, "Expect ')' after expression.")
            return expr
        raise ValueError("Expect expression.")

    def match(self, *types):
        #print(f'match')
        for type in types:
            #print('', type, self.peek().type)
            if self.check(type):
                #print('', type, 'is matched')
                self.advance()
                return True
        return False

    def check(self, type):
        if self.is_at_end():
            return False
        return self.peek().type == type

    def advance(self):
        if not self.is_at_end():
            self.current += 1
        return self.previous()

    def is_at_end(self):
        return self.peek().type == TokenType.EOF

    def peek(self):
        return self.tokens[self.current]

    def previous(self):
        return self.tokens[self.current - 1]

    def consume(self, type, message):
        if self.check(type):
            return self.advance()
        raise ValueError(message)


def parse_screener_expr(text):
    scanner = Scanner(text)
    tokens = scanner.scan_tokens()
    parser = Parser(tokens)
    return parser.parse()


# Example usage
if __name__ == "__main__":
    expressions = [
        'dayvolume [1M:5M]',
        'dayvolume < 10M',
        'dayvolume > 10M',
        'dayvolume == "test"',
        'dayvolume > 1.5M && dayvolume < 5M',
        'dayvolume[1.5M: 5M] && eodprice > 50',
        '50 < eodprice',
    ]

    for expr in expressions:
        print(f"Expression: {expr}")
        print(f"Parsed: {parse_screener_expr(expr)}")
        print()
