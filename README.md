# Math Count HTW
Discord bot for counting - but with math.

## Rules
1. The goal is to count as high as possible starting at 1.
2. To count, send a message with a mathematical expression.
3. The only allowed operands are the digits 1-6.
4. The only allowed operators are `+ - * / ^ !`.
5. Parenthesis with `()` are allowed.
6. Every message that does not start with `?` or `\\` is evaluated.
7. Messages may be enclosed by backticks (`).
8. A player may not count multiple times in a row.

## Example
If you are at `1336`, you could type

```
6^4 + 5 * (3! + 2) + 1
```

## Setup
- If needed: Adjust channel id
- Set bot Token in Environment
- Activate python virtual environment if needed
- `pip3 install -r requirements.txt` or `pip install -r requirements.txt` on Windows
- Start script