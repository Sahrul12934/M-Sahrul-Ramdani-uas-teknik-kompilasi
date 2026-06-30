# Dokumentasi Tugas UAS — Representasi Tahapan Kompilasi

```
Nama       : M. Sahrul Ramdani
NIM        : 231011400290
Kelas      : 06TPLE006
```

## 1. Konstruksi yang Dipilih
**Perulangan (Looping) — `for` statement**, dengan bentuk:

```
for ( init ; condition ; update ) { statements }
```

Contoh konkret yang dipakai sebagai studi kasus:

```
for ( i = 0 ; i < 5 ; i = i + 1 ) { sum = sum + i ; }
```

## 2. Pattern / Tata Bahasa (BNF)

```
<for_stmt>   ::= "for" "(" <init> ";" <condition> ";" <update> ")" "{" <stmt_list> "}"
<init>       ::= <id> "=" <number>
<condition>  ::= <id> <relop> <number>
<update>     ::= <id> "=" <id> <addop> <number>
<stmt_list>  ::= <statement> { <statement> }
<statement>  ::= <id> "=" <expr> ";"
<expr>       ::= <id> [ <addop> ( <id> | <number> ) ]
<relop>      ::= "<" | ">" | "<=" | ">=" | "==" | "!="
<addop>      ::= "+" | "-"
```

Pola ini membatasi cakupan tugas agar tetap sederhana: `init` dan `update` hanya boleh
mengubah satu variabel kontrol, `condition` membandingkan variabel kontrol dengan sebuah
literal angka, dan badan loop (`stmt_list`) berisi satu atau lebih statement penugasan
sederhana (`id = id [op (id|num)]`).

## 3. Implementasi Program

Program ditulis dalam Python (`compiler.py`) dan dibagi menjadi empat tahap sesuai topik
mata kuliah Teknik Kompilasi.

### 3.1 Analisis Leksikal
Fungsi `lexical_analysis()` menggunakan satu *master regex* yang dibangun dari beberapa
pasangan (nama token, pola regex) di `TOKEN_SPEC`. String sumber dipindai dari kiri ke
kanan; setiap kecocokan menghasilkan objek `Token(type, value)`. Token yang dikenali:
`FOR`, `ID`, `NUM`, `RELOP`, `ASSIGN`, `ADDOP`, `LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`,
`SEMI`. Spasi/tab/baris baru (`SKIP`) dibuang. Token `ID` yang nilainya persis `"for"`
diberi label ulang menjadi `FOR` (keyword).

### 3.2 Analisis Sintaksis (AST)
Dipakai pendekatan **recursive-descent parser** (`Parser`). Parser mengonsumsi token satu
per satu sesuai urutan grammar `<for_stmt>`, dengan method `eat(type)` yang memverifikasi
tipe token saat ini sama dengan yang diharapkan. Hasil akhirnya adalah pohon AST sederhana:

* `ForNode` — akar pohon, menyimpan `init`, `condition`, `update`, dan `body`.
* `AssignNode` — merepresentasikan satu statement penugasan `target = left [op right]`.
* `condition` disimpan sebagai tuple `(variabel, relop, nilai)`.

### 3.3 Analisis Semantik
Fungsi `semantic_analysis()` melakukan pengecekan dasar berbasis *symbol table* (`set`
nama variabel yang sudah "dideklarasikan"):

1. Variabel kontrol pada `init`, `condition`, dan `update` harus sama (mencegah loop yang
   tidak konsisten, mis. `for (i=0; j<5; i=i+1)`).
2. Setiap operand yang berupa variabel (bukan literal angka) harus sudah ada di symbol
   table sebelum dipakai — baik berasal dari parameter `known_vars` (variabel yang
   diasumsikan sudah dideklarasikan di luar loop) maupun dari variabel kontrol loop itu
   sendiri.
3. Jika ditemukan variabel yang belum dideklarasikan, program melempar `SemanticError`.

Pengujian kasus gagal disertakan di `compiler.py`: variabel `j` dipakai padahal tidak
pernah dideklarasikan, sehingga `SemanticError` berhasil ditangkap.

### 3.4 Generasi Kode Antara (Three-Address Code)
Kelas `TACGenerator` menghasilkan TAC mengikuti pola standar penerjemahan loop `for` pada
buku teks kompilasi (mirip pendekatan Aho/Sethi/Ullman):

```
<init>
L1:
t1 = <kondisi negasi>
if t1 goto L2
<body>
<update>
goto L1
L2:
```

Relop pada `condition` dinegasikan (`<` → `>=`, `<=` → `>`, dst.) supaya cabang `if`
mengarah keluar loop ketika kondisi asli sudah tidak terpenuhi — pola umum pada generasi
kode untuk struktur kontrol. Setiap ekspresi biner (`left op right`) dipecah menjadi
variabel sementara (`t1`, `t2`, ...) agar setiap instruksi TAC memiliki paling banyak satu
operator, sesuai definisi *three-address code*.

## 4. Contoh Hasil Eksekusi

Input:
```
for ( i = 0 ; i < 5 ; i = i + 1 ) { sum = sum + i ; }
```

Token (potongan):
```
[<FOR:for>, <LPAREN:(>, <ID:i>, <ASSIGN:=>, <NUM:0>, <SEMI:;>, <ID:i>, <RELOP:<>, <NUM:5>, ...]
```

AST:
```
ForNode(
  init=i = 0,
  condition=('i', '<', '5'),
  update=i = i + 1,
  body=[sum = sum + i]
)
```

Hasil Three-Address Code:
```
i = 0
L1:
t1 = i >= 5
if t1 goto L2
t2 = sum + i
sum = t2
t3 = i + 1
i = t3
goto L1
L2:
```

## 5. Cara Menjalankan
```bash
python3 compiler.py
```
Program akan mencetak hasil tiap tahap kompilasi secara berurutan untuk kasus valid,
diikuti dengan contoh kasus yang sengaja melanggar aturan semantik untuk menunjukkan
bahwa validasi bekerja.

## 6. Struktur File
```
.
├── compiler.py     # implementasi lexer, parser, semantic checker, dan TAC generator
└── dokumentasi.md  # dokumen penjelasan ini
```
