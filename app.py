from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

from functools import wraps

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("rol") != "admin":
            return "❌ Bu işlem için admin yetkisi gereklidir."
        return f(*args, **kwargs)
    return wrapper


app = Flask(__name__)
app.secret_key = "gizli_anahtar"

# Veritabanını oluştur
def init_db():
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        # Kullanıcılar tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kullanicilar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi TEXT UNIQUE NOT NULL,
                sifre TEXT NOT NULL
            )
        """)
        # Ürünler tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS urunler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_adi TEXT NOT NULL,
                kategori TEXT,
                miktar INTEGER,
                fiyat REAL
            )
        """)
        # Satışlar tablosu
        cur.execute("""
            CREATE TABLE IF NOT EXISTS satislar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_id INTEGER NOT NULL,
                miktar INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                FOREIGN KEY (urun_id) REFERENCES urunler(id)
            )
        """)
        con.commit()

@app.route("/")
def index():
    if "kullanici" not in session:
        return redirect(url_for("giris"))
    
    q = request.args.get("q", "")
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        if q:
            cur.execute("SELECT * FROM urunler WHERE urun_adi LIKE ?", ('%' + q + '%',))
        else:
            cur.execute("SELECT * FROM urunler")
        urunler = cur.fetchall()
    return render_template("index.html", urunler=urunler, q=q)

@app.route("/giris", methods=["GET", "POST"])
def giris():
    hata = None  # 💡 Hata mesajı tutulacak
    if request.method == "POST":
        kullanici_adi = request.form["kullanici_adi"]
        sifre = request.form["sifre"]
        with sqlite3.connect("stok.db") as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM kullanicilar WHERE kullanici_adi=? AND sifre=?", (kullanici_adi, sifre))
            kullanici = cur.fetchone()

        if kullanici:
            session["kullanici"] = kullanici_adi
            session["rol"] = kullanici[3]
            return redirect("/")
        else:
            hata = "⚠️ Kullanıcı adı veya şifre hatalı"

    return render_template("giris.html", hata=hata)




@app.route("/kayit", methods=["GET", "POST"])
def kayit():
    hata = None
    mesaj = None
    if request.method == "POST":
        kullanici_adi = request.form["kullanici_adi"]
        sifre = request.form["sifre"]
        
        with sqlite3.connect("stok.db") as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM kullanicilar WHERE kullanici_adi = ?", (kullanici_adi,))
            if cur.fetchone():
                hata = "Bu kullanıcı adı zaten kayıtlı!"
            else:
                cur.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", (kullanici_adi, sifre))
                con.commit()
                mesaj = "Kayıt başarılı! Şimdi giriş yapabilirsiniz."
    return render_template("kayit.html", hata=hata, mesaj=mesaj)

@app.route("/ekle", methods=["POST"])
@admin_required
def ekle():
    urun_adi = request.form["urun_adi"]
    kategori = request.form["kategori"]
    miktar = request.form["miktar"]
    fiyat = request.form["fiyat"]
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        cur.execute("INSERT INTO urunler (urun_adi, kategori, miktar, fiyat) VALUES (?, ?, ?, ?)",
                    (urun_adi, kategori, miktar, fiyat))
        con.commit()
    return redirect("/")


from datetime import datetime

@app.route("/sat", methods=["POST"])
def sat():
    urun_id = int(request.form["urun_id"])   # ← EKLENDİ
    miktar = int(request.form["miktar"])

    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()

        # Ürün kontrolü ve stok miktarı al
        cur.execute("SELECT miktar FROM urunler WHERE id = ?", (urun_id,))
        urun = cur.fetchone()
        if not urun:
            return "Ürün bulunamadı."

        mevcut_miktar = urun[0]
        if mevcut_miktar < miktar:
            return "Yetersiz stok!"

        # Stok güncelle
        cur.execute("UPDATE urunler SET miktar = miktar - ? WHERE id = ?", (miktar, urun_id))

        # Satışı kaydet
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO satislar (urun_id, miktar, tarih) VALUES (?, ?, ?)",
            (urun_id, miktar, tarih)
        )

        con.commit()

    return redirect("/")




@app.route("/sil/<int:id>")
@admin_required
def sil(id):
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        cur.execute("DELETE FROM urunler WHERE id = ?", (id,))
        con.commit()
    return redirect("/")

@app.route("/duzenle/<int:id>")
@admin_required
def duzenle_form(id):
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM urunler WHERE id = ?", (id,))
        urun = cur.fetchone()
    return render_template("duzenle.html", urun=urun)

@app.route("/guncelle/<int:id>", methods=["POST"])
def guncelle(id):
    urun_adi = request.form["urun_adi"]
    kategori = request.form["kategori"]
    miktar = request.form["miktar"]
    fiyat = request.form["fiyat"]
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        cur.execute("""
            UPDATE urunler SET urun_adi = ?, kategori = ?, miktar = ?, fiyat = ?
            WHERE id = ?
        """, (urun_adi, kategori, miktar, fiyat, id))
        con.commit()
    return redirect("/")

@app.route("/cikis")
def cikis():
    session.pop("kullanici", None)
    return redirect(url_for("giris"))

@app.route("/rapor")
def rapor():
    if "kullanici" not in session:
        return redirect(url_for("giris"))

    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM urunler")
        toplam_urun = cur.fetchone()[0]

        cur.execute("SELECT SUM(miktar) FROM urunler")
        toplam_miktar = cur.fetchone()[0] or 0

        cur.execute("SELECT SUM(miktar * fiyat) FROM urunler")
        toplam_deger = cur.fetchone()[0] or 0

        cur.execute("SELECT urun_adi, miktar FROM urunler ORDER BY miktar DESC LIMIT 1")
        en_cok_stokta = cur.fetchone()

        cur.execute("SELECT urun_adi, fiyat FROM urunler ORDER BY fiyat DESC LIMIT 1")
        en_pahali_urun = cur.fetchone()

    return render_template("rapor.html", toplam_urun=toplam_urun,
                           toplam_miktar=toplam_miktar,
                           toplam_deger=toplam_deger,
                           en_cok_stokta=en_cok_stokta,
                           en_pahali_urun=en_pahali_urun)

@app.route("/satislar")
def satislar():
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        cur.execute("""
            SELECT s.id, u.urun_adi, s.miktar, s.tarih
            FROM satislar s
            JOIN urunler u ON s.urun_id = u.id
            ORDER BY s.tarih DESC
        """)
        satislar = cur.fetchall()
    return render_template("satislar.html", satislar=satislar)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

import bcrypt

def kullanici_ekle(kullanici_adi, sifre):
    with sqlite3.connect("stok.db") as con:
        cur = con.cursor()
        # Şifreyi hashle
        hashed_sifre = bcrypt.hashpw(sifre.encode('utf-8'), bcrypt.gensalt())
        try:
            cur.execute("INSERT INTO kullanicilar (kullanici_adi, sifre) VALUES (?, ?)", 
                        (kullanici_adi, hashed_sifre))
            con.commit()
        except sqlite3.IntegrityError:
            print("Bu kullanıcı adı zaten kayıtlı.")


