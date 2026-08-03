"""Import paired Psionic Strength and training rules for CE-PSI-001."""
import argparse,os
import psycopg,requests
from import_foundation_rules import ROOT,fetch,normalize
URL=("https://cepheus-srd.opengamingnetwork.com/cepheus-engine-srd/"
     "cepheus-engine-psionics/")
SOURCE=ROOT/"sources/cepheus-srd/src/book1/psionics.md"
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--dsn");a=p.parse_args()
 dsn=a.dsn or os.environ.get("BASE_CEPHEUS_DATABASE_URL")
 if not dsn:p.error("--dsn or BASE_CEPHEUS_DATABASE_URL is required")
 s=requests.Session();s.headers["User-Agent"]="BaseCepheus psionic training/1.0"
 _,soup=fetch(s,URL);paired=(normalize(SOURCE.read_text()),normalize(soup.get_text(" ")))
 for phrase in ("roll 2d6 and subtract the number of terms served",
  "training requires four months of work","costs cr100,000",
  "may attempt the talents in any order","1 dm per check attempted",
  "gains that talent at level 0","awareness | +1","telepathy | +4"):
  if any(normalize(phrase) not in text for text in paired):
   raise ValueError(f"Paired psionic training sources omit: {phrase}")
 with psycopg.connect(dsn) as c:
  rule=c.execute("SELECT rule_id FROM rule_rule WHERE rule_code='psionics.system'").fetchone()[0]
  c.execute("""INSERT INTO rule_psionic_training
   VALUES (%s,2,6,-1,4,100000,8,-1,0,true)""",(rule,))
 print("published Psionic Strength determination and training");return 0
if __name__=="__main__":raise SystemExit(main())
