#!/usr/bin/env python3
"""Le kit de session terrain — E8h.

Lit les deux listes aveugles d'une commune et produit ce qu'une session E9 demande : une fiche
imprimable par candidat, une grille de saisie par liste, rien d'autre. Il ne lit **jamais** la
correspondance : il ne peut donc pas trahir l'origine d'un candidat. Il ne touche pas à la base.

Une valeur absente s'affiche absente, avec son motif quand la liste en donne un.
"""

import argparse
import csv
import html
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

GRID_COLUMNS = ["reference", "cadastral_id", "verdict", "motif", "connu", "notes"]
VERDICTS = ("pertinent", "non pertinent", "indécidable")


@dataclass(frozen=True)
class Field:
    label: str
    key: str
    render: Callable[[str], str] = lambda value: value


def number(digits: int = 0) -> Callable[[str], str]:
    def render(value: str) -> str:
        return f"{float(value):,.{digits}f}".replace(",", " ")

    return render


def percent(value: str) -> str:
    return f"{100 * float(value):.1f} %".replace(".", ",")


def ratio_percent(value: str) -> str:
    return f"{100 * float(value):.0f} %"


@dataclass(frozen=True)
class ListSpec:
    slug: str
    source: str
    title: str
    question: str
    says: str
    does_not_say: str
    fields: tuple[Field, ...]
    address_key: str | None = None


LISTS: tuple[ListSpec, ...] = (
    ListSpec(
        slug="parcelles-divisibles",
        source="exploratory-candidates",
        title="Parcelles où l'on pourrait construire",
        question="Où pourrait-on construire ?",
        says=(
            "La forme du terrain libre permet d'y inscrire un lot, d'après la géométrie cadastrale "
            "et le zonage du PLU. Chaque chiffre est mesuré sur la parcelle."
        ),
        does_not_say=(
            "Que le propriétaire vend, que la division est autorisée, ni que le terrain est "
            "accessible. Aucune adresse n'est rattachée : la relation adresse ↔ parcelle n'est "
            "vérifiable par aucune règle."
        ),
        fields=(
            Field("Année du bâti", "built_year"),
            Field("Surface de la parcelle", "parcel_area_m2", lambda v: number()(v) + " m²"),
            Field("Emprise bâtie", "footprint_ratio", ratio_percent),
            Field("Surface libre", "unbuilt_area_m2", lambda v: number()(v) + " m²"),
            Field("Largeur libre", "width_m", lambda v: number(1)(v) + " m"),
            Field(
                "Recul du bâti à la limite", "boundary_distance_m", lambda v: number(1)(v) + " m"
            ),
            Field("Bâtiments", "building_count"),
            Field("Zone PLU", "zone"),
            Field("Dernière mutation", "last_mutation"),
            Field("Étiquette DPE", "dpe_label"),
            Field("Note DPE", "dpe_note"),
            Field("Risques à la parcelle", "risks"),
        ),
    ),
    ListSpec(
        slug="biens-en-vente",
        source="biens-en-vente",
        title="Biens probablement en vente",
        question="Qui est sur le marché ?",
        says=(
            "Un DPE a été déposé à la date indiquée. C'est un fait administratif, obligatoire pour "
            "mettre un logement en vente. Les taux sont observés sur le département."
        ),
        does_not_say=(
            "Que le bien sera vendu — deux tiers des DPE frais ne mutent pas dans l'année — ni "
            "s'il s'agit d'une vente ou d'une location. L'adresse est celle déclarée sur le "
            "diagnostic."
        ),
        fields=(
            Field("DPE déposé le", "dpe_deposited_at"),
            Field("Âge du DPE", "dpe_age_months", lambda v: f"{v} mois"),
            Field("Chance de vente sous 6 mois, selon l'âge", "residual_probability", percent),
            Field("Étiquette", "energy_label"),
            Field("Taux de vente à 12 mois de cette étiquette", "label_rate", percent),
            Field("Surface habitable", "living_area_m2", lambda v: number(1)(v) + " m²"),
            Field("Année de construction", "built_year"),
            Field("Surface de la parcelle", "parcel_area_m2", lambda v: number()(v) + " m²"),
            Field("Zone PLU", "zone"),
            Field("Dernière mutation", "last_mutation"),
        ),
        address_key="dpe_address",
    ),
)


