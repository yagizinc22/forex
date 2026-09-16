from __future__ import annotations

UNIVERSE_NAME = "BIST 100"
EFFECTIVE_FROM = "2026-07-01"
EFFECTIVE_TO = "2026-09-30"

# Q3 2026 BIST 100 universe. Index membership is periodic and must be
# refreshed when the next review becomes effective.
BIST100_Q3_2026: tuple[str, ...] = (
    "ASELS", "TUPRS", "BIMAS", "THYAO", "AKBNK", "DSTKF", "ODINE", "KCHOL",
    "ASTOR", "EREGL", "YKBNK", "ISCTR", "SAHOL", "TCELL", "GARAN", "CCOLA",
    "KTLEV", "MGROS", "SISE", "SASA", "TRALT", "TAVHL", "FROTO", "ENKAI",
    "AEFES", "PGSUS", "IEYHO", "MPARK", "EKGYO", "TOASO", "GUBRF", "KRDMD",
    "TURSG", "RALYH", "ENJSA", "TTKOM", "KUYAS", "PASEU", "MAVI", "EUPWR",
    "PETKM", "TRMET", "VAKBN", "SARKY", "ANSGR", "HALKB", "OYAKC", "BRSAN",
    "AKSEN", "DOHOL", "CIMSA", "TKFEN", "BTCIM", "DOAS", "ENERY", "ALARK",
    "BSOKE", "GLRMK", "ULKER", "AKSA", "ISMEN", "GESAN", "EFOR", "SOKM",
    "HEKTS", "TSKB", "CWENE", "MAGEN", "ARCLK", "GENIL", "KLRHO", "ECILC",
    "PSGYO", "CVKMD", "OTKAR", "TRENJ", "MIATK", "CANTE", "ODAS", "BRYAT",
    "GRSEL", "DAPGM", "BALSU", "SKBNK", "FENER", "ALTNY", "BERA", "GRTHO",
    "IZENR", "PATEK", "GSRAY", "PAHOL", "TUKAS", "ZOREN", "EUREN", "QUAGR",
    "OBAMS", "VESTL", "REEDR", "ESEN",
)


def validate_universe() -> None:
    if len(BIST100_Q3_2026) != 100:
        raise RuntimeError(f"BIST100 universe must contain 100 symbols, got {len(BIST100_Q3_2026)}")
    if len(set(BIST100_Q3_2026)) != 100:
        raise RuntimeError("BIST100 universe contains duplicate symbols")
