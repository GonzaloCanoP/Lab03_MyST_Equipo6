"""Universos candidatos para la selección del grupo (paso 1 de §3.2 del enunciado).

Cada integrante aporta un universo con su justificación económica. La justificación es la defensa frente al
problema de pruebas múltiples: se prueban solo grupos con una razón económica para compartir una tendencia
estocástica común, y se reporta cuántos se probaron. Este módulo solo contiene datos; el embudo de selección
vive en el resto de `cointegration/`.
"""

UNIVERSES = {
    "petroleras": {
        "owner": "JME",
        "tickers": ["XOM", "CVX", "COP", "OXY", "EOG", "DVN", "APA", "BP", "SHEL"],
        "names": {
            "XOM": "Exxon Mobil",
            "CVX": "Chevron",
            "COP": "ConocoPhillips",
            "OXY": "Occidental Petroleum",
            "EOG": "EOG Resources",
            "DVN": "Devon Energy",
            "APA": "APA Corp.",
            "BP": "BP (ADR)",
            "SHEL": "Shell (ADR)",
        },
        "rationale": (
            "Petroleras de EE. UU. y Europa: todas venden el mismo producto (crudo y gas), así que el precio del "
            "petróleo es una tendencia estocástica común. Lo que las separa es temporal (costos de extracción, "
            "deuda, coberturas) y es lo que debería revertir. Las europeas se toman como ADR en dólares para evitar "
            "el ruido cambiario y la diferencia de horarios de cierre."
        ),
        "excluded": {
            "HES": "Hess: adquirida por Chevron (2025); sesgo de supervivencia / huecos en los datos",
            "MRO": "Marathon Oil: adquirida por ConocoPhillips (2024)",
            "PXD": "Pioneer Natural Resources: adquirida por Exxon Mobil (2024)",
        },
    },
    "oro": {
        "owner": "GC",
        "tickers": ["GLD", "GDX", "NEM", "AEM", "KGC", "B", "AU", "FNV"],
        "names": {
            "GLD": "SPDR Gold Shares (ETF de oro físico)",
            "GDX": "VanEck Gold Miners (ETF de mineras)",
            "NEM": "Newmont",
            "AEM": "Agnico Eagle",
            "KGC": "Kinross Gold",
            "B": "Barrick Mining",
            "AU": "AngloGold Ashanti",
            "FNV": "Franco-Nevada (regalías)",
        },
        "rationale": (
            "Mineras de oro más el metal: el ingreso de las mineras es el precio del oro, así que comparten su "
            "tendencia estocástica. El apalancamiento operativo y las coberturas hacen que la relación cambie en "
            "el tiempo, que es lo que rastrea el filtro 1. GLD/GDX es el ejemplo clásico de Chan (2013)."
        ),
        "excluded": {
            "GOLD": "El ticker GOLD hoy es Gold.com, Inc. (historia desde 2014); Barrick cotiza como B",
        },
    },
}


def all_tickers() -> list[str]:
    """Devuelve los tickers de todos los universos, sin repetidos y en el orden en que aparecen."""
    tickers = []
    for universe in UNIVERSES.values():
        tickers += [t for t in universe["tickers"] if t not in tickers]
    return tickers
