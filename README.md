# Duyuru Kontrol

Türkçe etkinlik duyurularında **tarih geçerli mi?**, **yazılan haftanın günü doğru mu?** ve
**metin belirlenen karakter sınırını aşıyor mu?** sorularını yerel olarak
denetleyen küçük bir Python aracı. Harici servise metin göndermez.

Örnek: `24 Eylül 2026 Çarşamba` yazıldığında doğru günün **Perşembe**
olduğunu bildirir. `31 Eylül 2026` gibi geçersiz tarihleri, haftanın günü
yazılmamış olsa da bildirir. Dosyada yıl yoksa `--year` verilmesini ister; sessizce
geçerli yılı varsaymaz.

## Kullanım

Python 3.11 veya yenisi gerekir. Başka çalışma bağımlılığı yoktur.

```bash
python -m duyuru_kontrol duyuru.txt --year 2026 --max-chars 1000
```

Paket olarak kurmak ve komutu kullanmak için:

```bash
python -m pip install .
duyuru-kontrol duyuru.txt --year 2026 --max-chars 1000
```

Standart girdiyi `-` ile okuyabilir, birden çok dosyayı kontrol edebilir ve
makine tarafından okunabilir JSON üretebilirsiniz:

```bash
printf '24 Eylül Perşembe' | python -m duyuru_kontrol - --year 2026 --format json
```

Yanlış gün veya karakter sınırı aşımı için çıkış kodu **1**, dosya/argüman
hatası için **2**, başarılı denetim için **0** döner.

## Kapsam ve sınırlar

- `24 Eylül Perşembe`, `24 Eylül 2026 Perşembe`,
  `24 Eylül Perşembe 2026` ve `24.09.2026 Perşembe` biçimlerini tanır.
  Gün adı olmayan `24 Eylül`, `24 Eylül 2026` ve `24.09.2026` biçimlerini de
  denetler. `24 Eylül` için açıkça `--year` verilmelidir.
- Tarihin takvimde geçerli olup olmadığını denetler; gün adı yazılmışsa ayrıca
  tarih-gün eşleşmesini karşılaştırır. Yılı belirtilmeyen tarihlerde mevcut yılı
  varsaymaz. `29 Şubat` gibi tarihler ancak yıl verilince doğrulanabilir.
- Ay adı tam yazılmalıdır; kısaltmalar, eğik çizgili tarihler ve yılı olmayan
  sayısal `24.09` biçimi desteklenmez. Denetlenen tarih adayı sayısını çıktıda
  gösterir; sıfır olması metindeki tüm tarihlerin doğrulandığı anlamına gelmez.
- `--max-chars`, Python'un Unicode karakter sayısını kullanır; dosyanın
  en sonundaki tek satır sonunu saymaz. **SMS parça sayısı veya operatör
  ücretlendirmesi hesaplamaz.** Kodlama ve Türkiye'deki operatör kuralları
  gerçek teslimat sınırını değiştirebilir. Bkz. [Türkiye için SMS
  kuralları](https://www.twilio.com/en-us/guidelines/tr/sms) ve
  [karakter/kodlama sınırları](https://www.twilio.com/docs/glossary/what-sms-character-limit).
- Metinde yıl yazılmışsa `--year` seçeneğinin değeri o yılla da uyuşmalıdır.

## Testler

```bash
python -m unittest discover -s tests -v
```

GitHub Actions bu testleri Python 3.11, 3.12 ve 3.13 üzerinde çalıştırır.
