# İşyeri Bilgisayarına Kurulum (Windows)

Bu rehber, Perfetti vardiya irsaliyelerini bölgelere ayıran programı bir
Windows bilgisayara kurmak içindir. **Teknik bilgi gerektirmez** — adımları
sırayla takip edin.

---

## ⭐ En Kolay Yol — Hazır program (.exe) (önerilen)

Bu yolda **Python kurmanıza gerek yoktur**, tek bir program dosyası indirip
çalıştırırsınız.

1. **https://github.com/bahacvs/b2cargo-pdf/releases** adresine gidin ve en
   üstteki sürümde **`PerfettiVardiyaAyirma.zip`** dosyasını indirin.
   - *(Henüz sürüm yoksa: repo → **Actions** → "Windows EXE Derle" → en son
     çalışmanın altındaki **Artifacts**'tan `PerfettiVardiyaAyirma.zip`.)*
2. ZIP'e sağ tıklayın → **Tümünü ayıkla**. Çıkan klasörü kolay bir yere
   taşıyın (örn. **`C:\Perfetti`**). İçinde şunlar olur:
   - `PerfettiVardiyaAyirma.exe` — program
   - `Gelen_PDF\` — PDF'leri buraya koyacaksınız
   - `config\regions.yaml` — bölge listesi (gerekirse Not Defteri ile düzenlenir)
3. Vardiya irsaliye PDF'lerinin **hepsini** `Gelen_PDF\` klasörüne kopyalayın.
4. **`PerfettiVardiyaAyirma.exe`** dosyasına **çift tıklayın** → açılan
   pencerede **AYIR** butonuna basın.
5. İşlem bitince özet görünür; **"Çıktı Klasörünü Aç"** ile sonuçları
   (`Birlesik_PDF\<vardiya>\`) açabilirsiniz.

> Windows "bilinmeyen yayıncı" uyarısı verirse: **Ek bilgi → Yine de çalıştır**.
>
> Sonraki vardiyalarda sadece 3–5. adımları tekrarlarsınız.

Aşağıdaki **Python ile kurulum** yalnızca geliştirici/yedek yoldur; hazır
`.exe` kullanıyorsanız gerekmez.

---

## 1. Adım — Python kurun (tek seferlik)

1. Tarayıcıda **https://www.python.org/downloads/** adresine gidin.
2. Sarı **“Download Python”** butonuna tıklayın, inen dosyayı çalıştırın.
3. ⚠️ **ÇOK ÖNEMLİ:** Açılan ilk ekranda en alttaki
   **“Add python.exe to PATH”** kutusunu **işaretleyin**.
4. **“Install Now”** deyin, kurulum bitince **Close** ile kapatın.

> Bu adımı yalnızca bir kez yaparsınız. Bilgisayarda Python zaten kuruluysa
> atlayabilirsiniz.

---

## 2. Adım — Programı indirin

1. **https://github.com/bahacvs/b2cargo-pdf** adresine gidin.
2. Sol üstteki dal (branch) menüsünden
   **`claude/test-coverage-analysis-ngrkaq`** dalını seçin.
3. Yeşil **`< > Code`** butonuna → **Download ZIP**.
4. İnen ZIP dosyasına sağ tıklayın → **Tümünü ayıkla** (Extract All).
5. Çıkan klasörü kolay bir yere taşıyın, örneğin **`C:\Perfetti`**.

---

## 3. Adım — Kurun (tek seferlik)

Klasörün içindeki **`kur.bat`** dosyasına **çift tıklayın**.

- Siyah bir pencere açılır ve gerekli parçaları indirir (internet gerekir).
- Sonunda **“KURULUM TAMAM”** yazısını görünce bir tuşa basıp pencereyi
  kapatın.

> Windows “bilinmeyen yayıncı” uyarısı verirse: **Ek bilgi → Yine de çalıştır**.

---

## 4. Adım — PDF'leri yerleştirin

Vardiya irsaliye PDF'lerinin **hepsini** şu klasöre kopyalayın:

```
<program klasörü>\workdir\Gelen_PDF\
```

> Her irsaliye ayrı bir PDF dosyasıdır; hepsini bu klasöre atın.

---

## 5. Adım — Çalıştırın

**`calistir.bat`** dosyasına **çift tıklayın**.

- Vardiya adı sorar — yazabilir (örn. `2026-06-24_18-00_Vardiya`) veya boş
  bırakıp Enter'a basabilirsiniz (otomatik tarih kullanılır).
- İşlem bitince ekranda bölge özetini görürsünüz ve **çıktı klasörü
  otomatik açılır**:

```
<program klasörü>\workdir\Birlesik_PDF\<vardiya>\
├── Adana\                ← bölge klasörü
│   ├── A101 ADANA - PVS2026000029867.pdf
│   └── GRATIS - ADANA DEPO - PVS2026000030031.pdf
├── Ankara\
│   └── A101 KAYSERI - PVS2026000029873.pdf
├── ...
├── Hata\                 ← bölgesi belirlenemeyen / eksik bilgili evraklar
│   ├── <sorunlu PDF'ler>
│   └── Hata_raporu.csv   ← her hatalı dosya + nedeni + okunan adres
└── ozet.txt              ← vardiya özeti
```

> **Çıktı:** Her bölge artık ayrı bir **klasör**; içinde irsaliyeler `{Alıcı} - {PVS}.pdf`
> adıyla ayrı ayrı durur (tek birleşik PDF yok).
>
> **Hata klasörü:** Bölgesi bulunamayan evraklar buraya gelir; `Hata_raporu.csv`
> her birinin nedenini ve okunan adresi gösterir. Eksik bir şehir varsa
> `config\regions.yaml`'a ekleyip, arayüzdeki **"Hata Klasörünü Tekrar Tara"**
> butonuyla bu evrakları yeniden işleyebilirsiniz.

Sonraki vardiyalarda sadece **4. ve 5. adımları** tekrarlarsınız.

> **Pencereli arayüz isterseniz:** `calistir.bat` yerine **`arayuz.bat`**'a çift
> tıklayın — yukarıdaki `.exe` ile aynı pencere açılır (klasör seç → AYIR).

---

## Sorun Giderme

**“Python bulunamadı” hatası**
→ 1. adımdaki **“Add python.exe to PATH”** kutusu işaretlenmemiş.
Python'u **Denetim Masası → Programlar**'dan kaldırıp, kutuyu işaretleyerek
yeniden kurun.

**`kur.bat` “Bağımlılıklar kurulamadı” diyor**
→ İnternet yok ya da kurumsal **proxy/güvenlik duvarı** engelliyor olabilir.

- *Proxy varsa* (IT'den proxy adresini öğrenin) komut isteminde:
  ```
  .venv\Scripts\python.exe -m pip install --proxy http://KULLANICI:SIFRE@PROXY:PORT -r requirements.txt
  ```
- *İnternet tamamen kapalıysa (çevrimdışı kurulum):* internet erişimli başka
  bir bilgisayarda program klasöründe şunu çalıştırıp paketleri toplayın:
  ```
  pip download -r requirements.txt -d wheelhouse
  ```
  `wheelhouse` klasörünü işyeri bilgisayarına kopyalayın ve orada:
  ```
  .venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements.txt
  ```

**`calistir.bat` “Gelen_PDF klasöründe hiç PDF bulunamadı” diyor**
→ 4. adımı atlamışsınız; PDF'leri `workdir\Gelen_PDF\` içine kopyalayın.

**Bir bölge eksik / yanlış**
→ Şehir–bölge eşlemesi `config\regions.yaml` dosyasındadır. Bu dosyayı Not
Defteri ile açıp düzeltebilirsiniz (kod değişmez). Belirsiz/eksik evraklar
güvenlik gereği tahmin edilmeden **Hata**'ya gönderilir.
