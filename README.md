# Market AI

BIST hisseleri icin veri, teknik gostergeler, sinyal testi, toplu tarama, risk hesaplama, event-driven backtest ve walk-forward optimizasyon altyapisi.

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

## v0.3

- Tek pozisyonlu, long-only event-driven backtest motoru
- Sinyal kapanista okunur; giris sonraki seans acilisinda yapilir
- ATR tabanli stop ve R-multiple tabanli hedef
- Portfoy risk yuzdesine gore pozisyon boyutu
- Nakit limiti; kaldirac yok
- Ayni anda yalnizca tek acik pozisyon; cakisan islemler yok
- Stop/target ayni gun gorulurse konservatif olarak stop once kabul edilir
- Gap stop ve gap target mantigi
- Maksimum elde tutma suresi ve time exit
- Komisyon ve slippage varsayimlari
- Gunluk equity curve
- Total return, CAGR, max drawdown, Sharpe, Sortino
- Win rate, profit factor, expectancy (R), ortalama islem getirisi
- Ortalama elde tutma, maksimum ardisik kayip ve exposure
- Ayrintili trade log

## v0.4

- Girdi filtresi parametreleri artik ayarlanabilir: RSI alt/ust, minimum momentum, minimum hacim orani ve opsiyonel SMA50>SMA200 trend filtresi.
- Trade yonetimi parametreleri grid search ile taranabilir: ATR stop, R hedefi ve maksimum elde tutma.
- Walk-forward yapi kullanir: once train doneminde parametre secilir, sonra ayni parametreler daha once gorulmemis test doneminde degerlendirilir.
- Gosterge hesaplari icin warmup verisi korunur ancak test donemi disindaki sinyaller kapatilir; boylece test baslangicinda eski bir sinyalle islem acilmaz.
- Train skoru minimum islem sayisi, Sharpe/CAGR ve drawdown cezasini birlikte kullanir.
- Her fold icin train ve out-of-sample test getirisi, Sharpe, drawdown ve islem sayisi raporlanir.
- `degradation_pct` train ile test performansi arasindaki farki gosterir; train'de guclu gorunup testte bozulan parametreleri fark etmeye yardim eder.

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

## v0.3 event-driven backtest

Varsayilanlar: 100.000 TL baslangic, islem basina %0.5 risk, 2 ATR stop, 2R hedef, 20 gun max hold, 10 bps komisyon ve 5 bps slippage.

```bash
python -m app.backtest_cli THYAO --period 5y
```

Parametreli ornek:

```bash
python -m app.backtest_cli THYAO --period 10y --initial-cash 100000 --risk-pct 0.5 --stop-atr 2 --target-r 2 --max-hold 20 --fee-bps 10 --slippage-bps 5 --show-trades 20
```

Backtest varsayimlari ozellikle konservatiftir. Gunluk OHLC verisinde stop ve hedefin hangi sirayla tetiklendigi bilinemez; ikisi de ayni bar icinde gorulurse stop once kabul edilir.

## v0.4 walk-forward optimizasyon

Hizli deneme:

```bash
python -m app.optimize_cli THYAO --period 10y --fast-grid
```

Daha genis varsayilan grid:

```bash
python -m app.optimize_cli THYAO --period 10y --train-years 3 --test-years 1 --step-years 1 --min-train-trades 8
```

Ciktiyi yorumlarken **train kolonlarini performans kaniti olarak kullanma**. Parametre secimi train verisinde yapildigi icin asil dikkat edilmesi gereken kolonlar `test_return_pct`, `test_sharpe`, `test_max_drawdown_pct`, `test_trades` ve fold'lar arasindaki tutarliliktir.

## Baseline sinyal mantigi

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

## Iki farkli backtest ne ise yarar?

`app/backtest/signal_edge.py`: her sinyali bagimsiz bir sonraki-acilis -> sonraki-acilis islemi olarak olcer. Bu, sinyalin kisa vadeli tahmin gucunu hizli test etmek icindir; portfoy simulasyonu degildir.

`app/backtest/event_driven.py`: islemleri sirayla gerceklestirir, pozisyonlarin cakismasina izin vermez, sermaye ve risk boyutlandirmasini kullanir ve equity curve olusturur. Strateji performansi icin esas test motoru budur.

`app/optimization/walk_forward.py`: parametreleri train doneminde secer ve daha sonra gorulmemis test doneminde ayni parametrelerle tekrar backtest eder. Optimizasyon icin tercih edilen degerlendirme katmanidir.

## Proje yapisi

```text
app/
  data/market_data.py
  indicators/technical.py
  strategies/baseline.py
  strategies/configurable.py
  backtest/signal_edge.py
  backtest/event_driven.py
  optimization/walk_forward.py
  risk/position_sizing.py
  scanner/score.py
  scanner/bist_scanner.py
  universe/bist100.py
  main.py
  scanner_cli.py
  backtest_cli.py
  optimize_cli.py
tests/
.github/workflows/tests.yml
```

## Otomatik testler

Her `main` push'unda ve pull request'te GitHub Actions uzerinden:

```bash
python -m pytest -q
```

calisir.

## Veri

Ilk prototip Yahoo Finance verisini `yfinance` ile kullanir. Gercek para ile kullanmadan once kurumsal/guvenilir piyasa veri saglayicisi, veri kalite kontrolleri ve kaynak yedekliligi eklenmelidir.

BIST 100 uyelikleri donemseldir. `app/universe/bist100.py` icindeki evren 2026-07-01 ile 2026-09-30 donemi icin etiketlenmistir ve yeni endeks donemi basladiginda guncellenmelidir.
