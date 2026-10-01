# Duyuru Kontrol

Türkçe etkinlik duyurularında **tarih/aralık geçerli mi?**, **yazılan haftanın günü doğru mu?** ve
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

### Aynı ay ve yıl içindeki tarih aralıkları

Tam Türkçe ay adıyla yazılan `24–25 Eylül 2026` gibi aralıkların iki uç
tarihini de denetler. `-`, `–` ve `—` ayraçlarını, çevrelerindeki boşluklarla
birlikte tanır: `24 - 25 Eylül 2026` ve `24 — 25 Eylül 2026` da geçerlidir.
Ay ve yıl iki uç için ortaktır. İki tarih de geçerliyse başlangıcın bitişten
sonra olup olmadığını kontrol eder; `24–24 Eylül 2026` geçerlidir.

| İfade | Sonuç |
| --- | --- |
| `24–25 Eylül 2026` | Geçerli |
| `31–24 Eylül 2026` | Başlangıç için `INVALID_DATE` |
| `25–24 Eylül 2026` | `REVERSED_RANGE` |
| `28–29 Şubat 2025` | Bitiş için `INVALID_DATE` |
| `28–29 Şubat 2024` | Artık yılda geçerli |
| `24–25 Eylül` | `YEAR_REQUIRED`; `--year 2026` verilirse geçerli |

Yıl kendiliğinden mevcut yıl olarak alınmaz. Metindeki yıl ile `--year`
çelişirse `YEAR_CONFLICT`, aynı ifadede iki yıl yazılırsa `AMBIGUOUS_YEAR`
verilir; bu yıl hataları giderilmeden takvim/sıralama kontrolü yapılmaz.
Takvim açısından geçersiz olan iki uç da ayrı ayrı bildirilir; uçlardan biri
geçersizse ayrıca sıralama hatası üretilmez. Geçersiz uç için hata konumu o
ucun gün sayısının başlangıcıdır. Aralığın geneline ait yıl, sıralama ve gün
adı belirsizliği hataları aralığın başlangıcında gösterilir.

`checked_dates`, **tanınan tarih adayı sayısıdır**, başarılı denetim sayısı
değildir. Her tekil tarih 1, her aralık 2 sayılır; uçlar aynı olsa, geçersiz
olsa veya yıl eksik/çelişkili olsa da bu sayım değişmez. Aralığın son tarihi
ayrıca eşleştirilip üçüncü kez sayılmaz. Örneğin `24–25 Eylül 2026;
26.09.2026` için değer 3'tür. Sayım, desteklenmeyen ifadelerin veya metindeki
tüm tarihler arasındaki ilişkilerin doğrulandığı anlamına gelmez.

Aralığa eklenen gün adı hangi uca ait olduğunu belirtmez: `24–25 Eylül 2026
Cuma`, `24–25 Eylül Cuma 2026` ve `24–25 Eylül 2026 Perşembe–Cuma` başarılı
kabul edilmez; `AMBIGUOUS_RANGE_WEEKDAY` bildirilir. Yıl ve ay çözümlenebiliyorsa
uç tarihlerin takvim/sıralama kontrolleri de yapılır; bu aralıkların hafta
günü eşleşmesi doğrulanmaz. Gün adlarıyla denetim için iki tam tekil tarih
yazın: `24 Eylül 2026 Perşembe – 25 Eylül 2026 Cuma`.

Ay/yıl geçişleri (`30 Eylül–1 Ekim 2026`, `31 Aralık 2026–1 Ocak 2027`),
kısaltılmış ay adları ve sayısal ortak-ay aralıkları bu aralık desteğinin
kapsamı dışındadır. Böyle ifadelerde mevcut tekil tarih ayrıştırıcısı bazı
tarihleri tanıyabilir; aralığın tamamı veya sırası doğrulanmış sayılmaz.

## Testler

```bash
python -m unittest discover -s tests -v
```

GitHub Actions bu testleri Python 3.11, 3.12 ve 3.13 üzerinde çalıştırır.
