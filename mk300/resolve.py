"""Which catalog model is based on a real-world unit ("Marshall JCM800" -> 21J800_CL_196 ...).

The MK-300 names are abbreviations of the modelled gear (J800 = JCM800, FD = Fender, VXO = Vox,
MES = Mesa, LANY = Laney, BOG = Bogner, EHV5150 = EVH 5150, RADAL = Randall, DUMBLE, ...).
This is a deterministic token match against a small alias table plus the model name; the
score is 0..1 and the caller decides. Nothing here is verified by ear."""
from __future__ import annotations

import re

from . import catalog as cat

ALIASES = {  # real-world token -> tokens that appear in MK-300 names
    "marshall": ["j120", "j800", "j900", "j2000", "jvm", "mar", "jv410", "uk", "196", "57"],
    "jcm800": ["j800"], "jcm900": ["j900"], "jcm2000": ["j2000"], "jvm": ["jvm"], "plexi": ["plx", "196"],
    "fender": ["fd", "fen", "tw", "bman", "deluxe", "fdi"], "twin": ["tw", "fd"], "bassman": ["bman"], "deluxe": ["deluxe", "fendelux"],
    "vox": ["vxo", "vx", "ac30", "ac15", "ac"], "ac30": ["vxo", "ac30"],
    "mesa": ["mes", "mesa", "recto", "mark"], "boogie": ["mes", "mesa"], "rectifier": ["recto", "mes"], "dual": ["mes"],
    "orange": ["or", "og", "ogp", "ogv"], "laney": ["lany"], "bogner": ["bog", "bgn"], "evh": ["ehv5150", "evh"], "5150": ["ehv5150", "pey5150", "va5153"],
    "peavey": ["pey", "peavey", "pey5150"], "randall": ["radal", "ranll", "ranrb"], "dumble": ["dumble"], "soldano": ["sold"], "engl": ["egnl", "eng"],
    "diezel": ["die"], "friedman": ["frman", "fiman"], "hiwatt": ["hiw", "hiwa"], "matchless": ["matter", "mat"], "two rock": ["twor"], "tworock": ["twor"],
    "roland": ["rolans", "j120", "rolnd", "roldb"], "jc120": ["j120"], "jazz chorus": ["j120", "jazz"],
    "ampeg": ["apsvt", "ampg", "apsp"], "svt": ["apsvt", "ampgsvt"], "darkglass": ["dgm900", "dgxu", "dgd", "b7000"], "gallien": ["gkf550", "gkrb", "gkl800"], "gk": ["gkf550", "gkrb", "gkl800"],
    "hartke": ["hkehd50", "hark"], "markbass": ["marklm", "mark500", "mb400", "mbsubway"], "aguilar": ["agdb750", "agula"], "trace elliot": ["tc21vt", "tace"],
    "tube screamer": ["ts8", "ts-9", "ts1", "ts2", "ts3", "808"], "ts808": ["ts8", "808"], "ts9": ["ts-9"], "ibanez": ["ts8", "ts-9", "808"],
    "rat": ["rat"], "proco": ["rat"], "boss": ["ds1", "ds2", "bd", "sd1", "mt"], "ds-1": ["ds1"], "blues driver": ["bd", "blues_dr"], "metal zone": ["mt_1", "mt_2", "mt"],
    "klon": ["gold", "cl_boost", "supa"], "centaur": ["gold"], "big muff": ["big-muff", "muff"], "fuzz face": ["face"], "ocd": ["ocd"], "fulltone": ["ocd"],
    "xotic": ["xep", "xc"], "ep booster": ["xep"], "horizon": ["horizon", "hrz"], "precision drive": ["horizon", "hrz"], "plumes": ["eqp"], "earthquaker": ["eqp"],
    "jhs": ["jhs"], "morning glory": ["jhs"], "bluesbreaker": ["blues_od", "m_blues"], "timmy": ["tds"], "suhr": ["supa"], "riot": ["supa"],
    "celestion": ["v30", "g12", "g75"], "vintage 30": ["v30"], "greenback": ["g12"], "1960": ["1960"], "4x12": ["412"], "2x12": ["212"], "1x12": ["112"], "4x10": ["410"], "1x15": ["115"],
}


def _tokens(s: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]


def resolve(block: str, query: str) -> list[tuple[dict, float]]:
    q = _tokens(query)
    wanted: set[str] = set()
    for t in q:
        wanted.add(t)
        for alias, toks in ALIASES.items():
            if t in _tokens(alias) or alias.replace(" ", "") == t:
                wanted.update(toks)
    scored = []
    for m in cat.models(block):
        name = re.sub(r"^\d+", "", m["name"]).lower()
        ntoks = set(_tokens(name)) | {name.replace("_", "").replace("-", "")}
        hits = 0.0
        for w in wanted:
            if any(w == t or (len(w) >= 3 and w in t) for t in ntoks):
                hits += 1.0
        if hits:
            scored.append((m, min(1.0, hits / max(1, len(q)))))
    scored.sort(key=lambda x: (-x[1], x[0]["index"]))
    return scored
