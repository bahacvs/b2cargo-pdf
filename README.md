# b2cargo-pdf — Perfetti Van Melle E-İrsaliye Bölge Ayırma Agentı (MVP)

Perfetti Van Melle'den vardiya başına gelen **ayrı ayrı irsaliye PDF'lerini**
(her dosya = bir irsaliye) otomatik okuyup, her dosyanın **sevk adresinden**
bölgesini tespit eder ve her bölge için **tek bir birleşik PDF** üretir.
Çıktı, B2Cargo → OCR sürecine hazırdır.

> Bu, projenin **1. fazı (lokal CLI MVP)**'dir. E-posta entegrasyonu, OCR,
> dev@mbar, ATF ve barkod sonraki fazlara bırakılmıştır.

## Kurulum

> **İşyeri bilgisayarı (Windows) için:** Teknik bilgi gerektirmeyen, çift
> tıklamayla kurulum rehberi → **[KURULUM_WINDOWS.md](KURULUM_WINDOWS.md)**
> (`kur.bat` ile kur, `calistir.bat` ile çalıştır).

Geliştirici kurulumu:

```bash
cd b2cargo-pdf
pip install -e .            # çalıştırmak için
pip install -e ".[test]"    # testleri de çalıştırmak için
# veya sadece runtime bağımlılıkları:
pip install -r requirements.txt
```

## Kullanım

```bash
# workdir/Gelen_PDF içine tüm irsaliye PDF'lerini koyun, sonra:
python -m perfetti_splitter workdir/Gelen_PDF/ --name 2026-06-24_18-00_Vardiya
```

Çıktılar `workdir/Birlesik_PDF/<vardiya>/` altına yazılır:

```
2026-06-24_18-00_Vardiya/
├── Adana_24evrak.pdf
├── Ankara_31evrak.pdf
├── ...
├── Hata_3evrak.pdf       # bölge tespit edilemeyen / eksik alanlı belgeler
├── Hata_raporu.csv       # her hatalı dosya + nedeni
└── ozet.txt              # vardiya özeti
```

### Seçenekler

| Seçenek | Varsayılan | Açıklama |
|---------|-----------|----------|
| `input_dir` | — | İrsaliye PDF'lerinin bulunduğu klasör (zorunlu) |
| `--config` | `config/regions.yaml` | Bölge → şehir haritası |
| `--outdir` | `workdir/Birlesik_PDF` | Çıktı taban klasörü |
| `--name` | gelen klasör adı | Vardiya adı (çıktı alt klasörü) |

## "Tahmin yapma" ilkesi

Aşağıdaki durumlarda belge bir bölgeye **zorlanmaz**, `Hata`'ya gönderilir:
PVS kodu yok · belge numarası yok · sevk adresi okunamadı · bölge bulunamadı ·
birden çok bölgeye eşleşme (ör. **Bilecik** hem Ankara hem Aytop'ta).

## Bölge haritası (`config/regions.yaml`)

Tek doğruluk kaynağıdır; kodda gömülü değildir. Resmi B2Cargo haritasıyla
doğrulamak için yalnızca bu dosyayı güncelleyin — kod değişmez.

## Testler

```bash
pytest
```

Testler sentetik PDF'lerle (reportlab) çalışır; gerçek vardiya PDF'i geldiğinde
`config/regions.yaml` ve `perfetti_splitter/parser.py` içindeki regex/etiketler
kalibre edilir.

## Mimari

```
perfetti_splitter/
├── extractor.py   PDF → metin (pdfplumber)
├── parser.py      PVS / belge no / adres çıkarımı
├── regions.py     TR normalizasyon + bölge tespiti
├── splitter.py    bölge başına PDF birleştirme (pypdf)
├── pipeline.py    uçtan uca akış
├── report.py      özet + hata raporu
└── cli.py         komut satırı
```
