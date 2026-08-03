"""Import all Cepheus Engine 9.1 career tables from the paired sources."""

import argparse
import os
import re

import psycopg
import requests

from import_foundation_rules import (
    GITHUB_COMMIT, ROOT, add_provenance, fetch, get_id, import_batch,
    normalize, publish_rule, sha256, slug, stage_candidate, upsert_artifact,
    upsert_locator,
)

SOURCE = ROOT / "sources/cepheus-srd/src/book1/character-creation.md"
URL = ("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
       "cepheus-engine-character-creation/")

CHECK_FIELDS = {
    "Qualifications": "qualification",
    "Survival": "survival",
    "Commission": "commission",
    "Advancement": "advancement",
    "Re-enlistment": "reenlistment",
}
TRAINING_HEADERS = {
    "Personal Development": "personal_development",
    "Service Skills": "service",
    "Specialist": "specialist",
    "Adv Education": "advanced_education",
}
CHARACTERISTICS = {
    "str": "characteristic.strength",
    "dex": "characteristic.dexterity",
    "end": "characteristic.endurance",
    "int": "characteristic.intelligence",
    "edu": "characteristic.education",
    "soc": "characteristic.social-standing",
}
SKILL_ALIASES = {
    "jack o trades": "skill.jack-of-all-trades",
    "pilot": "skill.piloting",
}


