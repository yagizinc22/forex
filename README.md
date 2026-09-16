# Market AI

BIST hisseleri icin veri, teknik gostergeler, sinyal testi, toplu tarama ve risk hesaplama altyapisi.

> Bu proje egitim ve arastirma amaclidir. Yatirim tavsiyesi veya garanti getiri sistemi degildir.

## v0.1

1. BIST hissesinin gunluk OHLCV verisini cekmek
2. SMA20/50/200, RSI14, ATR14, hacim orani ve 20 gunluk momentumu hesaplamak
3. Basit ve acik bir trend/momentum sinyali uretmek
4. Sinyalin sonraki gun acilisindan bir sonraki gun acilisina tarihsel edge'ini olcmek
5. Portfoy riski ve stop mesafesine gore maksimum pozisyon boyutunu hesaplamak

## v0.2

- 2026 Q3 BIST 100 evrenini toplu tarar.
- Her hisse icin 0-100 arasi `setup_score` hesaplar.
- Son baseline sinyalini gosterir.
- Her sembol icin tarihsel signal-edge win rate, expectancy ve profit factor hesaplar.
- Veri gelmeyen sembolleri hata listesinde raporlar.

`setup_score` gelecek getiri olasiligi degildir. Yalnizca trend, momentum, hacim ve volatilite tercihlerimize ne kadar uyuldugunu gosteren seffaf bir rules-fit puanidir.

## Kurulum

Python 3.11+ onerilir.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Tek hisse analizi

```bash
python -m app.main THYAO --portfolio 100000 --risk-pct 0.5 --period 5y
```

BIST sembollerine `.IS` otomatik eklenir. Ornegin `THYAO` -> `THYAO.IS`.

## BIST 100 scanner

En yuksek puanli 15 setup:

```bash
python -m app.scanner_cli --top 15 --period 5y
```

Yalnizca baseline sinyali aktif olanlar:

```bash
python -m app.scanner_cli --signals-only --top 30
```

## v0.1 sinyal mantigi

Sinyal su kosullarin ayni anda saglanmasidir:

- Kapanis > SMA200
- Kapanis > SMA50
- 20 gunluk momentum > 0
- RSI14 50 ile 70 arasinda
- Hacim / 20 gunluk ortalama hacim > 1.10

Bu kurallar nihai strateji degildir; sadece test edilebilir ilk hipotezdir.

## v0.2 setup score

Toplam 100 puan:

- Close > SMA200: 25
- Close > SMA50: 15
- SMA50 > SMA200: 10
- 20 gun momentum: 0-20
- RSI rejimi: 0-15
- Hacim orani: 0-10
- ATR rejimi: 0-5

Puanlama kodu `app/scanner/score.py` dosyasinda acikca gorulebilir ve test edilebilir.

## Backtest hakkinda

Mevcut backtest sinyalin tahmin gucunu izole etmek icin her sinyali bagimsiz bir 1 gunluk islem olarak olcer: sinyal gununun ardindaki acilistan, onu takip eden acilisa. Komisyon/slippage icin `fee_bps` maliyeti dusulur. Sinyaller ust uste binebilir; bu nedenle bu modul tam portfoy simulasyonu degil, **signal-edge testi**dir.

Sonraki adim: event-driven, cakismayan pozisyonlar, gunluk equity curve, max drawdown ve Sharpe/Sortino.

## Proje yapisi

```text
app/
  data/market_data.py
  indicators/technical.py
  strategies/baseline.py
  backtest/signal_edge.py
  risk/position_sizing.py
  scanner/score.py
  scanner/bist_scanner.py
  universe/bist100.py
  main.py
  scanner_cli.py
tests/
```

## Veri

Ilk prototip Yahoo Finance verisini `yfinance` ile kullanir. Gercek para ile kullanmadan once kurumsal/guvenilir piyasa veri saglayicisi, veri kalite kontrolleri ve kaynak yedekliligi eklenmelidir.

BIST 100 uyelikleri donemseldir. `app/universe/bist100.py` icindeki evren 2026-07-01 ile 2026-09-30 donemi icin etiketlenmistir ve yeni endeks donemi basladiginda guncellenmelidir.
