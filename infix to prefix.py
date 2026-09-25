def precedence(op):
    """
    Returns operator precedence. 
    Higher return value means higher priority.
    """
    if op in ('+', '-'):
        return 1
    if op in ('*', '/'):
        return 2
    if op == '^':
        return 3
    return 0

def infix_to_postfix(tokens):
    """
    Standard Shunting-Yard Algorithm to convert infix tokens into postfix.
    """
    output = []  
    stack = []   
    
    for token in tokens:

        if token.isalnum():
            output.append(token)
            

        elif token == '(':
            stack.append(token)
            

        elif token == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            if stack:
                stack.pop()  
                

        else:

            while (stack and stack[-1] != '(' and 
                   precedence(stack[-1]) >= precedence(token)):
                output.append(stack.pop())

            stack.append(token)
            

    while stack:
        output.append(stack.pop())
        
    return output

def infix_to_prefix(expression):

    tokens = expression.split()
    

    reversed_tokens = []
    for token in reversed(tokens):
        if token == '(':
            reversed_tokens.append(')')
        elif token == ')':
            reversed_tokens.append('(')
        else:
            reversed_tokens.append(token)
            

    postfix_tokens = infix_to_postfix(reversed_tokens)
    

    prefix_tokens = list(reversed(postfix_tokens))
    
    return " ".join(prefix_tokens)



test_cases = [
    "( A + B ) * C",                       
    "A + B * C",                           
    "( A + B ) * ( C - D )",               
    "A + B * C - D / E",                  
    "( ( A * B ) + ( C / D ) ) ^ E"        
]

print(f"{'Infix Expression':<35} | {'Prefix Result'}")
print("-" * 60)

for expr in test_cases:
    result = infix_to_prefix(expr)
    print(f"{expr:<35} | {result}")