def read_blind(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def value(row: dict[str, str], field: Field) -> str:
    raw = (row.get(field.key) or "").strip()
    if not raw:
        return "absent"
    try:
        return field.render(raw)
    except ValueError:
        return raw


def location(row: dict[str, str], spec: ListSpec) -> list[str]:
    """Adresse déclarée quand la liste en porte une ; position et lien de carte ; ou absents."""
    lines: list[str] = []
    if spec.address_key:
        address = (row.get(spec.address_key) or "").strip()
        lines.append(
            f"<b>Adresse déclarée sur le DPE :</b> {html.escape(address)}"
            if address
            else "<b>Adresse :</b> absente — non déclarée sur le diagnostic"
        )
    latitude, longitude = (row.get("latitude") or "").strip(), (row.get("longitude") or "").strip()
    if latitude and longitude:
        lines.append(f"<b>Position :</b> {float(latitude):.5f}, {float(longitude):.5f}")
        url = (row.get("map_url") or "").strip()
        if url:
            lines.append(
                f'<b>Carte :</b> <a href="{html.escape(url)}">parcellaire sur orthophoto</a>'
            )
    else:
        reason = (row.get("position_missing") or "").strip() or "non calculée"
        lines.append(f"<b>Position :</b> absente — {html.escape(reason)}")
    return lines


def card(row: dict[str, str], spec: ListSpec) -> str:
    facts = "".join(
        f"<tr><th>{html.escape(field.label)}</th><td>{html.escape(value(row, field))}</td></tr>"
        for field in spec.fields
    )
    verdicts = "".join(f"<label><span class='box'></span> {v}</label>" for v in VERDICTS)
    return f"""<section class="card">
  <header><span class="ref">{html.escape(row["reference"])}</span>
  <code>{html.escape(row.get("cadastral_id", ""))}</code></header>
  <p class="where">{"<br>".join(location(row, spec))}</p>
  <table>{facts}</table>
  <div class="verdict">
    <p>{verdicts}</p>
    <p>Motif : <span class="line"></span></p>
    <p>Ce bien vous était : <label><span class='box'></span> connu</label>
       <label><span class='box'></span> inconnu</label></p>
  </div>
</section>"""


STYLE = """
body{font-family:Georgia,serif;margin:2rem auto;max-width:52rem;padding:0 1rem;
     color:#111;background:#fff}
h1{font-size:1.6rem;margin:0}.lead{color:#444}
.card{border:1px solid #999;border-radius:6px;padding:1rem 1.2rem;margin:1.2rem 0;
      page-break-inside:avoid}
.card header{display:flex;justify-content:space-between;align-items:baseline}
.ref{font-size:1.4rem;font-weight:bold}.where{margin:.6rem 0}
table{border-collapse:collapse;width:100%;font-size:.95rem}
th{text-align:left;font-weight:normal;color:#555;padding:.15rem .6rem .15rem 0;width:55%}
td{padding:.15rem 0}
.verdict{border-top:1px dashed #999;margin-top:.8rem;padding-top:.6rem}
.verdict label{margin-right:1.2rem}
.box{display:inline-block;width:.9rem;height:.9rem;border:1px solid #333;vertical-align:middle}
.line{display:inline-block;width:70%;border-bottom:1px solid #333;height:1rem}
@media print{body{margin:0;max-width:none}.card{margin:.8rem 0}}
"""


def sheet(rows: list[dict[str, str]], spec: ListSpec, commune: str, today: str) -> str:
    cards = "\n".join(card(row, spec) for row in rows)
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{html.escape(spec.title)} — {commune}</title>
<style>{STYLE}</style></head><body>
<h1>{html.escape(spec.title)} — commune {commune}</h1>
<p class="lead"><b>{html.escape(spec.question)}</b> · {len(rows)} candidats · généré le {today}</p>
<p><b>Ce que la liste dit :</b> {html.escape(spec.says)}</p>
<p><b>Ce qu'elle ne dit pas :</b> {html.escape(spec.does_not_say)}</p>
<p>Pour chaque candidat : pertinent, non pertinent ou indécidable, <b>avec le motif</b>.
Les objections sont la donnée : rien n'est corrigé ni justifié pendant la session.</p>
{cards}
</body></html>
"""


def grid(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {"reference": row["reference"], "cadastral_id": row.get("cadastral_id", "")} for row in rows
    ]


def build(root: Path, commune: str, today: str) -> list[Path]:
    """Fiches et grilles pour les deux listes ; échoue si une liste manque, sans en fabriquer."""
    output = root / "field-test-35" / commune
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in LISTS:
        source = root / spec.source / commune / "liste-aveugle.csv"
        if not source.exists():
            raise FileNotFoundError(f"liste absente : {source} — la régénérer d'abord")
        rows = read_blind(source)
        page = output / f"fiches-{spec.slug}.html"
        page.write_text(sheet(rows, spec, commune, today), encoding="utf-8")
        table = output / f"grille-{spec.slug}.csv"
        with table.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=GRID_COLUMNS)
            writer.writeheader()
            writer.writerows(grid(rows))
        written += [page, table]
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Kit de session terrain pour une commune")
    parser.add_argument("--commune", required=True, help="Code INSEE, par exemple 35051")
    parser.add_argument("--root", type=Path, default=None, help="Dossier docs/data")
    arguments = parser.parse_args()
    root = arguments.root or (Path(__file__).resolve().parents[2] / "docs" / "data")
    for path in build(root, arguments.commune, date.today().isoformat()):
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
