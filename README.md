# AI Fon Bot

Bu proje, TEFAS verileriyle calisan otomatik bir portfoy karar motorudur.
Ilk surum, guvenlik icin `paper broker` ile gelir. Canli emir icin ayri `broker adapter`
eklenir.

## Neyi Yapar

- Fon fiyat gecmisini CSV dosyasindan okur
- TEFAS fon analiz sayfalarindan canli veri okuyabilir
- Momentum, volatilite ve dusus riskine gore skor uretir
- `AL`, `TUT`, `AZALT`, `SAT` kararlarini verir
- Portfoyu otomatik yeniden dengeler
- Toplam zarar freni ve nakit tamponu uygular
- 10.000 TL gibi kucuk baslangic sermayesi icin uygun sinirlar kullanir

## Neyi Henuz Yapmaz

- Banka veya araci kurum hesabina dogrudan baglanmaz
- Yatirim danismanligi vermez

## Strateji Ozet

Varsayimlar:

- Baslangic sermayesi: 10.000 TL
- Risk tercihi: yuksek
- Yatirim ufku: en az 1 yil
- Emir frekansi: gunde en fazla 1 yeniden dengeleme

Kurallar:

- En fazla 3 fon tasinir
- Tek fona maksimum agirlik: %40
- Asgari nakit tamponu: %10
- Fon secimi: 90 gun momentum + 30 gun momentum + volatilite cezasi
- Sert dusus filtresi: 20 gun getirisi negatif ve 60 gun maksimum dusus esigi asilirsa disari alinir
- Portfoy maksimum dusus freni: %12

## Kurulum

```bash
cd /Users/merttemizkan/Documents/ai-fon-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Ornek Calistirma

```bash
cd /Users/merttemizkan/Documents/ai-fon-bot
python3 -m fon_ai_bot.cli \
  --prices sample_prices.csv \
  --config config.sample.toml \
  --broker paper \
  --state portfolio_state.json \
  --notify telegram
```

Ilk calistirmada `portfolio_state.json` dosyasi yoksa sistem baslangic nakdi ile yeni portfoy
olusturur. Sonraki calistirmalarda ayni dosyayi gunceller.

## Canli TEFAS Calistirma

```bash
cd /Users/merttemizkan/Documents/ai-fon-bot
python3 -m fon_ai_bot.cli \
  --config config.tefas.toml \
  --broker paper \
  --state portfolio_state_tefas.json \
  --notify telegram
```

Canli TEFAS modunda repodaki gercek fon evreni:

- `AFT`
- `AFA`
- `IPB`
- `FUA`
- `TTA`
- `GUM`
- `PPN`

## Telegram Bildirimi

Telegram gonderimi icin su environment variable'lari tanimla:

```bash
export TELEGRAM_BOT_TOKEN="bot-token-buraya"
export TELEGRAM_CHAT_ID="chat-id-buraya"
```

Sonra komutu `--notify telegram` ile calistir:

```bash
python3 -m fon_ai_bot.cli \
  --config config.tefas.toml \
  --broker paper \
  --state portfolio_state_tefas.json \
  --notify telegram
```

Bot, ayni icerikli raporu ust uste gondermez. Yeni emir olusursa veya portfoy karari degisirse
mesaj gonderir.

## Ucretsiz ve PC Kapaliyken Calistirma

Bu proje icin en pratik ucretsiz cozum `GitHub Actions` kullanmaktir.
Hazir workflow dosyasi: [.github/workflows/daily-report.yml](/Users/merttemizkan/Documents/ai-fon-bot/.github/workflows/daily-report.yml)

Varsayilan calisma saati:

- Her gun `15:00 UTC`
- Turkiye saatiyle `18:00`

### Kurulum

1. Bu klasoru bir GitHub reposuna push et
2. GitHub repo icinde `Settings > Secrets and variables > Actions` bolumune gir
3. Su iki secret'i ekle:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
4. Repo'da `Actions` tabini ac
5. `Daily Fund Report` workflow'unu gor
6. Istersen `Run workflow` ile hemen test et

### Nasil calisir

- GitHub Actions her gun botu calistirir
- Telegram raporunu yollar
- `portfolio_state_tefas.json` dosyasi degistiysa repo'ya otomatik commit eder
- Boylece state kalici olur ve PC'nin acik kalmasi gerekmez

### Onemli not

Varsayilan GitHub Actions akisi `config.tefas.toml` ile canli TEFAS sayfalarini kullanir.
Ornek CSV akisi ise sadece gelistirme ve test icin repoda tutulur.

## CSV Formati

`sample_prices.csv` dosyasinda su kolonlar olmali:

```text
date,fund_code,price
2025-09-01,ALT,10.12
2025-09-01,HIS,21.40
2025-09-01,PPF,1.08
```

## Canliya Gecis

Canli islem icin asagidaki adim gerekir:

1. Araci kurum veya banka belirlenir
2. Resmi API varsa yeni bir broker adapter yazilir
3. API yoksa web otomasyonu dusunulur, ama gercek para icin risklidir
4. Ilk asamada paper trade ile en az 4 hafta izlenir

## Not

Bu sistem teknik olarak "tam otomatik" olacak sekilde tasarlanmistir, fakat gercek para
ve canli emir tarafinda once broker entegrasyonu gerekir.
