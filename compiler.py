"""
Tugas Proyek Akhir - Representasi Tahapan Kompilasi
Konstruksi yang dipilih : Perulangan (For Loop)

Nama       : M. Sahrul Ramdani
NIM        : 231011400290
Kelas      : 06TPLE006

Tahapan yang disimulasikan:
1. Analisis Leksikal  -> tokenisasi
2. Analisis Sintaksis  -> pembentukan AST (recursive descent parser)
3. Analisis Semantik   -> validasi deklarasi variabel & kesesuaian tipe sederhana
4. Generasi Kode Antara -> Three-Address Code (TAC)

Pola tata bahasa (BNF) konstruksi for-loop:

    <for_stmt>   ::= "for" "(" <init> ";" <condition> ";" <update> ")" "{" <stmt_list> "}"
    <init>       ::= <id> "=" <number>
    <condition>  ::= <id> <relop> <number>
    <update>     ::= <id> "=" <id> <addop> <number>
    <stmt_list>  ::= <statement> { <statement> }
    <statement>  ::= <id> "=" <expr> ";"
    <expr>       ::= <id> [ <addop> ( <id> | <number> ) ]
    <relop>      ::= "<" | ">" | "<=" | ">=" | "==" | "!="
    <addop>      ::= "+" | "-"
"""

import re


# ---------------------------------------------------------------------------
# 1. ANALISIS LEKSIKAL
# ---------------------------------------------------------------------------
class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"<{self.type}:{self.value}>"


TOKEN_SPEC = [
    ("FOR",     r"for"),
    ("ID",      r"[A-Za-z_][A-Za-z0-9_]*"),
    ("NUM",     r"\d+"),
    ("RELOP",   r"==|!=|<=|>=|<|>"),
    ("ASSIGN",  r"="),
    ("ADDOP",   r"\+|-"),
    ("LPAREN",  r"\("),
    ("RPAREN",  r"\)"),
    ("LBRACE",  r"\{"),
    ("RBRACE",  r"\}"),
    ("SEMI",    r";"),
    ("SKIP",    r"[ \t\n]+"),
]

MASTER_RE = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


def lexical_analysis(source_code):
    """Memecah source_code menjadi daftar token."""
    tokens = []
    pos = 0
    while pos < len(source_code):
        match = MASTER_RE.match(source_code, pos)
        if not match:
            raise SyntaxError(f"Karakter tidak dikenali pada posisi {pos}: '{source_code[pos]}'")
        kind = match.lastgroup
        value = match.group()
        pos = match.end()
        if kind == "SKIP":
            continue
        if kind == "ID" and value == "for":
            kind = "FOR"
        tokens.append(Token(kind, value))
    tokens.append(Token("EOF", None))
    return tokens


# ---------------------------------------------------------------------------
# 2. ANALISIS SINTAKSIS -> AST
# ---------------------------------------------------------------------------
class AssignNode:
    """Node untuk statement: id = expr  (expr berupa id [op (id|num)])"""
    def __init__(self, target, left, op, right):
        self.target = target  # nama variabel tujuan
        self.left = left      # operand kiri
        self.op = op          # operator ('+','-') atau None jika tidak ada
        self.right = right    # operand kanan atau None

    def __repr__(self):
        if self.op:
            return f"{self.target} = {self.left} {self.op} {self.right}"
        return f"{self.target} = {self.left}"


class ForNode:
    """Node akar AST untuk konstruksi for-loop."""
    def __init__(self, init, condition, update, body):
        self.init = init            # AssignNode
        self.condition = condition  # tuple (var, relop, value)
        self.update = update        # AssignNode
        self.body = body            # list[AssignNode]

    def __repr__(self):
        return (f"ForNode(\n  init={self.init},\n  condition={self.condition},\n"
                f"  update={self.update},\n  body={self.body}\n)")


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def eat(self, type_):
        tok = self.current()
        if tok.type != type_:
            raise SyntaxError(f"Diharapkan token {type_} tetapi mendapat {tok.type} ('{tok.value}')")
        self.pos += 1
        return tok

    def parse_assignment(self):
        """<id> = <expr> [;]   dipakai untuk init, update, dan statement di body"""
        target = self.eat("ID").value
        self.eat("ASSIGN")
        left = self.current()
        if left.type == "ID":
            left_val = self.eat("ID").value
        else:
            left_val = self.eat("NUM").value
        op = None
        right_val = None
        if self.current().type == "ADDOP":
            op = self.eat("ADDOP").value
            right_tok = self.current()
            if right_tok.type == "ID":
                right_val = self.eat("ID").value
            else:
                right_val = self.eat("NUM").value
        return AssignNode(target, left_val, op, right_val)

    def parse_condition(self):
        var = self.eat("ID").value
        relop = self.eat("RELOP").value
        val = self.current()
        if val.type == "ID":
            value = self.eat("ID").value
        else:
            value = self.eat("NUM").value
        return (var, relop, value)

    def parse_for(self):
        self.eat("FOR")
        self.eat("LPAREN")
        init = self.parse_assignment()
        self.eat("SEMI")
        condition = self.parse_condition()
        self.eat("SEMI")
        update = self.parse_assignment()
        self.eat("RPAREN")
        self.eat("LBRACE")

        body = []
        while self.current().type != "RBRACE":
            stmt = self.parse_assignment()
            self.eat("SEMI")
            body.append(stmt)
        self.eat("RBRACE")

        return ForNode(init, condition, update, body)


