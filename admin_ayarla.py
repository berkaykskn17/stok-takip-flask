import sqlite3

con = sqlite3.connect("stok.db")
cur = con.cursor()

cur.execute("UPDATE kullanicilar SET rol = 'admin' WHERE kullanici_adi = 'admin'")
print("✅ admin yetkisi verildi.")

con.commit()
con.close()
