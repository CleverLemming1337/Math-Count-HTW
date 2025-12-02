from typing import Union, List
import math
import discord
import datetime
import os

COUNTING_CHANNEL_ID = 1445504113470341212

allowed_digits = {"1", "2", "3", "4", "5", "6"}
allowed_operators = {"+", "-", "*", "/", "^", "!"}

class ParsingError(Exception):
    def __init__(self, char: str, msg: str):
        self.char = char
        self.msg = msg

    def __str__(self) -> str:
        if len(self.char) > 0:
            return f"Fehler bei Zeichen {self.char}: {self.msg}"
        return f"Fehler: {self.msg}"

class Parser:
    def __init__(self, text: str):
        self.text = text
        self.i = 0
        self.len = len(text)
        self.used_digits = set()

    def _peek(self) -> str:
        return self.text[self.i] if self.i < self.len else ""

    def _next(self) -> str:
        ch = self._peek()
        self.i += 1
        return ch

    def _skip_spaces(self):
        while self._peek().isspace() or self._peek() == "`":
            self._next()

    def parse_expression(self) -> float:
        # expression := term ((+|-) term)*
        val = self.parse_term()
        while True:
            self._skip_spaces()
            ch = self._peek()
            if ch in ("+", "-"):
                op = self._next()
                rhs = self.parse_term()
                if op == "+":
                    val = val + rhs
                else:
                    val = val - rhs
            else:
                break
        return val

    def parse_term(self) -> float:
        # term := power ((*|/) power)*
        val = self.parse_power()
        while True:
            self._skip_spaces()
            ch = self._peek()
            if ch in ("*", "/"):
                op = self._next()
                rhs = self.parse_power()
                if op == "*":
                    val = val * rhs
                else:
                    if rhs == 0:
                        raise ParsingError("/", "Division durch 0")
                    val = val / rhs
            else:
                break
        return val

    def parse_power(self) -> float:
        # power := factor (^ power)?
        val = self.parse_factor()
        self._skip_spaces()
        if self._peek() == "^":
            self._next()
            rhs = self.parse_power()  # right-associative
            try:
                val = val ** rhs
            except Exception as e:
                raise ParsingError("^", f"Ungültige Potenz: {e}")
        return val

    def parse_factor(self) -> float:
        # factor := primary ('!')*
        val = self.parse_primary()
        self._skip_spaces()
        while self._peek() == "!":
            self._next()
            # factorial only defined for non-negative integers
            if not float(val).is_integer() or val < 0:
                raise ParsingError("!", "Fakultät auf nicht-ganze oder negative Zahl angewendet.")
            n = int(val)
            try:
                val = math.factorial(n)
            except Exception as e:
                raise ParsingError("!", f"Fakultätfehler: {e}")
            self._skip_spaces()
        return val

    def parse_primary(self) -> float:
        # primary := DIGIT | '(' expression ')'
        self._skip_spaces()
        ch = self._peek()
        if ch == "(":
            self._next()
            val = self.parse_expression()
            self._skip_spaces()
            if self._peek() != ")":
                raise ParsingError(")", "Schließende Klammer erwartet.")
            self._next()
            return val
        if ch.isdigit():
            digit = self._next()
            if digit not in allowed_digits:
                raise ParsingError(digit, "Unzulässige Ziffer.")
            if digit in self.used_digits:
                raise ParsingError(digit, "Ziffer mehrfach verwendet.")
            self.used_digits.add(digit)
            return float(int(digit))
        if ch == "":
            raise ParsingError("", "Unerwartetes Ende der Eingabe. Wert erwartet.")
        raise ParsingError(ch, "Ungültiges Zeichen. Wert erwartet.")

def parse(text: str) -> Union[int, float]:
    """
    Parse and evaluate expression like "5*(4+3)+6!".
    Rules:
    - Allowed digits: 1-6
    - Each digit may appear at most once
    - Allowed operators: + - * / ^ !
    - Parentheses allowed
    - On error raise ParsingError with informative message
    - On success return numeric value (int if whole number)
    """
    parser = Parser(text)
    val = None
    try:
        parser._skip_spaces()
        if parser.i >= parser.len:
            raise ParsingError("", "Leere Eingabe.")
        val = parser.parse_expression()
        parser._skip_spaces()
        if parser.i != parser.len:
            # leftover characters
            raise ParsingError(parser._peek(), "Zusätzliche Zeichen nach gültigem Ausdruck.")
    except ParsingError:
        raise
    # return int if integer-valued
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val

