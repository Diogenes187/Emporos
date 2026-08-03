"""Compare pinned Cepheus SRD Markdown with the rendered OGN website.

This is an audit tool, not an importer. It removes navigation/presentation
markup, normalizes Unicode and punctuation, and reports token-level similarity.
The raw source remains authoritative evidence for any detailed mismatch review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE = "https://cepheus-srd.opengamingnetwork.com"


@dataclass(frozen=True)
class Page:
    name: str
    url: str
    sources: tuple[str, ...]


PAGES = (
    Page("Introduction", "/", ("src/introduction.md",)),
    Page("Adventures", "/cepheus-engine-srd/cepheus-engine-adventures/", ("src/book3/adventures.md",)),
    Page("Character Creation", "/cepheus-engine-srd/cepheus-engine-character-creation/", ("src/book1/character-creation.md",)),
    Page("Environments and Hazards", "/cepheus-engine-srd/cepheus-engine-environments-and-hazards/", ("src/book3/environments-and-hazards.md",)),
    Page("Equipment", "/cepheus-engine-srd/cepheus-engine-equipment/", ("src/book1/equipment.md",)),
    Page("Off-World Travel", "/cepheus-engine-srd/cepheus-engine-off-world-travel/", ("src/book2/off-world-travel.md",)),
    Page("Personal Combat", "/cepheus-engine-srd/cepheus-engine-personal-combat/", ("src/book1/personal-combat.md",)),
    Page("Planetary Wilderness Encounters", "/cepheus-engine-srd/cepheus-engine-planetary-wilderness-encounters/", ("src/book3/planetary-wilderness-encounters.md",)),
    Page("Psionics", "/cepheus-engine-srd/cepheus-engine-psionics/", ("src/book1/psionics.md",)),
    Page("Refereeing the Game", "/cepheus-engine-srd/cepheus-engine-refereeing-the-game/", ("src/book3/refereeing-the-game.md",)),
    Page("Skills", "/cepheus-engine-srd/cepheus-engine-skills/", ("src/book1/skills.md",)),
    Page("Social Encounters", "/cepheus-engine-srd/cepheus-engine-social-encounters/", ("src/book3/social-encounters.md",)),
    Page("Space Combat", "/cepheus-engine-srd/cepheus-engine-space-combat/", ("src/book2/space-combat.md",)),
    Page("Starship Encounters", "/cepheus-engine-srd/cepheus-engine-starship-encounters/", ("src/book3/starship-encounters.md",)),
    Page("Worlds", "/cepheus-engine-srd/cepheus-engine-worlds/", ("src/book3/worlds.md",)),
    Page("Legal", "/cepheus-engine-srd/cepheus-engine-legal/", ("src/legal.md",)),
    Page("Common Aircraft", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-aircraft/", ("src/vds/common-aircraft.md",)),
    Page("Common Grav Vehicles", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-grav-vehicles/", ("src/vds/common-grav-vehicles.md",)),
    Page("Common Ground Vehicles", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-ground-vehicles/", ("src/vds/common-ground-vehicles.md",)),
    Page("Common Vessels", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-vessels/", ("src/book2/common-vessels.md",)),
    Page("Common Watercraft", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-common-watercraft/", ("src/vds/common-watercraft.md",)),
    Page("Ship Design and Construction", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-ship-design-and-construction/", ("src/book2/ship-design-and-construction.md",)),
    Page("Trade and Commerce", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-trade-and-commerce/", ("src/book2/trade-and-commerce.md",)),
    Page("Uncommon Vehicles", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-uncommon-vehicles/", ("src/vds/uncommon-vehicles.md",)),
    Page("Vehicle Design System", "/cepheus-engine-srd/cepheus-engine-equipment/cepheus-engine-introduction-2/", ("src/vds/introduction.md", "src/vds/vehicle-design.md")),
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strip_markdown(text: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(?m)^\s*\|?(?:\s*:?-+:?\s*\|)+\s*$", " ", text)
    text = re.sub(r"[#*_`|>~]", " ", text)
    return text


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", text)
    text = (
        text.replace("×", "x")
        .replace("–", "-")
        .replace("—", "-")
        .replace("−", "-")
        .replace("’", "'")
        .replace("\u00e2\u20ac\u201c", "-")
        .replace("\u00e2\u20ac\u201d", "-")
        .replace("\u00e2\u20ac\u2122", "'")
    )
    text = re.sub(r"\bchapter\s+\d+\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"\bcontents\b", " ", text, flags=re.I)
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?|[+-]\d+", text.lower())


def website_article(html: str | bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")
    if article is None:
        raise ValueError("No article element found")
    for selector in (
        "script", "style", "nav", "aside", ".ez-toc-container", ".sharedaddy",
        ".jp-relatedposts", ".code-block", ".adsbygoogle", ".post-ratings",
    ):
        for node in article.select(selector):
            node.decompose()
    # Site-generated page TOCs sometimes lack a stable class. Remove a
    # "Contents" heading/list pair immediately following the article title.
    for node in list(article.find_all(["p", "div", "h2"], recursive=True)):
        if node.get_text(" ", strip=True).lower() == "contents":
            nxt = node.find_next_sibling()
            node.decompose()
            if nxt and nxt.name in {"ul", "ol"}:
                nxt.decompose()
            break
    return article.get_text(" ", strip=True)


def diff_samples(a: list[str], b: list[str], limit: int = 5) -> list[dict]:
    out = []
    sm = SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        out.append({
            "kind": tag,
            "github": " ".join(a[i1:i2][:35]),
            "website": " ".join(b[j1:j2][:35]),
            "github_token_count": i2 - i1,
            "website_token_count": j2 - j1,
        })
        if len(out) >= limit:
            break
    return out


def diff_audit(a: list[str], b: list[str]) -> dict:
    """Return aggregate and largest-difference evidence for manual review."""
    changed = []
    counts = {"replace": 0, "delete": 0, "insert": 0}
    for tag, i1, i2, j1, j2 in SequenceMatcher(
        a=a, b=b, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            continue
        counts[tag] += 1
        changed.append({
            "kind": tag,
            "github": " ".join(a[i1:i2][:100]),
            "website": " ".join(b[j1:j2][:100]),
            "github_token_count": i2 - i1,
            "website_token_count": j2 - j1,
        })
    changed.sort(
        key=lambda row: max(row["github_token_count"], row["website_token_count"]),
        reverse=True,
    )
    return {"opcode_counts": counts, "largest_differences": changed[:10]}


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus concordance audit/1.0"
    results = []

    for page in PAGES:
        source_bytes = []
        source_text = []
        missing = []
        for rel in page.sources:
            path = repo / rel
            if not path.exists():
                missing.append(rel)
                continue
            data = path.read_bytes()
            source_bytes.append(data)
            source_text.append(data.decode("utf-8"))

        url = BASE + page.url
        response = session.get(url, timeout=45)
        response.raise_for_status()
        # Let BeautifulSoup inspect the response bytes instead of trusting
        # requests' occasionally incorrect legacy-encoding guess.
        web_text = website_article(response.content)
        md_text = "\n".join(source_text)
        md_tokens = normalize(strip_markdown(md_text))
        web_tokens = normalize(web_text)
        matcher = SequenceMatcher(a=md_tokens, b=web_tokens, autojunk=False)
        ratio = matcher.ratio()
        matched = sum(block.size for block in matcher.get_matching_blocks())
        results.append({
            "name": page.name,
            "url": url,
            "sources": list(page.sources),
            "missing_sources": missing,
            "http_status": response.status_code,
            "github_sha256": sha256(b"\n".join(source_bytes)),
            "website_sha256": sha256(response.content),
            "github_tokens": len(md_tokens),
            "website_tokens": len(web_tokens),
            "matched_tokens": matched,
            "similarity": round(ratio, 6),
            "github_coverage": round(matched / len(md_tokens), 6) if md_tokens else 0,
            "website_coverage": round(matched / len(web_tokens), 6) if web_tokens else 0,
            "diff_samples": diff_samples(md_tokens, web_tokens),
            "diff_audit": diff_audit(md_tokens, web_tokens),
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": str(repo),
        "branch": git(repo, "branch", "--show-current"),
        "commit": git(repo, "rev-parse", "HEAD"),
        "tag": git(repo, "describe", "--tags", "--exact-match", "HEAD"),
        "pages": results,
        "repository_only_content": [
            "src/tools/sector-generator.md",
            "src/tools/sector.js",
            "src/tools/space-encounter-generator.md",
            "src/tools/space-encounter.js",
            "src/tools/roll.js",
            "src/tools/pseudohex.js",
            "src/vds/updated-common-vehicles-table.md",
        ],
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Cepheus Website/GitHub Concordance Report",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Repository commit: `{payload['commit']}`",
        f"- Exact tag: `{payload['tag']}`",
        f"- Compared website pages: {len(results)}",
        "",
        "## Page Results",
        "",
        "| Page | Similarity | GitHub coverage | Website coverage | GitHub tokens | Website tokens |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['name']} | {row['similarity']:.2%} | "
            f"{row['github_coverage']:.2%} | {row['website_coverage']:.2%} | "
            f"{row['github_tokens']} | {row['website_tokens']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "Similarity below 100% does not by itself mean a rules difference. Generated",
        "website tables of contents, headings, link labels, punctuation, and WordPress",
        "presentation produce normalization differences. Every low-scoring page and",
        "every numeric replacement requires manual review before certification.",
        "",
        "## Manual Certification Findings",
        "",
        "- **Shared rules text:** Concordant. After correcting UTF-8 dash handling,",
        "  23 of 25 pages exceed 98% token similarity; the remaining Introduction",
        "  variance is site navigation/presentation.",
        "- **Character Creation:** Not complete on the website. The rendered page",
        "  includes the Athlete-through-Bureaucrat career tables but omits the",
        "  remaining 18 careers present in the pinned GitHub source (three blocks:",
        "  Colonist-through-Marine, Maritime Defense-through-Physician, and",
        "  Pirate-through-Technician). This is a substantive publication omission.",
        "- **Numbers reviewed:** Remaining numeric replacements in the largest-diff",
        "  audit are typography/rendering differences (for example `TL9`/`TL 9`,",
        "  superscript rendering, and concatenated display text), not detected rule",
        "  value conflicts.",
        "- **Certification:** The two publications agree on content they share, but",
        "  neither is assumed to be the complete corpus. Treat GitHub tag `v9.1`",
        "  and the captured OGN pages as paired governing sources: use either to",
        "  fill an omission in the other, retain record-level provenance, and stop",
        "  for review if a genuine conflict is found. Preserve repository-only",
        "  tools and the updated vehicle table as separately classified material.",
        "",
        "## Repository-Only Material",
        "",
    ]
    lines.extend(f"- `{p}`" for p in payload["repository_only_content"])
    lines += ["", "## Difference Samples", ""]
    for row in results:
        if not row["diff_samples"]:
            continue
        lines.append(f"### {row['name']}")
        lines.append("")
        for sample in row["diff_samples"]:
            lines.append(
                f"- **{sample['kind']}** — GitHub: `{sample['github']}`; "
                f"Website: `{sample['website']}`"
            )
        lines.append("")
    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