def syntax_analysis(tokens):
    parser = Parser(tokens)
    ast = parser.parse_for()
    if parser.current().type != "EOF":
        raise SyntaxError("Terdapat token tersisa setelah parsing selesai.")
    return ast


# ---------------------------------------------------------------------------
# 3. ANALISIS SEMANTIK
# ---------------------------------------------------------------------------
class SemanticError(Exception):
    pass


def semantic_analysis(ast, known_vars=None):
    """
    Validasi sederhana:
    - Variabel kontrol pada init, condition, dan update harus sama.
    - Setiap variabel yang dipakai (selain literal angka) harus sudah
      'dideklarasikan' (muncul sebagai target assignment sebelumnya atau
      termasuk dalam known_vars yang diasumsikan sudah ada).
    - Update harus mengubah variabel kontrol itu sendiri (mencegah infinite loop trivial).
    """
    symbol_table = set(known_vars) if known_vars else set()

    # variabel kontrol loop dideklarasikan oleh init
    symbol_table.add(ast.init.target)

    if ast.init.target != ast.condition[0]:
        raise SemanticError(
            f"Variabel kontrol tidak konsisten: init memakai '{ast.init.target}' "
            f"tetapi condition memakai '{ast.condition[0]}'"
        )
    if ast.init.target != ast.update.target:
        raise SemanticError(
            f"Variabel kontrol tidak konsisten: init memakai '{ast.init.target}' "
            f"tetapi update memakai '{ast.update.target}'"
        )

    def check_operand(name):
        if not name.isdigit() and name not in symbol_table:
            raise SemanticError(f"Variabel '{name}' digunakan sebelum dideklarasikan.")

    check_operand(ast.condition[2])
    check_operand(ast.update.left)
    if ast.update.right is not None:
        check_operand(ast.update.right)

    for stmt in ast.body:
        check_operand(stmt.left)
        if stmt.right is not None:
            check_operand(stmt.right)
        # variabel hasil assignment otomatis menjadi terdeklarasi (mendukung akumulator)
        symbol_table.add(stmt.target)

    return True


# ---------------------------------------------------------------------------
# 4. GENERASI KODE ANTARA (THREE-ADDRESS CODE)
# ---------------------------------------------------------------------------
class TACGenerator:
    def __init__(self):
        self.temp_counter = 1
        self.label_counter = 1
        self.code = []

    def new_temp(self):
        t = f"t{self.temp_counter}"
        self.temp_counter += 1
        return t

    def new_label(self):
        l = f"L{self.label_counter}"
        self.label_counter += 1
        return l

    def emit(self, instr):
        self.code.append(instr)

    def gen_assign(self, node):
        if node.op:
            temp = self.new_temp()
            self.emit(f"{temp} = {node.left} {node.op} {node.right}")
            self.emit(f"{node.target} = {temp}")
        else:
            self.emit(f"{node.target} = {node.left}")

    def generate(self, ast: ForNode):
        # init
        self.gen_assign(ast.init)

        label_start = self.new_label()
        label_end = self.new_label()

        self.emit(f"{label_start}:")

        # negasi relop untuk uji keluar loop
        negate = {"<": ">=", ">": "<=", "<=": ">", ">=": "<", "==": "!=", "!=": "=="}
        var, relop, val = ast.condition
        neg_relop = negate[relop]
        temp_cond = self.new_temp()
        self.emit(f"{temp_cond} = {var} {neg_relop} {val}")
        self.emit(f"if {temp_cond} goto {label_end}")

        # body
        for stmt in ast.body:
            self.gen_assign(stmt)

        # update
        self.gen_assign(ast.update)

        self.emit(f"goto {label_start}")
        self.emit(f"{label_end}:")

        return "\n".join(self.code)


# ---------------------------------------------------------------------------
# KELAS PEMBUNGKUS (mengikuti pola contoh tugas)
# ---------------------------------------------------------------------------
class ForLoopCompiler:
    def __init__(self, source_code, known_vars=None):
        self.source_code = source_code
        self.known_vars = known_vars or []

    def run(self):
        print("=== SOURCE CODE ===")
        print(self.source_code)

        print("\n--- 1. Analisis Leksikal (Token) ---")
        tokens = lexical_analysis(self.source_code)
        print(tokens)

        print("\n--- 2. Analisis Sintaksis (AST) ---")
        ast = syntax_analysis(tokens)
        print(ast)

        print("\n--- 3. Analisis Semantik ---")
        semantic_analysis(ast, known_vars=self.known_vars)
        print("Valid: semua variabel terdeklarasi & variabel kontrol konsisten.")

        print("\n--- 4. Generasi Three-Address Code (TAC) ---")
        generator = TACGenerator()
        tac = generator.generate(ast)
        print(tac)
        return tac


# ---------------------------------------------------------------------------
# CONTOH PENGGUNAAN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    source = "for ( i = 0 ; i < 5 ; i = i + 1 ) { sum = sum + i ; }"
    compiler = ForLoopCompiler(source, known_vars=["sum"])
    compiler.run()

    print("\n\n=== Contoh kasus gagal semantik (variabel belum dideklarasikan) ===")
    bad_source = "for ( i = 0 ; i < 5 ; i = i + 1 ) { total = total + j ; }"
    bad_compiler = ForLoopCompiler(bad_source, known_vars=["total"])
    try:
        bad_compiler.run()
    except SemanticError as e:
        print(f"SemanticError tertangkap: {e}")