# =================================================================================================

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

current_count = 0
game_started = False
cooldown_until = None
last_player_id = None
current_highscore = 0
current_highscore_player_name = None

async def end_game(message, text: str, cooldown: int):
    global current_count, game_started, cooldown_until, last_player_id, current_highscore, current_highscore_player_name
    await message.add_reaction("❌")
    await message.channel.send(text)
    await message.channel.send(
        f"Das Spiel ist vorbei. Ihr seid bis `{current_count}` gekommen. Danke fürs Mitspielen! Nächster Versuch in {cooldown} Minuten."
    )

    current_count = 0
    game_started = False
    cooldown_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
        minutes=cooldown
    )
    last_player_id = None

@bot.event
async def on_ready():
    channel = bot.get_channel(COUNTING_CHANNEL_ID)
    if channel is not None:
        await channel.send("Mal sehen, wie weit ihr diesmal kommt. Schafft ihr `6^4 + 5 * (3! + 2) + 1`?\nTippe `?rules`, um die Regeln zu sehen.")
    
@bot.event
async def on_message(message):
    global current_count, game_started, cooldown_until, last_player_id, current_highscore, current_highscore_player_name
    if message.author == bot.user or message.content[0] == "\\":
        return
    if message.channel.id == COUNTING_CHANNEL_ID:
        if message.content == "?rules" or message.content == "?help":
            await message.channel.send("""
**Regeln**
1. Ihr zählt gemeinsam von 1 beginnend.
2. Schickt eine Nachricht mit einem mathematischen Ausdruck, um zu zählen.
3. Die einzigen zulässigen Operanden sind die Ziffern 1-6.
4. Die einzigen zulässigen Operatoren sind `+ - * / ^ !`.
5. Klammern mit `()` sind erlaubt.
6. Jede Nachricht, die nicht mit `?` oder `\\` beginnt, wird ausgewertet.
7. Nachrichten dürfen von Backticks (`) umschlossen sein.
8. Ein Spieler darf nicht mehrmals hintereinander zählen.
9. Um diese Regeln anzuzeigen, `?rules` eingeben.
            """)
            return
        if message.content == "?highscore":
            if current_highscore == 0:
                await message.channel.send("Ihr habt es schon sehr weit geschafft: `0`. Fang doch einfach an.")
                return
            await message.channel.send(f"Highscore: `{current_highscore}`, erreicht von {current_highscore_player_name}")
            return
        if message.content[0] in ["?", "\\"]:
            return
        # Check cooldown
        if cooldown_until is not None:
            now = datetime.datetime.now(datetime.timezone.utc)
            if now < cooldown_until:
                remaining = cooldown_until - now
                await message.add_reaction("⏳")
                remaining_seconds = round(remaining.total_seconds())
                if remaining_seconds > 3 * 60:
                    remaining_text = f"~{round(remaining_seconds / 60)} Minuten"
                else:
                    remaining_text = f"~{remaining_seconds}s"
                await message.channel.send(
                    f"Cooldown aktiv. Versuch's in {remaining_text} wieder"
                )
                return
            else:
                cooldown_until = None

        # Check game start
        if not game_started:
            if message.content.strip().lower() == "start":
                game_started = True
                await message.channel.send("Na endlich. Spiel läuft. Fangt bei `3-2` an. Oder `1`, wenn ihr faul seid.")
                return
            else:
                await message.add_reaction("⏸️")
                await message.channel.send("Tippe `start`, um ein neues Spiel zu beginnen.")
                return
        
        # Parse expression
        try:
            # Check double turn
            if last_player_id is not None and message.author.id == last_player_id:
                await message.add_reaction("❌")
                await end_game(
                    message,
                    f"{message.author.mention} `4/2` Züge hintereinander? Das hier ist kein Solo.",
                    cooldown=max(2, current_count + 1),
                )
                return
            
            new_value = parse(message.content.strip())
            if new_value == current_count + 1:
                current_count += 1
                last_player_id = message.author.id

                if current_count > current_highscore:
                    current_highscore = current_count
                    current_highscore_player_name = message.author.display_name
                await message.add_reaction("✅")
            else:
                await end_game(
                    message,
                    f"{message.author.mention} Wer genau zählen kann, ist klar im Vorteil. {message.content} = {new_value}. Erwartet: {current_count + 1}",
                    cooldown=max(2, current_count + 1)
                )
        except ParsingError as error:
            await end_game(message, f"{error}", cooldown=max(2, current_count + 1))

bot.run(os.environ["TOKEN"])