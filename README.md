# Market AI

BIST hisseleri icin veri, teknik gostergeler, sinyal testi ve risk hesaplama altyapisi.

> Bu proje egitim ve arastirma amaclidir. Yatirim tavsiyesi veya garanti getiri sistemi degildir.

## v0.1 hedefi

1. BIST hissesinin gunluk OHLCV verisini cekmek
2. SMA20/50/200, RSI14, ATR14, hacim orani ve 20 gunluk momentumu hesaplamak
3. Basit ve acik bir trend/momentum sinyali uretmek
4. Sinyalin sonraki gun acilisindan bir sonraki gun acilisina tarihsel edge'ini olcmek
5. Portfoy riski ve stop mesafesine gore maksimum pozisyon boyutunu hesaplamak

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

## Calistirma

```bash
python -m app.main THYAO --portfolio 100000 --risk-pct 0.5 --period 5y
```

BIST sembollerine `.IS` otomatik eklenir. Ornegin `THYAO` -> `THYAO.IS`.

## v0.1 sinyal mantigi

Sinyal su kosullarin ayni anda saglanmasidir:

- Kapanis > SMA200
- Kapanis > SMA50
- 20 gunluk momentum > 0
- RSI14 50 ile 70 arasinda
- Hacim / 20 gunluk ortalama hacim > 1.10

Bu kurallar nihai strateji degildir; sadece test edilebilir ilk hipotezdir.

## Backtest hakkinda

v0.1 backtest'i sinyalin tahmin gucunu izole etmek icin her sinyali bagimsiz bir 1 gunluk islem olarak olcer: sinyal gununun ardindaki acilistan, onu takip eden acilisa. Komisyon/slippage icin `fee_bps` maliyeti dusulur. Sinyaller ust uste binebilir; bu nedenle bu modul tam portfoy simulasyonu degil, **signal-edge testi**dir.

v0.2'de event-driven, cakismayan pozisyonlar ve gunluk equity curve eklenmesi planlanmistir.

## Proje yapisi

```text
app/
  data/market_data.py
  indicators/technical.py
  strategies/baseline.py
  backtest/signal_edge.py
  risk/position_sizing.py
  main.py
tests/
```

## Veri

Ilk prototip Yahoo Finance verisini `yfinance` ile kullanir. Gercek para ile kullanmadan once kurumsal/guvenilir piyasa veri saglayicisi, veri kalite kontrolleri ve kaynak yedekliligi eklenmelidir.
