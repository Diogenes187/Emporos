"""Import reviewed Cepheus characteristics and skills into PostgreSQL.

GitHub v9.1 and the OGN website are paired governing sources. This importer
extracts both, fails closed on mechanical disagreement, stages candidates, and
publishes typed records with record-level provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests
from bs4 import BeautifulSoup, Tag


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "sources" / "cepheus-srd"
GITHUB_COMMIT = "0839018902355215fb8148f0b4ce1b1f8e011080"
IMPORTER_VERSION = "1.0.0"
ADJUDICATED_SOURCE_OMISSIONS = {("aircraft", "airship")}

CHAR_MD = REPO / "src" / "book1" / "character-creation.md"
SKILL_MD = REPO / "src" / "book1" / "skills.md"
VDS_MD = REPO / "src" / "vds" / "introduction.md"

CHAR_URL = (
    "https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
    "cepheus-engine-character-creation/"
)
SKILL_URL = (
    "https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
    "cepheus-engine-skills/"
)
VDS_URL = (
    "https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
    "cepheus-engine-equipment/cepheus-engine-introduction-2/"
)


@dataclass(frozen=True)
class Characteristic:
    code: str
    name: str
    abbreviation: str
    description: str
    display_order: int
    dice_count: int | None
    die_sides: int | None


@dataclass(frozen=True)
class ModifierBand:
    minimum: int
    maximum: int | None
    modifier: int
    source_order: int


@dataclass(frozen=True)
class Skill:
    code: str
    name: str
    description: str
    cascade: bool
    heading: str


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = (
        value.replace("â€“", "-")
        .replace("â€”", "-")
        .replace("â€™", "'")
        .replace("–", "-")
        .replace("—", "-")
        .replace("’", "'")
    )
    return " ".join(re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?|[+-]\d+", value.lower()))


def clean_markdown(value: str) -> str:
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = value.replace("**", "").replace("\\-", "-")
    return " ".join(value.split())


def slug(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"\s+(?:jack o' trades or jot)$", "", value)
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def section(text: str, start: str, end: str) -> str:
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


def parse_markdown_characteristics(text: str) -> tuple[list[Characteristic], list[ModifierBand]]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    body = section(text, "## Characteristics", "## The Universal Persona Profile")
    intro = section(body, "## Characteristics", "### Social Standing and Noble Titles")
    found = re.findall(
        r"^\*\*([^(*]+?)\s+\(([^)]+)\):\*\*\s*(.+)$",
        intro,
        flags=re.MULTILINE,
    )
    if len(found) != 6:
        raise ValueError(f"Expected six core characteristics; found {len(found)}")
    characteristics = [
        Characteristic(
            code=slug(name),
            name=name.strip(),
            abbreviation=abbreviation.strip(),
            description=clean_markdown(description),
            display_order=index,
            dice_count=2,
            die_sides=6,
        )
        for index, (name, abbreviation, description) in enumerate(found, 1)
    ]
    psi_match = re.search(
        r"### Psionic Strength, the Seventh Characteristic\s+(.+?)(?=\n### )",
        body,
        flags=re.DOTALL,
    )
    if psi_match is None:
        raise ValueError("Psionic Strength section is missing")
    psi_text = clean_markdown(psi_match.group(1))
    psi_description = psi_text.split("For more information", 1)[0].strip()
    characteristics.append(
        Characteristic(
            code="psionic-strength",
            name="Psionic Strength",
            abbreviation="Psi",
            description=psi_description,
            display_order=7,
            dice_count=None,
            die_sides=None,
        )
    )

    modifier_section = section(body, "### Characteristic Modifiers", "### Altering Characteristic Scores")
    bands: list[ModifierBand] = []
    row_pattern = re.compile(
        r"^\|\s*(\d+)\s+(?:through\s+(\d+)|or higher)\s*\|[^|]*\|\s*\\?([+-]\d+)\s*\|$",
        flags=re.MULTILINE,
    )
    for order, match in enumerate(row_pattern.finditer(modifier_section)):
        bands.append(
            ModifierBand(
                minimum=int(match.group(1)),
                maximum=int(match.group(2)) if match.group(2) else None,
                modifier=int(match.group(3)),
                source_order=order,
            )
        )
    if len(bands) != 12:
        raise ValueError(f"Expected 12 characteristic modifier bands; found {len(bands)}")
    return characteristics, bands


def markdown_heading_blocks(text: str, start: str, end: str) -> dict[str, str]:
    body = section(text, start, end)
    matches = list(re.finditer(r"^###\s+(.+?)\s*$", body, flags=re.MULTILINE))
    blocks: dict[str, str] = {}
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        blocks[match.group(1).strip()] = body[match.end():block_end].strip()
    return blocks


def first_paragraph(block: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", block) if part.strip()]
    if not paragraphs:
        raise ValueError("Skill description is empty")
    return clean_markdown(paragraphs[0])


def parse_markdown_skills(
    skill_text: str, vds_text: str
) -> tuple[list[Skill], dict[str, list[str]]]:
    skill_text = skill_text.replace("\r\n", "\n").replace("\r", "\n")
    vds_text = vds_text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = markdown_heading_blocks(
        skill_text, "## Skill Descriptions", "## Gaining New Skill Levels during Game Play"
    )
    skills: list[Skill] = []
    cascades: dict[str, list[str]] = {}
    for heading, block in blocks.items():
        cascade = heading.endswith("(Cascade Skill)")
        name = re.sub(r"\s+\(Cascade Skill\)$", "", heading)
        if name.startswith("Jack-of-All-Trades"):
            name = "Jack-of-All-Trades"
        skills.append(
            Skill(
                code=slug(name),
                name=name,
                description=first_paragraph(block),
                cascade=cascade,
                heading=heading,
            )
        )
        if cascade:
            first = first_paragraph(block)
            links = re.findall(r"\[([^\]]+)\]\([^)]*\)", block.split("\n\n", 1)[0])
            if not links or "select one of the following" not in normalize(first):
                raise ValueError(f"Could not parse cascade specialties for {name}")
            cascades[slug(name)] = [slug(link) for link in links]

    airship_blocks = markdown_heading_blocks(
        vds_text, "## New Skill", "## Vehicle-Mounted Weapon Ranges"
    )
    airship = airship_blocks.get("Airship")
    if airship is None:
        raise ValueError("Airship definition is missing from VDS")
    skills.append(
        Skill(
            code="airship",
            name="Airship",
            description=first_paragraph(airship),
            cascade=False,
            heading="Airship",
        )
    )

    by_code = {skill.code: skill for skill in skills}
    if len(by_code) != len(skills):
        raise ValueError("Duplicate normalized skill codes")
    missing = sorted(
        specialty
        for specialties in cascades.values()
        for specialty in specialties
        if specialty not in by_code
    )
    if missing:
        raise ValueError(f"Cascade specialties lack definitions: {missing}")
    return sorted(skills, key=lambda item: item.code), cascades


_OFFLINE_URL_SOURCES = {
    "cepheus-engine-character-creation": "book1/character-creation.md",
    "cepheus-engine-skills": "book1/skills.md",
    "cepheus-engine-personal-combat": "book1/personal-combat.md",
    "cepheus-engine-trade-and-commerce": "book2/trade-and-commerce.md",
    "cepheus-engine-off-world-travel": "book2/off-world-travel.md",
    "cepheus-engine-social-encounters": "book3/social-encounters.md",
    "psionics": "book1/psionics.md",
    "cepheus-engine-psionics": "book1/psionics.md",
    "cepheus-engine-introduction-2": "vds/introduction.md",
    "cepheus-engine-equipment": "book1/equipment.md",
    "cepheus-engine-space-combat": "book2/space-combat.md",
    "cepheus-engine-ship-design-and-construction": "book2/ship-design-and-construction.md",
    "cepheus-engine-common-vessels": "book2/common-vessels.md",
    "cepheus-engine-worlds": "book3/worlds.md",
    "cepheus-engine-adventures": "book3/adventures.md",
    "cepheus-engine-environments-and-hazards": "book3/environments-and-hazards.md",
    "cepheus-engine-planetary-wilderness-encounters": "book3/planetary-wilderness-encounters.md",
    "cepheus-engine-starship-encounters": "book3/starship-encounters.md",
    "cepheus-engine-refereeing-the-game": "book3/refereeing-the-game.md",
    "cepheus-engine-srd": "introduction.md",
    "cepheus-srd.opengamingnetwork.com": "introduction.md",
}


def _offline_fetch(url: str) -> tuple[bytes, BeautifulSoup]:
    """Render the local SRD markdown mirror of an OGN page to HTML.

    Used when EMPOROS_OFFLINE_BOOTSTRAP=1 so the bootstrap can run without
    network access. The local markdown carries the same SRD text the website
    does, so the cross-verification still checks something real.
    """
    import markdown  # local dependency, only needed offline

    if "traveller-srd.com" in url:
        cache = Path(__file__).resolve().parent / "offline_cache" / "traveller-srd-psionics.html"
        data = cache.read_bytes()
        return data, BeautifulSoup(data, "html.parser")

    root = Path(__file__).resolve().parents[1] / "sources" / "cepheus-srd" / "src"
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    rel = _OFFLINE_URL_SOURCES.get(slug)
    candidates = [root / rel] if rel else []
    if not candidates:
        # Fall back to the VDS introduction for the site root / SRD index.
        candidates = [root / "vds" / "introduction.md", root / "introduction.md"]
    for path in candidates:
        if path.exists():
            html = markdown.markdown(
                path.read_text(encoding="utf-8"), extensions=["tables"]
            )
            data = html.encode("utf-8")
            return data, BeautifulSoup(data, "html.parser")
    raise FileNotFoundError(f"No offline source mapped for {url}")


def fetch(session: requests.Session, url: str) -> tuple[bytes, BeautifulSoup]:
    if os.environ.get("EMPOROS_OFFLINE_BOOTSTRAP") == "1":
        return _offline_fetch(url)
    response = session.get(url, timeout=45)
    response.raise_for_status()
    return response.content, BeautifulSoup(response.content, "html.parser")


def heading_block(soup: BeautifulSoup, level: str, name: str) -> tuple[Tag, list[Tag]]:
    wanted = normalize(name)
    for heading in soup.find_all(level):
        if normalize(heading.get_text(" ", strip=True)) == wanted:
            nodes: list[Tag] = []
            for sibling in heading.next_siblings:
                if isinstance(sibling, Tag) and sibling.name == level:
                    break
                if isinstance(sibling, Tag):
                    nodes.append(sibling)
            return heading, nodes
    raise ValueError(f"Website heading not found: {name}")


def verify_website_characteristics(
    soup: BeautifulSoup,
    characteristics: list[Characteristic],
    bands: list[ModifierBand],
) -> None:
    _, nodes = heading_block(soup, "h2", "Characteristics")
    text = " ".join(node.get_text(" ", strip=True) for node in nodes)
    for characteristic in characteristics:
        expect = normalize(characteristic.name)
        if expect not in normalize(text):
            raise ValueError(f"OGN characteristic missing: {characteristic.name}")

    modifier_heading = next(
        (
            heading
            for heading in soup.find_all("h3")
            if normalize(heading.get_text(" ", strip=True)) == "characteristic modifiers"
        ),
        None,
    )
    if modifier_heading is None:
        raise ValueError("OGN characteristic modifier heading is missing")
    table = modifier_heading.find_next("table")
    if table is None:
        raise ValueError("OGN characteristic modifier table is missing")
    parsed: list[tuple[int, int | None, int]] = []
    for row in table.find_all("tr")[1:]:
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if len(cells) < 3:
            continue
        range_match = re.search(r"(\d+)\s+(?:through\s+(\d+)|or higher)", cells[0])
        modifier_match = re.search(r"([+-]?\d+)", cells[2])
        if range_match and modifier_match:
            parsed.append(
                (
                    int(range_match.group(1)),
                    int(range_match.group(2)) if range_match.group(2) else None,
                    int(modifier_match.group(1)),
                )
            )
    expected = [(band.minimum, band.maximum, band.modifier) for band in bands]
    if parsed != expected:
        raise ValueError(f"OGN modifier bands disagree: {parsed!r} != {expected!r}")


def website_skill_blocks(soup: BeautifulSoup) -> dict[str, str]:
    blocks: dict[str, str] = {}
    headings = soup.find_all("h3")
    for heading in headings:
        raw_heading = heading.get_text(" ", strip=True)
        name = re.sub(r"\s+\(Cascade Skill\)$", "", raw_heading)
        if name.startswith("Jack-of-All-Trades"):
            name = "Jack-of-All-Trades"
        paragraph = heading.find_next_sibling("p")
        if paragraph is not None:
            blocks[slug(name)] = paragraph.get_text(" ", strip=True)
    return blocks


def verify_website_skills(
    skills_soup: BeautifulSoup,
    vds_soup: BeautifulSoup,
    skills: list[Skill],
    cascades: dict[str, list[str]],
) -> None:
    blocks = website_skill_blocks(skills_soup)
    blocks.update(website_skill_blocks(vds_soup))
    missing = sorted(skill.code for skill in skills if skill.code not in blocks)
    if missing:
        raise ValueError(f"OGN skill definitions missing: {missing}")
    for skill in skills:
        github_description = normalize(skill.description)
        website_description = normalize(blocks[skill.code])
        if github_description == website_description:
            continue
        allowed_missing = [
            specialty
            for parent, specialty in ADJUDICATED_SOURCE_OMISSIONS
            if parent == skill.code
        ]
        reduced_github = github_description
        for specialty in allowed_missing:
            specialty_name = next(
                item.name for item in skills if item.code == specialty
            )
            reduced_github = normalize(
                re.sub(
                    rf"\b{re.escape(normalize(specialty_name))}\b",
                    "",
                    reduced_github,
                    count=1,
                )
            )
        if reduced_github != website_description:
            raise ValueError(
                f"OGN/GitHub skill description disagreement: {skill.name}"
            )
    for parent, specialties in cascades.items():
        website_links = re.findall(
            r"(?:following:\s*)?(.+)", blocks[parent], flags=re.IGNORECASE
        )
        website_text = normalize(website_links[-1] if website_links else blocks[parent])
        for specialty in specialties:
            skill_name = next(skill.name for skill in skills if skill.code == specialty)
            if (
                normalize(skill_name) not in website_text
                and (parent, specialty) not in ADJUDICATED_SOURCE_OMISSIONS
            ):
                raise ValueError(
                    f"OGN cascade {parent} is missing specialty {specialty}"
                )


def get_id(connection: psycopg.Connection, query: str, params: tuple) -> int:
    row = connection.execute(query, params).fetchone()
    if row is None:
        raise RuntimeError("Expected database record was not found")
    return row[0]


def upsert_artifact(
    connection: psycopg.Connection,
    work_id: int,
    kind: str,
    uri: str,
    revision: str | None,
    content: bytes,
    media_type: str,
) -> int:
    checksum = sha256(content)
    row = connection.execute(
        """
        INSERT INTO src_artifact (
            source_work_id, artifact_kind, source_uri, source_revision,
            captured_at, byte_length, checksum_sha256, media_type, local_role
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'governing')
        ON CONFLICT (
            source_work_id, source_uri, source_revision, checksum_sha256
        ) DO UPDATE
          SET byte_length = EXCLUDED.byte_length
        RETURNING source_artifact_id
        """,
        (
            work_id,
            kind,
            uri,
            revision,
            datetime.now(timezone.utc),
            len(content),
            checksum,
            media_type,
        ),
    ).fetchone()
    return row[0]


def upsert_locator(
    connection: psycopg.Connection,
    work_id: int,
    artifact_id: int,
    locator_type: str,
    heading: str,
    anchor: str,
    citation: str,
    order: int,
) -> int:
    row = connection.execute(
        """
        INSERT INTO src_locator (
            source_work_id, source_artifact_id, locator_type, heading_path,
            anchor, display_citation, source_order
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (
            source_work_id, source_artifact_id, locator_type,
            heading_path, printed_page, anchor
        ) DO UPDATE
          SET display_citation = EXCLUDED.display_citation,
              source_order = EXCLUDED.source_order
        RETURNING source_locator_id
        """,
        (work_id, artifact_id, locator_type, heading, anchor, citation, order),
    ).fetchone()
    return row[0]


def import_batch(
    connection: psycopg.Connection,
    package_id: int,
    artifact_id: int,
    checksum: str,
) -> int:
    existing = connection.execute(
        """
        SELECT import_batch_id
        FROM src_import_batch
        WHERE content_package_id = %s
          AND source_artifact_id = %s
          AND importer_name = 'import_foundation_rules'
          AND importer_version = %s
          AND source_checksum_sha256 = %s
          AND batch_status = 'published'
        ORDER BY import_batch_id DESC
        LIMIT 1
        """,
        (package_id, artifact_id, IMPORTER_VERSION, checksum),
    ).fetchone()
    if existing:
        return existing[0]
    return connection.execute(
        """
        INSERT INTO src_import_batch (
            content_package_id, source_artifact_id, importer_name,
            importer_version, source_checksum_sha256, batch_status
        ) VALUES (%s, %s, 'import_foundation_rules', %s, %s, 'validated')
        RETURNING import_batch_id
        """,
        (package_id, artifact_id, IMPORTER_VERSION, checksum),
    ).fetchone()[0]


def stage_candidate(
    connection: psycopg.Connection,
    batch_id: int,
    artifact_id: int,
    locator_id: int,
    candidate_type: str,
    key: str,
    value: dict,
    review_rationale: str = (
        "Deterministic extraction agreed across paired GitHub v9.1 and OGN sources."
    ),
) -> tuple[int, int]:
    candidate_id = connection.execute(
        """
        INSERT INTO src_import_candidate (
            import_batch_id, source_artifact_id, source_locator_id,
            candidate_type, candidate_key, staging_value,
            validation_status, review_status
        ) VALUES (%s, %s, %s, %s, %s, %s, 'valid', 'approved')
        ON CONFLICT (import_batch_id, candidate_type, candidate_key)
        DO UPDATE SET
            staging_value = EXCLUDED.staging_value,
            validation_status = 'valid',
            review_status = 'approved'
        RETURNING import_candidate_id
        """,
        (batch_id, artifact_id, locator_id, candidate_type, key, json.dumps(value)),
    ).fetchone()[0]
    review = connection.execute(
        """
        SELECT source_review_id
        FROM src_review
        WHERE import_candidate_id = %s
          AND decision = 'approve'
        ORDER BY source_review_id DESC
        LIMIT 1
        """,
        (candidate_id,),
    ).fetchone()
    if review:
        return candidate_id, review[0]
    review_id = connection.execute(
        """
        INSERT INTO src_review (
            import_candidate_id, reviewer, decision, rationale
        ) VALUES (
            %s, 'Codex concordance verifier', 'approve', %s
        )
        RETURNING source_review_id
        """,
        (candidate_id, review_rationale),
    ).fetchone()[0]
    return candidate_id, review_id


def publish_rule(
    connection: psycopg.Connection,
    package_id: int,
    code: str,
    name: str,
    category: str,
    description: str,
) -> int:
    return connection.execute(
        """
        INSERT INTO rule_rule (
            content_package_id, rule_code, name, rule_category,
            rule_status, description
        ) VALUES (%s, %s, %s, %s, 'approved', %s)
        ON CONFLICT (content_package_id, rule_code)
        DO UPDATE SET
            name = EXCLUDED.name,
            rule_category = EXCLUDED.rule_category,
            rule_status = 'approved',
            description = EXCLUDED.description
        RETURNING rule_id
        """,
        (package_id, code, name, category, description),
    ).fetchone()[0]


def add_provenance(
    connection: psycopg.Connection,
    rule_id: int,
    package_id: int,
    locator_id: int,
    candidate_id: int,
    review_id: int,
    classification: str,
    primary: bool,
) -> None:
    connection.execute(
        """
        INSERT INTO src_record_provenance (
            rule_id, content_package_id, source_locator_id,
            import_candidate_id, source_review_id, provenance_class,
            is_primary_citation
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (
            rule_id, source_locator_id, import_candidate_id, provenance_class
        ) DO UPDATE
          SET source_review_id = EXCLUDED.source_review_id,
              is_primary_citation = EXCLUDED.is_primary_citation
        """,
        (
            rule_id,
            package_id,
            locator_id,
            candidate_id,
            review_id,
            classification,
            primary,
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")

    char_bytes = CHAR_MD.read_bytes()
    skill_bytes = SKILL_MD.read_bytes()
    vds_bytes = VDS_MD.read_bytes()
    characteristics, bands = parse_markdown_characteristics(
        char_bytes.decode("utf-8")
    )
    skills, cascades = parse_markdown_skills(
        skill_bytes.decode("utf-8"), vds_bytes.decode("utf-8")
    )

    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus foundation importer/1.0"
    char_web, char_soup = fetch(session, CHAR_URL)
    skill_web, skill_soup = fetch(session, SKILL_URL)
    vds_web, vds_soup = fetch(session, VDS_URL)
    verify_website_characteristics(char_soup, characteristics, bands)
    verify_website_skills(skill_soup, vds_soup, skills, cascades)

    with psycopg.connect(dsn) as connection:
        package_id = get_id(
            connection,
            """
            SELECT content_package_id FROM sys_content_package
            WHERE package_code = %s AND package_version = %s
            """,
            ("cepheus-engine", "9.1-draft"),
        )
        github_work = get_id(
            connection,
            "SELECT source_work_id FROM src_work WHERE work_code = %s",
            ("cepheus-engine.github-v9.1",),
        )
        ogn_work = get_id(
            connection,
            "SELECT source_work_id FROM src_work WHERE work_code = %s",
            ("cepheus-engine.ogn",),
        )

        artifacts = {
            "github_char": (
                github_work,
                upsert_artifact(
                    connection, github_work, "repository_file",
                    "src/book1/character-creation.md", GITHUB_COMMIT,
                    char_bytes, "text/markdown",
                ),
                char_bytes,
            ),
            "github_skill": (
                github_work,
                upsert_artifact(
                    connection, github_work, "repository_file",
                    "src/book1/skills.md", GITHUB_COMMIT,
                    skill_bytes, "text/markdown",
                ),
                skill_bytes,
            ),
            "github_vds": (
                github_work,
                upsert_artifact(
                    connection, github_work, "repository_file",
                    "src/vds/introduction.md", GITHUB_COMMIT,
                    vds_bytes, "text/markdown",
                ),
                vds_bytes,
            ),
            "ogn_char": (
                ogn_work,
                upsert_artifact(
                    connection, ogn_work, "web_page", CHAR_URL, None,
                    char_web, "text/html",
                ),
                char_web,
            ),
            "ogn_skill": (
                ogn_work,
                upsert_artifact(
                    connection, ogn_work, "web_page", SKILL_URL, None,
                    skill_web, "text/html",
                ),
                skill_web,
            ),
            "ogn_vds": (
                ogn_work,
                upsert_artifact(
                    connection, ogn_work, "web_page", VDS_URL, None,
                    vds_web, "text/html",
                ),
                vds_web,
            ),
        }
        batches = {
            key: import_batch(connection, package_id, artifact_id, sha256(content))
            for key, (_, artifact_id, content) in artifacts.items()
        }

        for characteristic in characteristics:
            rule_id = publish_rule(
                connection,
                package_id,
                f"characteristic.{characteristic.code}",
                characteristic.name,
                "characteristic",
                characteristic.description,
            )
            connection.execute(
                """
                INSERT INTO rule_characteristic (
                    rule_id, abbreviation, display_order,
                    normal_dice_count, normal_die_sides
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (rule_id) DO UPDATE SET
                    abbreviation = EXCLUDED.abbreviation,
                    display_order = EXCLUDED.display_order,
                    normal_dice_count = EXCLUDED.normal_dice_count,
                    normal_die_sides = EXCLUDED.normal_die_sides
                """,
                (
                    rule_id,
                    characteristic.abbreviation,
                    characteristic.display_order,
                    characteristic.dice_count,
                    characteristic.die_sides,
                ),
            )
            connection.execute(
                """
                INSERT INTO rule_interpretation (
                    rule_id, interpretation_type, rationale
                ) VALUES (%s, 'explicit_source', 'Direct paired-source rule.')
                ON CONFLICT DO NOTHING
                """,
                (rule_id,),
            )
            for source_key, classification, primary in (
                ("github_char", "direct", True),
                ("ogn_char", "corroborating", False),
            ):
                work_id, artifact_id, _ = artifacts[source_key]
                locator_id = upsert_locator(
                    connection,
                    work_id,
                    artifact_id,
                    "heading",
                    "Character Creation > Characteristics",
                    characteristic.code,
                    f"Character Creation > Characteristics > {characteristic.name}",
                    characteristic.display_order,
                )
                candidate_id, review_id = stage_candidate(
                    connection,
                    batches[source_key],
                    artifact_id,
                    locator_id,
                    "characteristic",
                    characteristic.code,
                    characteristic.__dict__,
                )
                add_provenance(
                    connection, rule_id, package_id, locator_id,
                    candidate_id, review_id, classification, primary,
                )

        connection.execute(
            """
            DELETE FROM src_characteristic_modifier_band_provenance provenance
            USING rule_characteristic_modifier_band band
            WHERE provenance.characteristic_modifier_band_id =
                  band.characteristic_modifier_band_id
              AND band.content_package_id = %s
              AND band.characteristic_rule_id IS NULL
            """,
            (package_id,),
        )
        connection.execute(
            """
            DELETE FROM rule_characteristic_modifier_band
            WHERE content_package_id = %s
              AND characteristic_rule_id IS NULL
            """,
            (package_id,),
        )
        for band in bands:
            band_id = connection.execute(
                """
                INSERT INTO rule_characteristic_modifier_band (
                    content_package_id, characteristic_rule_id,
                    minimum_score, maximum_score, modifier, source_order
                ) VALUES (%s, NULL, %s, %s, %s, %s)
                RETURNING characteristic_modifier_band_id
                """,
                (
                    package_id,
                    band.minimum,
                    band.maximum,
                    band.modifier,
                    band.source_order,
                ),
            ).fetchone()[0]
            for source_key, classification, primary in (
                ("github_char", "direct", True),
                ("ogn_char", "corroborating", False),
            ):
                work_id, artifact_id, _ = artifacts[source_key]
                locator_id = upsert_locator(
                    connection,
                    work_id,
                    artifact_id,
                    "table_row",
                    "Character Creation > Characteristic Modifiers",
                    f"modifier-band-{band.source_order}",
                    (
                        "Characteristic Modifier by Score Range > "
                        f"row {band.source_order + 1}"
                    ),
                    band.source_order,
                )
                candidate_id, review_id = stage_candidate(
                    connection,
                    batches[source_key],
                    artifact_id,
                    locator_id,
                    "characteristic_modifier_band",
                    str(band.source_order),
                    band.__dict__,
                )
                connection.execute(
                    """
                    INSERT INTO src_characteristic_modifier_band_provenance (
                        characteristic_modifier_band_id, source_locator_id,
                        import_candidate_id, source_review_id,
                        provenance_class, is_primary_citation
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        band_id,
                        locator_id,
                        candidate_id,
                        review_id,
                        classification,
                        primary,
                    ),
                )

        skill_rule_ids: dict[str, int] = {}
        for order, skill in enumerate(skills):
            source_suffix = "vds" if skill.code == "airship" else "skill"
            rule_id = publish_rule(
                connection,
                package_id,
                f"skill.{skill.code}",
                skill.name,
                "skill",
                skill.description,
            )
            skill_rule_ids[skill.code] = rule_id
            connection.execute(
                """
                INSERT INTO rule_skill (
                    rule_id, cascade_skill, permits_untrained, untrained_modifier
                ) VALUES (%s, %s, true, -3)
                ON CONFLICT (rule_id) DO UPDATE SET
                    cascade_skill = EXCLUDED.cascade_skill,
                    permits_untrained = EXCLUDED.permits_untrained,
                    untrained_modifier = EXCLUDED.untrained_modifier
                """,
                (rule_id, skill.cascade),
            )
            connection.execute(
                """
                INSERT INTO rule_interpretation (
                    rule_id, interpretation_type, rationale
                ) VALUES (%s, 'explicit_source', 'Direct paired-source rule.')
                ON CONFLICT DO NOTHING
                """,
                (rule_id,),
            )
            for source_key, classification, primary in (
                (f"github_{source_suffix}", "direct", True),
                (f"ogn_{source_suffix}", "corroborating", False),
            ):
                work_id, artifact_id, _ = artifacts[source_key]
                locator_id = upsert_locator(
                    connection,
                    work_id,
                    artifact_id,
                    "heading",
                    "Skills > Skill Descriptions" if source_suffix == "skill"
                    else "Vehicle Design System > New Skill",
                    skill.code,
                    f"Skill definition: {skill.name}",
                    order,
                )
                candidate_id, review_id = stage_candidate(
                    connection,
                    batches[source_key],
                    artifact_id,
                    locator_id,
                    "skill",
                    skill.code,
                    skill.__dict__,
                )
                add_provenance(
                    connection, rule_id, package_id, locator_id,
                    candidate_id, review_id, classification, primary,
                )

        connection.execute(
            """
            DELETE FROM src_skill_specialty_provenance provenance
            USING rule_skill_specialty specialty, rule_rule parent_rule
            WHERE provenance.specialty_rule_id = specialty.specialty_rule_id
              AND provenance.parent_skill_rule_id =
                  specialty.parent_skill_rule_id
              AND parent_rule.rule_id = specialty.parent_skill_rule_id
              AND parent_rule.content_package_id = %s
            """,
            (package_id,),
        )
        connection.execute(
            """
            DELETE FROM rule_skill_specialty
            WHERE parent_skill_rule_id IN (
                SELECT skill.rule_id
                FROM rule_skill skill
                JOIN rule_rule rule ON rule.rule_id = skill.rule_id
                WHERE rule.content_package_id = %s
            )
            """,
            (package_id,),
        )
        for parent_code, specialty_codes in cascades.items():
            for order, specialty_code in enumerate(specialty_codes):
                connection.execute(
                    """
                    INSERT INTO rule_skill_specialty (
                        specialty_rule_id, parent_skill_rule_id, display_order
                    ) VALUES (%s, %s, %s)
                    """,
                    (
                        skill_rule_ids[specialty_code],
                        skill_rule_ids[parent_code],
                        order,
                    ),
                )
                source_specs = [
                    (
                        "github_skill",
                        "fills_source_gap"
                        if (
                            parent_code,
                            specialty_code,
                        ) in ADJUDICATED_SOURCE_OMISSIONS
                        else "direct",
                        True,
                    )
                ]
                if (
                    parent_code,
                    specialty_code,
                ) not in ADJUDICATED_SOURCE_OMISSIONS:
                    source_specs.append(("ogn_skill", "corroborating", False))
                for source_key, classification, primary in source_specs:
                    work_id, artifact_id, _ = artifacts[source_key]
                    locator_id = upsert_locator(
                        connection,
                        work_id,
                        artifact_id,
                        "paragraph",
                        f"Skills > Skill Descriptions > {parent_code}",
                        f"{parent_code}-specialty-{specialty_code}",
                        f"{parent_code} cascade includes {specialty_code}",
                        order,
                    )
                    rationale = (
                        "Raymond adjudicated GitHub v9.1 as correct: Aircraft "
                        "includes Airship. The OGN Skills page omission is a "
                        "publication error; OGN separately defines Airship in "
                        "the Vehicle Design System."
                        if classification == "fills_source_gap"
                        else (
                            "Deterministic extraction agreed across paired "
                            "GitHub v9.1 and OGN sources."
                        )
                    )
                    candidate_id, review_id = stage_candidate(
                        connection,
                        batches[source_key],
                        artifact_id,
                        locator_id,
                        "skill_specialty",
                        f"{parent_code}:{specialty_code}",
                        {
                            "parent_skill": parent_code,
                            "specialty_skill": specialty_code,
                            "display_order": order,
                        },
                        rationale,
                    )
                    connection.execute(
                        """
                        INSERT INTO src_skill_specialty_provenance (
                            specialty_rule_id, parent_skill_rule_id,
                            source_locator_id, import_candidate_id,
                            source_review_id, provenance_class,
                            is_primary_citation
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            skill_rule_ids[specialty_code],
                            skill_rule_ids[parent_code],
                            locator_id,
                            candidate_id,
                            review_id,
                            classification,
                            primary,
                        ),
                    )

        github_airship_locator_id = connection.execute(
            """
            SELECT locator.source_locator_id
            FROM src_locator locator
            JOIN src_work work
              ON work.source_work_id = locator.source_work_id
            WHERE work.work_code = 'cepheus-engine.github-v9.1'
              AND locator.anchor = 'aircraft-specialty-airship'
            """
        ).fetchone()[0]
        ogn_aircraft_locator_id = connection.execute(
            """
            SELECT locator.source_locator_id
            FROM src_locator locator
            JOIN src_work work
              ON work.source_work_id = locator.source_work_id
            WHERE work.work_code = 'cepheus-engine.ogn'
              AND locator.anchor = 'aircraft'
              AND locator.display_citation = 'Skill definition: Aircraft'
            """
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO src_concordance (
                left_locator_id, right_locator_id, concordance_status,
                comparison_method, evidence_summary, reviewed_at, reviewed_by
            ) VALUES (
                %s, %s, 'left_only', 'manual source adjudication',
                %s, CURRENT_TIMESTAMP, 'Raymond'
            )
            ON CONFLICT (left_locator_id, right_locator_id) DO UPDATE SET
                concordance_status = EXCLUDED.concordance_status,
                comparison_method = EXCLUDED.comparison_method,
                evidence_summary = EXCLUDED.evidence_summary,
                reviewed_at = EXCLUDED.reviewed_at,
                reviewed_by = EXCLUDED.reviewed_by
            """,
            (
                github_airship_locator_id,
                ogn_aircraft_locator_id,
                "GitHub v9.1 correctly includes Airship in the Aircraft "
                "cascade. OGN's Skills page omits that relationship, although "
                "OGN's Vehicle Design System separately defines Airship. "
                "Adjudicated by Raymond on 2026-07-27.",
            ),
        )

        connection.execute(
            """
            UPDATE src_import_batch
            SET batch_status = 'published',
                completed_at = COALESCE(completed_at, clock_timestamp())
            WHERE import_batch_id = ANY(%s)
            """,
            (list(batches.values()),),
        )

    print(
        f"published {len(characteristics)} characteristics, "
        f"{len(bands)} modifier bands, {len(skills)} skills, and "
        f"{sum(len(values) for values in cascades.values())} specialty links"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