def cells(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def clean(value):
    return (
        value.replace("\\[", "[").replace("\\]", "]")
        .replace("â€”", "—").strip()
    )


def empty(value):
    return clean(value) in {"", "—", "-"}


def parse_markdown():
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    careers = {}
    index = 0
    order = 0
    while index < len(lines):
        row = cells(lines[index]) if lines[index].startswith("|") else []
        if not (len(row) == 7 and row[0] == "Career"
                and row[1] != "Roll of 4+"):
            index += 1
            continue
        names = row[1:]
        for name in names:
            order += 1
            careers[name] = {
                "order": order, "checks": {}, "ranks": {},
                "training": {}, "material": {}, "cash": {},
            }
        section = None
        index += 2
        while index < len(lines):
            if not lines[index].startswith("|"):
                index += 1
                continue
            row = cells(lines[index])
            if len(row) == 7 and row[0] == "Career":
                break
            label = clean(row[0]) if row else ""
            if label in CHECK_FIELDS:
                for name, value in zip(names, row[1:]):
                    careers[name]["checks"][CHECK_FIELDS[label]] = clean(value)
                index += 1
                continue
            if label == "Ranks and Skills":
                section = "ranks"
            elif label == "Material Benefits":
                section = "material"
            elif label in {"Cash Benefits", "Cost Benefits"}:
                section = "cash"
            elif label in TRAINING_HEADERS:
                section = TRAINING_HEADERS[label]
            elif label.isdigit() and len(row) == 7 and section:
                number = int(label)
                for name, value in zip(names, row[1:]):
                    value = clean(value)
                    if section == "ranks":
                        careers[name]["ranks"][number] = value
                    elif section == "material":
                        careers[name]["material"][number] = value
                    elif section == "cash":
                        careers[name]["cash"][number] = value
                    else:
                        careers[name]["training"].setdefault(
                            section, {})[number] = value
            index += 1
    return careers


def parse_check(raw, allow_characteristic=True):
    if empty(raw):
        return None, None
    match = re.fullmatch(r"([A-Za-z]+)\s+(\d+)\+", clean(raw))
    if match and allow_characteristic:
        return CHARACTERISTICS[match.group(1).lower()], int(match.group(2))
    target = re.fullmatch(r"(\d+)\+", clean(raw))
    if target:
        return None, int(target.group(1))
    raise ValueError(f"Unparsed career check: {raw}")


def parse_rank(raw, skill_codes):
    if empty(raw):
        return None, None, None, None
    match = re.search(r"\[(.+?)\]", raw)
    grant = match.group(1) if match else None
    title = re.sub(r"\s*\[.+?\]\s*", "", raw).strip() or None
    if not grant:
        return title, None, None, None
    skill_text, separator, level_text = grant.rpartition("-")
    level = int(level_text) if separator and level_text.isdigit() else 1
    skill_name = skill_text if separator else grant
    normalized = normalize(skill_name)
    skill = SKILL_ALIASES.get(normalized) or skill_codes.get(normalized)
    return title, skill, level, grant


def parse_training(raw, skill_codes):
    characteristic = re.fullmatch(
        r"\+(\d+)\s+(Str|Dex|End|Int|Edu|Soc)", raw, re.IGNORECASE)
    if characteristic:
        return (
            "characteristic", None,
            CHARACTERISTICS[characteristic.group(2).lower()],
            int(characteristic.group(1)), None,
        )
    fixed = re.fullmatch(r"(.+)-(\d+)", raw)
    skill_name = fixed.group(1) if fixed else raw
    level = int(fixed.group(2)) if fixed else None
    alias = SKILL_ALIASES.get(normalize(skill_name))
    skill = alias or skill_codes.get(normalize(skill_name))
    if skill:
        return "skill", skill, None, None, level
    return "text", None, None, None, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn")
    args = parser.parse_args()
    dsn = args.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
    if not dsn:
        parser.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
    parsed = parse_markdown()
    if len(parsed) != 24:
        raise ValueError(f"Expected 24 careers, parsed {len(parsed)}")
    session = requests.Session()
    session.headers["User-Agent"] = "BaseCepheus career importer/1.0"
    github_raw = SOURCE.read_bytes()
    ogn_raw, soup = fetch(session, URL)
    paired_text = (
        normalize(github_raw.decode()),
        normalize(soup.get_text(" ")),
    )
    for name, career in parsed.items():
        identity = {
            "Surface Defense": "Surface System Defense",
            "Maritime Defense": "Maritime System Defense",
            "Aerospace Defense": "Aerospace System Defense",
        }.get(name, name)
        if any(normalize(identity) not in text for text in paired_text):
            raise ValueError(f"Paired sources omit career identity: {name}")
        if career["order"] <= 6:
            required = (
                normalize(career["checks"]["qualification"]),
                normalize(career["checks"]["reenlistment"]),
            )
            if any(any(token not in text for token in required)
                   for text in paired_text):
                raise ValueError(
                    f"Paired sources disagree on detailed career: {name}")

    with psycopg.connect(dsn) as connection:
        package = get_id(connection, """SELECT content_package_id
            FROM sys_content_package WHERE package_code='cepheus-engine'
              AND package_version='9.1-draft'""", ())
        works = {
            "github": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.github-v9.1'", ()),
            "ogn": get_id(connection, "SELECT source_work_id FROM src_work "
                "WHERE work_code='cepheus-engine.ogn'", ()),
        }
        artifacts = {}
        for side, raw, uri, kind, revision, media in (
            ("github", github_raw, "src/book1/character-creation.md",
             "repository_file", GITHUB_COMMIT, "text/markdown"),
            ("ogn", ogn_raw, URL, "web_page", None, "text/html"),
        ):
            artifact = upsert_artifact(
                connection, works[side], kind, uri, revision, raw, media)
            artifacts[side] = (
                artifact,
                import_batch(connection, package, artifact, sha256(raw)),
            )

        def evidence(
            rule_id, category, code, name, payload, anchor,
            *, relationship=False, ogn_has_detail=True,
        ):
            for side in ("github", "ogn"):
                if relationship and side == "ogn" and not ogn_has_detail:
                    continue
                artifact, batch = artifacts[side]
                locator = upsert_locator(
                    connection, works[side], artifact, "table_row",
                    "Character Creation > Career Tables", anchor, name, 0)
                candidate, review = stage_candidate(
                    connection, batch, artifact, locator,
                    category, code, payload)
                if rule_id is not None:
                    add_provenance(
                        connection, rule_id, package, locator, candidate, review,
                        "direct" if side == "github" else "corroborating",
                        side == "github")
                provenance_class = (
                    "fills_source_gap"
                    if relationship and side == "github"
                    and not ogn_has_detail
                    else "direct" if side == "github" else "corroborating"
                )
                yield side, locator, candidate, review, provenance_class

        skill_codes = {
            normalize(name): code
            for code, name in connection.execute(
                """SELECT rule.rule_code,rule.name
                   FROM rule_skill skill
                   JOIN rule_rule rule ON rule.rule_id=skill.rule_id"""
            )
        }
        skill_ids = {
            code: get_id(
                connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (code,))
            for code in set(skill_codes.values()) | set(SKILL_ALIASES.values())
        }
        characteristic_ids = {
            code: get_id(
                connection,
                "SELECT rule_id FROM rule_rule WHERE rule_code=%s", (code,))
            for code in CHARACTERISTICS.values()
        }
        unresolved = set()

        for name, career in parsed.items():
            code = slug(name)
            rule_id = publish_rule(
                connection, package, f"career.{code}", name, "career", name)
            list(evidence(
                rule_id, "career", f"career.{code}", name,
                {"career": name}, f"career-{code}"))
            ogn_has_detail = career["order"] <= 6
            connection.execute(
                """INSERT INTO rule_career VALUES (%s,%s,%s)
                   ON CONFLICT (career_rule_id) DO UPDATE SET
                     career_code=EXCLUDED.career_code,
                     display_order=EXCLUDED.display_order""",
                (rule_id, code, career["order"]))

            checks = career["checks"]
            qualification = parse_check(checks["qualification"])
            survival = parse_check(checks["survival"])
            commission = parse_check(checks["commission"])
            advancement = parse_check(checks["advancement"])
            _, reenlistment = parse_check(
                checks["reenlistment"], allow_characteristic=False)
            progression_id = connection.execute(
                """INSERT INTO rule_career_progression
                   (career_rule_id,qualification_characteristic_rule_id,
                    qualification_target,survival_characteristic_rule_id,
                    survival_target,commission_characteristic_rule_id,
                    commission_target,advancement_characteristic_rule_id,
                    advancement_target,reenlistment_target)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (career_rule_id,assignment_rule_id)
                   DO UPDATE SET
                     qualification_target=EXCLUDED.qualification_target,
                     survival_target=EXCLUDED.survival_target,
                     commission_target=EXCLUDED.commission_target,
                     advancement_target=EXCLUDED.advancement_target,
                     reenlistment_target=EXCLUDED.reenlistment_target
                   RETURNING career_progression_id""",
                (rule_id,
                 characteristic_ids.get(qualification[0]), qualification[1],
                 characteristic_ids.get(survival[0]), survival[1],
                 characteristic_ids.get(commission[0]), commission[1],
                 characteristic_ids.get(advancement[0]), advancement[1],
                 reenlistment),
            ).fetchone()[0]
            for side, locator, candidate, review, provenance_class in evidence(
                    None, "career_progression", code, name, checks,
                    f"{code}-progression", relationship=True,
                    ogn_has_detail=ogn_has_detail):
                connection.execute(
                    """INSERT INTO src_career_progression_provenance
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    (progression_id, locator, candidate, review,
                     provenance_class,
                     side == "github"))

            for rank_number, raw in career["ranks"].items():
                title, skill_code, level, grant = parse_rank(raw, skill_codes)
                if grant and skill_code is None:
                    unresolved.add(grant)
                rank_id = connection.execute(
                    """INSERT INTO rule_career_rank
                       (career_rule_id,rank_number,title,granted_skill_rule_id,
                        granted_skill_level,source_grant_text)
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (career_rule_id,assignment_rule_id,rank_number)
                       DO UPDATE SET title=EXCLUDED.title,
                         granted_skill_rule_id=EXCLUDED.granted_skill_rule_id,
                         granted_skill_level=EXCLUDED.granted_skill_level,
                         source_grant_text=EXCLUDED.source_grant_text
                       RETURNING career_rank_id""",
                    (rule_id, rank_number, title,
                     skill_ids.get(skill_code), level if skill_code else None,
                     grant),
                ).fetchone()[0]
                for side, locator, candidate, review, provenance_class in evidence(
                        None, "career_rank", f"{code}-{rank_number}", name,
                        {"rank": rank_number, "value": raw},
                        f"{code}-rank-{rank_number}", relationship=True,
                        ogn_has_detail=ogn_has_detail):
                    connection.execute(
                        """INSERT INTO src_career_rank_provenance
                           VALUES (%s,%s,%s,%s,%s,%s)
                           ON CONFLICT DO NOTHING""",
                        (rank_id, locator, candidate, review,
                         provenance_class,
                         side == "github"))

            for table_code, entries in career["training"].items():
                for roll, raw in entries.items():
                    kind, skill_code, characteristic_code, increase, fixed = (
                        parse_training(raw, skill_codes))
                    if kind == "text":
                        unresolved.add(raw)
                    entry_id = connection.execute(
                        """INSERT INTO rule_career_training_entry
                           (career_rule_id,training_table_code,roll_value,
                            outcome_kind,skill_rule_id,characteristic_rule_id,
                            characteristic_increase,fixed_skill_level,
                            source_outcome_text)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (
                             career_rule_id,assignment_rule_id,
                             training_table_code,roll_value
                           ) DO UPDATE SET
                             outcome_kind=EXCLUDED.outcome_kind,
                             skill_rule_id=EXCLUDED.skill_rule_id,
                             characteristic_rule_id=
                               EXCLUDED.characteristic_rule_id,
                             characteristic_increase=
                               EXCLUDED.characteristic_increase,
                             fixed_skill_level=EXCLUDED.fixed_skill_level,
                             source_outcome_text=EXCLUDED.source_outcome_text
                           RETURNING career_training_entry_id""",
                        (rule_id, table_code, roll, kind,
                         skill_ids.get(skill_code),
                         characteristic_ids.get(characteristic_code),
                         increase, fixed, raw),
                    ).fetchone()[0]
                    for side, locator, candidate, review, provenance_class in evidence(
                            None, "career_training", f"{code}-{table_code}-{roll}",
                            name, {"table": table_code, "roll": roll,
                                   "outcome": raw},
                            f"{code}-{table_code}-{roll}", relationship=True,
                            ogn_has_detail=ogn_has_detail):
                        connection.execute(
                            """INSERT INTO src_career_training_entry_provenance
                               VALUES (%s,%s,%s,%s,%s,%s)
                               ON CONFLICT DO NOTHING""",
                            (entry_id, locator, candidate, review,
                             provenance_class, side == "github"))

            for table_code in ("material", "cash"):
                for roll, raw in career[table_code].items():
                    cash = int(raw) if table_code == "cash" else None
                    benefit_id = connection.execute(
                        """INSERT INTO rule_career_benefit
                           (career_rule_id,benefit_table_code,roll_value,
                            cash_credits,source_outcome_text)
                           VALUES (%s,%s,%s,%s,%s)
                           ON CONFLICT (
                             career_rule_id,benefit_table_code,roll_value
                           ) DO UPDATE SET
                             cash_credits=EXCLUDED.cash_credits,
                             source_outcome_text=EXCLUDED.source_outcome_text
                           RETURNING career_benefit_id""",
                        (rule_id, table_code, roll, cash, raw),
                    ).fetchone()[0]
                    for side, locator, candidate, review, provenance_class in evidence(
                            None, "career_benefit", f"{code}-{table_code}-{roll}",
                            name, {"table": table_code, "roll": roll,
                                   "outcome": raw},
                            f"{code}-{table_code}-{roll}", relationship=True,
                            ogn_has_detail=ogn_has_detail):
                        connection.execute(
                            """INSERT INTO src_career_benefit_provenance
                               VALUES (%s,%s,%s,%s,%s,%s)
                               ON CONFLICT DO NOTHING""",
                            (benefit_id, locator, candidate, review,
                             provenance_class, side == "github"))

        system_rule = publish_rule(
            connection, package, "career.system", "Career Lifepath System",
            "career", "Career Lifepath System")
        list(evidence(
            system_rule, "career", "career.system",
            "Career Lifepath System",
            {"starting_age": 18, "term_years": 4, "retirement_terms": 7,
             "previous_career_qualification_modifier": -2,
             "draft_uses_allowed": 1, "drifter_always_open": True,
             "survival_natural_two_fails": True},
            "career-lifepath-system"))
        connection.execute(
            """INSERT INTO rule_career_system
               VALUES (%s,18,4,7,-2,1,true,true)
               ON CONFLICT (rule_id) DO UPDATE SET
                 starting_age_years=EXCLUDED.starting_age_years,
                 term_years=EXCLUDED.term_years,
                 retirement_terms=EXCLUDED.retirement_terms,
                 previous_career_qualification_modifier=
                   EXCLUDED.previous_career_qualification_modifier,
                 draft_uses_allowed=EXCLUDED.draft_uses_allowed,
                 drifter_always_open=EXCLUDED.drifter_always_open,
                 survival_natural_two_fails=
                   EXCLUDED.survival_natural_two_fails""",
            (system_rule,))
        draft = (
            (1, "aerospace-defense"), (2, "marine"),
            (3, "maritime-defense"), (4, "navy"),
            (5, "scout"), (6, "surface-defense"),
        )
        for roll, career_code in draft:
            career_id = get_id(
                connection,
                "SELECT career_rule_id FROM rule_career WHERE career_code=%s",
                (career_code,))
            connection.execute(
                """INSERT INTO rule_career_draft_roll VALUES (%s,%s)
                   ON CONFLICT (roll_value) DO UPDATE SET
                     career_rule_id=EXCLUDED.career_rule_id""",
                (roll, career_id))
            for side, locator, candidate, review, provenance_class in evidence(
                    None, "career_draft", f"draft-{roll}",
                    "Career Draft",
                    {"roll": roll, "career": career_code},
                    f"draft-{roll}", relationship=True,
                    ogn_has_detail=True):
                connection.execute(
                    """INSERT INTO src_career_draft_roll_provenance
                       VALUES (%s,%s,%s,%s,%s,%s)
                       ON CONFLICT DO NOTHING""",
                    (roll, locator, candidate, review,
                     provenance_class, side == "github"))
        connection.commit()
    print(
        "published 24 careers, 24 progression rows, 168 ranks, "
        "576 training entries, and 336 benefits"
    )
    if unresolved:
        print("source outcomes without defined skill rows: "
              + ", ".join(sorted(unresolved)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
