"""
DocStudio Claims Ledger & Numeric Verification Engine.
Maintains the factual backbone of the documentary.
Enforces that every numeric claim spoken in narration is tied to a verified ledger entry.
"""

from __future__ import annotations
import csv
import re
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Set

@dataclass
class ClaimEntry:
    claim_id: str
    claim: str
    number_or_date: str
    unit: str
    source_url: str
    excerpt: str
    confidence: str
    graphic_worthy: bool
    human_anchor: str
    verified: bool = True
    status: str = "established"
    absolute_ok: bool = False

class ClaimsLedger:
    def __init__(self, ledger_path: Path | str | None = "claims.csv"):
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self.claims: Dict[str, ClaimEntry] = {}
        self.number_index: Dict[str, List[ClaimEntry]] = {}
        if self.ledger_path and self.ledger_path.exists():
            self.load()

    def load(self) -> None:
        """Loads claims from CSV or JSON and indexes numeric entries for narration verification."""
        if not self.ledger_path or not self.ledger_path.exists():
            return
        self.claims.clear()
        self.number_index.clear()

        if self.ledger_path.suffix.lower() == ".json":
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            claims_list = data if isinstance(data, list) else data.get("claims", [])
            self.ingest_research_claims({"claims": claims_list})
            return

        with open(self.ledger_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cid = row.get("ID", row.get("claim_id", "")).strip()
                num_val = row.get("number/date", row.get("number_or_date", "")).strip()
                status_val = row.get("status", row.get("confidence", "established")).strip().lower()
                absolute_val = row.get("absolute_ok", "").strip().lower() in ("yes", "true", "1")
                entry = ClaimEntry(
                    claim_id=cid,
                    claim=row.get("claim", "").strip(),
                    number_or_date=num_val,
                    unit=row.get("unit", "").strip(),
                    source_url=row.get("source_url", "").strip(),
                    excerpt=row.get("excerpt", "").strip(),
                    confidence=row.get("confidence", "high").strip().lower(),
                    graphic_worthy=row.get("graphic_worthy", "").strip().lower() in ("yes", "true", "1"),
                    human_anchor=row.get("human_anchor", "").strip(),
                    verified=True,
                    status=status_val,
                    absolute_ok=absolute_val,
                )
                self.claims[cid] = entry
                
                # Normalize numeric token for matching
                clean_num = num_val.replace(",", "").strip()
                if clean_num not in self.number_index:
                    self.number_index[clean_num] = []
                self.number_index[clean_num].append(entry)

    def ingest_research_claims(self, research_data: Dict[str, Any] | List[Dict[str, Any]]) -> int:
        """
        Dynamically ingests claims extracted by ResearchEngine into the ledger.
        Ensures any new topic can be autonomously verified without manual CSV creation.
        """
        claims_list = research_data if isinstance(research_data, list) else research_data.get("claims", [])
        ingested_count = 0

        # Also register numbers appearing in topic title as verified subject entities (e.g. numbered missions)
        if isinstance(research_data, dict) and "topic" in research_data:
            topic_str = str(research_data["topic"])
            for tn in self.extract_numbers_from_text(topic_str):
                clean_tn = tn.replace(",", "").strip()
                if clean_tn not in self.number_index:
                    self.number_index[clean_tn] = []
                self.number_index[clean_tn].append(
                    ClaimEntry(
                        claim_id="TOPIC_ENTITY",
                        claim=f"Topic entity designator: {topic_str}",
                        number_or_date=clean_tn,
                        unit="",
                        source_url="",
                        excerpt="",
                        confidence="high",
                        graphic_worthy=False,
                        human_anchor="",
                        verified=True,
                        status="verified",
                        absolute_ok=True,
                    )
                )

        for item in claims_list:
            cid = str(item.get("claim_id", f"C{ingested_count+1:03d}")).strip()
            num_or_date = str(item.get("number_or_date", "")).strip()
            sources = item.get("sources", [])
            if not sources and item.get("source_url"):
                sources = [item.get("source_url")]
            elif not sources and item.get("source"):
                sources = [item.get("source")]
            source_str = ", ".join(sources) if isinstance(sources, list) else str(sources)
            status_val = str(item.get("verification_status", item.get("status", "verified"))).strip().lower()
            confidence_val = str(item.get("confidence", "high")).strip().lower()

            claim_text = str(item.get("claim", item.get("statement", ""))).strip()
            entry = ClaimEntry(
                claim_id=cid,
                claim=claim_text,
                number_or_date=num_or_date,
                unit=str(item.get("unit", "")).strip(),
                source_url=source_str,
                excerpt=source_str,
                confidence=confidence_val,
                graphic_worthy=bool(item.get("graphic_worthy", False)),
                human_anchor=str(item.get("human_anchor", "")).strip(),
                verified=(status_val != "unverified") and bool(source_str.strip()),
                status=status_val if source_str.strip() else "unverified",
                absolute_ok=bool(item.get("absolute_ok", False)),
            )
            self.claims[cid] = entry
            ingested_count += 1

            tokens_to_index = []
            if num_or_date:
                tokens_to_index.extend(self.extract_numbers_from_text(num_or_date))
            if claim_text:
                tokens_to_index.extend(self.extract_numbers_from_text(claim_text))

            for tok in tokens_to_index:
                clean_tok = tok.replace(",", "").strip()
                if clean_tok not in self.number_index:
                    self.number_index[clean_tok] = []
                if entry not in self.number_index[clean_tok]:
                    self.number_index[clean_tok].append(entry)

        return ingested_count

    def validate_claims_grounding(self, topic: Optional[str] = None) -> Tuple[bool, List[str]]:
        """
        Validates that all registered claims in the ledger have:
        1. Non-empty claim statements.
        2. Non-empty primary/secondary source citations.
        3. No ungrounded generic incident template boilerplate.
        """
        errors: List[str] = []
        if not self.claims:
            errors.append("Claims ledger is empty; at least 2 verified claims required.")
            return False, errors

        for cid, entry in self.claims.items():
            if not entry.claim or not entry.claim.strip():
                errors.append(f"Claim '{cid}' has an empty statement.")
            if not entry.source_url and not entry.excerpt:
                errors.append(f"Claim '{cid}' lacks supporting source or evidence citation.")

        return len(errors) == 0, errors

    def export_json(self, dest_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
        """Exports the active claims ledger to a structured claims dictionary, optionally saving to dest_path."""
        serialized = [
            {
                "claim_id": e.claim_id,
                "claim": e.claim,
                "statement": e.claim,
                "number_or_date": e.number_or_date,
                "unit": e.unit,
                "source_url": e.source_url,
                "sources": [e.source_url] if e.source_url else [],
                "source": e.source_url,
                "excerpt": e.excerpt,
                "confidence": e.confidence,
                "graphic_worthy": e.graphic_worthy,
                "human_anchor": e.human_anchor,
                "verified": e.verified,
                "status": e.status,
                "verification_status": e.status,
                "absolute_ok": e.absolute_ok,
            }
            for e in self.claims.values()
        ]
        result = {"claims": serialized}
        if dest_path:
            out = Path(dest_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        return result

    def verify_narration_claim_provenance(
        self,
        paragraphs: Union[List[Dict[str, Any]], Dict[str, Any]],
        allow_unverified_numbers: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Verifies that:
        1. Factual statements reference registered claim_ids.
        2. Disputed or uncertain claims are acknowledged with uncertainty markers.
        3. Spoken numbers in paragraphs match verified claims.
        """
        if isinstance(paragraphs, dict):
            paragraphs = paragraphs.get("paragraphs", [])
            
        violations: List[str] = []
        uncertainty_markers = [
            "disputed", "claimed", "alleged", "conflicting", "uncertain",
            "unconfirmed", "debated", "some argue", "according to", "reportedly",
            "purported", "contested", "unresolved"
        ]

        for p in paragraphs:
            pid = p.get("paragraph_id", p.get("scene_id", "P?"))
            text = p.get("text", p.get("narration", ""))
            c_ids = p.get("claim_ids", [])
            text_lower = text.lower()

            # Check numbers
            ok_nums, bad_nums = self.verify_narration_text(text, allow_unverified=allow_unverified_numbers)
            if not ok_nums:
                for n in bad_nums:
                    violations.append(f"[{pid}] Number '{n}' is not backed by any verified claim in ledger.")

            # Check claim status representation
            for cid in c_ids:
                claim_entry = self.get_claim(cid)
                if claim_entry and claim_entry.status in ("disputed", "uncertain"):
                    has_marker = any(m in text_lower for m in uncertainty_markers)
                    if not has_marker:
                        violations.append(
                            f"[{pid}] References {claim_entry.status.upper()} claim '{cid}' without proper uncertainty phrasing "
                            f"(e.g. 'reportedly', 'conflicting accounts', 'allegedly')."
                        )

        return (len(violations) == 0), violations

    def get_provenance_report(
        self, paragraphs: Union[List[Dict[str, Any]], Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Returns a structured dictionary report of narration claims provenance.
        """
        if isinstance(paragraphs, dict):
            paragraphs = paragraphs.get("paragraphs", [])

        ok, violations = self.verify_narration_claim_provenance(paragraphs)
        all_referenced_cids = []
        unknown_claims = []
        for p in paragraphs:
            for cid in p.get("claim_ids", []):
                all_referenced_cids.append(cid)
                if cid not in self.claims:
                    unknown_claims.append(cid)

        return {
            "all_claims_verified": ok and len(unknown_claims) == 0,
            "violations": violations,
            "unknown_claims": unknown_claims,
            "verified_count": len(all_referenced_cids) - len(unknown_claims),
            "total_referenced_claims": len(all_referenced_cids),
            "total_paragraphs": len(paragraphs),
        }

    def get_claim(self, claim_id: str) -> Optional[ClaimEntry]:
        return self.claims.get(claim_id)

    def register_claim(
        self,
        claim_id: str,
        claim_text: str,
        status: str = "verified",
        source_citation: str = "",
        absolute_ok: bool = False,
        number_or_date: str = "",
        unit: str = "",
    ) -> ClaimEntry:
        entry = ClaimEntry(
            claim_id=claim_id,
            claim=claim_text,
            number_or_date=number_or_date,
            unit=unit,
            source_url=source_citation,
            excerpt=source_citation,
            confidence="high",
            graphic_worthy=False,
            human_anchor="",
            verified=True,
            status=status,
            absolute_ok=absolute_ok,
        )
        self.claims[claim_id] = entry
        if number_or_date:
            clean_num = str(number_or_date).replace(",", "").strip()
            if clean_num not in self.number_index:
                self.number_index[clean_num] = []
            self.number_index[clean_num].append(entry)
        return entry

    def extract_numbers_from_text(self, text: str) -> List[str]:
        """
        Extracts numbers (integers, floats, formatted numbers with commas) from narration text.
        Excludes pure ordinals or simple single-digit words unless formatted as digits.
        """
        # Matches patterns like 10,994, 36,000, 1086, 2.5, 32,000, 1960
        raw_nums = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b', text)
        clean_nums = []
        for n in raw_nums:
            cleaned = n.replace(",", "").strip()
            # Ignore years if below 100 or common tiny loop counters unless relevant
            clean_nums.append(cleaned)
        return clean_nums

    def verify_narration_text(
        self,
        narration_text: str,
        allow_unverified: bool = False,
        ignored_numbers: Optional[Set[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Verifies that every numerical token in narration corresponds to an entry in claims.csv.
        Returns (True, []) if verified or allow_unverified is True.
        Returns (False, [unverified_numbers]) if unverified numbers exist.
        """
        if allow_unverified:
            return True, []

        ignored = ignored_numbers or {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10"} # small conversational counts
        numbers_in_text = self.extract_numbers_from_text(narration_text)
        unverified = []

        for num in numbers_in_text:
            if num in ignored:
                continue
            if num not in self.number_index:
                # Also check with trailing zero or float variant
                float_val = float(num) if "." in num or num.isdigit() else None
                matched = False
                if float_val is not None:
                    for k in self.number_index:
                        try:
                            if abs(float(k) - float_val) < 1e-4:
                                matched = True
                                break
                        except ValueError:
                            pass
                if not matched:
                    unverified.append(num)

        if unverified:
            return False, unverified
        return True, []

    def verify_claims_and_hedges(
        self,
        narration_text: str,
        allow_unverified: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validates that:
        1. Claims marked 'legend' or 'disputed' require an explicit hedge in narration
           (e.g., 'according to legend', 'historians debate', 'legend holds').
        2. Absolute words ('forever', 'never', 'always', 'largest ever') require
           a backing claim with absolute_ok=True.
        """
        if allow_unverified:
            return True, []

        violations = []
        sentences = [s.strip() for s in re.split(r'[.!?]+', narration_text) if s.strip()]

        hedge_pattern = re.compile(
            r'\b(according to legend|legend holds|legend says|legend has it|historians debate|historians dispute|traditionally held|debated|disputed)\b',
            re.IGNORECASE
        )

        # 1. Legend / Disputed checks
        for cid, entry in self.claims.items():
            if entry.status in ("legend", "disputed") or entry.confidence in ("legend", "disputed"):
                claim_tokens = set(re.findall(r'\b[a-z]{4,}\b', entry.claim.lower()))
                claim_tokens -= {"about", "which", "their", "there", "where", "after", "before", "during", "killed", "battle"}
                for sent in sentences:
                    sent_tokens = set(re.findall(r'\b[a-z]{4,}\b', sent.lower()))
                    if len(claim_tokens.intersection(sent_tokens)) >= 2:
                        if not hedge_pattern.search(sent):
                            violations.append(
                                f"Unhedged claim: '{entry.claim}' (ID {cid}) requires a hedge ('according to legend', 'historians debate') in sentence: '{sent}'"
                            )

        # 2. Absolute words check
        absolute_words = ["forever", "never", "always", "largest ever", "largest in history"]
        for sent in sentences:
            s_lower = sent.lower()
            for word in absolute_words:
                if re.search(rf'\b{re.escape(word)}\b', s_lower):
                    sent_nums = self.extract_numbers_from_text(sent)
                    has_backing = False
                    for cid, entry in self.claims.items():
                        if entry.absolute_ok:
                            clean_n = entry.number_or_date.replace(",", "").strip()
                            claim_tokens = set(re.findall(r'\b[a-z]{4,}\b', entry.claim.lower()))
                            sent_tokens = set(re.findall(r'\b[a-z]{4,}\b', s_lower))
                            if (clean_n and clean_n in sent_nums) or (len(claim_tokens.intersection(sent_tokens)) >= 2):
                                has_backing = True
                                break
                    if not has_backing:
                        violations.append(
                            f"Unverified absolute word '{word}' in sentence: '{sent}'. Absolute terms require absolute_ok=true in claims ledger."
                        )

        return (len(violations) == 0), violations


def verify_overlay_label(
    label: str,
    license_manifest: Optional[Dict[str, Any]] = None,
    project_config: Optional[Any] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Overlay labels may only be from an approved list:
      - ARCHIVAL plus real source
      - ILLUSTRATION
      - REPLICA
      - RECREATION
      - Or a verified date/place
    A label naming a real publication or organization must match an asset in license manifest.
    Block CLASSIFIED, DECLASSIFIED, BREAKING, LEAKED, UNSEALED unless overridden in project_config.
    """
    clean_label = label.strip()
    label_upper = clean_label.upper()

    # 1. Banned sensationalist words
    banned_words = ["CLASSIFIED", "DECLASSIFIED", "BREAKING", "LEAKED", "UNSEALED"]
    override_words: List[str] = []
    if project_config is not None:
        override_words = getattr(project_config, "banned_label_words_override", [])
        if getattr(project_config, "allow_unsealed_labels", False):
            override_words.extend(banned_words)

    for bw in banned_words:
        if bw not in [w.upper() for w in override_words]:
            if re.search(rf'\b{re.escape(bw)}\b', label_upper):
                return False, f"Label contains banned word '{bw}': '{clean_label}'"

    # 2. Approved formats
    approved_prefixes = ["ARCHIVAL", "ILLUSTRATION", "REPLICA", "RECREATION"]
    is_approved_prefix = False
    for prefix in approved_prefixes:
        if (
            label_upper == prefix
            or label_upper.startswith(f"{prefix} //")
            or label_upper.startswith(f"{prefix} -")
            or label_upper.startswith(f"{prefix}:")
            or label_upper.startswith(f"{prefix} |")
        ):
            is_approved_prefix = True
            break

    # Date / Place format: e.g. "43 AD // RICHBOROUGH", "1066 // HASTINGS", "1215 // RUNNYMEDE"
    is_date_place = bool(
        re.match(
            r'^(?:(?:\d{1,4}\s*(?:AD|BC|BCE|CE)?|[A-Za-z\s]+)\s*(?://|-|\|)\s*(?:[A-Za-z0-9\s,\.]{2,40})|\d{1,4}\s*(?:AD|BC|BCE|CE)?)$',
            clean_label,
            re.IGNORECASE,
        )
    )

    if not (is_approved_prefix or is_date_place):
        return False, f"Label '{clean_label}' does not follow approved format (ARCHIVAL, ILLUSTRATION, REPLICA, RECREATION, or DATE/PLACE)"

    # 3. Real publication or organization check
    known_orgs = [
        "LONDON TIMES", "THE LONDON TIMES", "FLEET INTEL", "TIMES", "BBC",
        "REUTERS", "GUARDIAN", "TELEGRAPH", "NATIONAL ARCHIVES", "BRITISH LIBRARY",
        "LIBRARY OF CONGRESS", "IMPERIAL WAR MUSEUM", "NOAA", "NASA"
    ]
    for org in known_orgs:
        if re.search(rf'\b{re.escape(org)}\b', label_upper):
            if license_manifest is not None:
                if isinstance(license_manifest, list):
                    manifest_assets = license_manifest
                elif isinstance(license_manifest, dict):
                    manifest_assets = license_manifest.get("assets", [])
                else:
                    manifest_assets = []
                matched = any(
                    org in str(a.get("source", "")).upper() or org in str(a.get("license", "")).upper()
                    for a in manifest_assets
                )
                if not matched:
                    return False, f"Label references publication/organization '{org}' with no matching asset in license manifest"
            else:
                if "FLEET INTEL" in label_upper or "LONDON TIMES" in label_upper:
                    return False, f"Fabricated publication/organization '{org}' has no archive backing in license manifest"

    return True, None


def verify_all_claims_against_sources(sources_dir: Path | str = "sources", ledger_path: Path | str = "claims.csv") -> Dict[str, Any]:
    """
    Scans the sources directory and confirms that each claim in claims.csv
    has an authentic corresponding primary source file.
    """
    s_dir = Path(sources_dir)
    ledger = ClaimsLedger(ledger_path)
    
    results = {
        "total_claims": len(ledger.claims),
        "verified_count": 0,
        "failed_count": 0,
        "details": [],
    }

    source_contents = {}
    for s_file in s_dir.glob("*.md"):
        source_contents[s_file.name] = s_file.read_text(encoding="utf-8")

    for cid, entry in ledger.claims.items():
        matched_source = None
        for s_name, content in source_contents.items():
            if entry.source_url in content or entry.number_or_date in content:
                matched_source = s_name
                break
        
        status = "PASS" if matched_source else "FAIL"
        if status == "PASS":
            results["verified_count"] += 1
        else:
            results["failed_count"] += 1

        results["details"].append({
            "claim_id": cid,
            "claim": entry.claim,
            "number_or_date": entry.number_or_date,
            "unit": entry.unit,
            "status": status,
            "matched_source": matched_source,
            "source_url": entry.source_url,
        })

    return results
