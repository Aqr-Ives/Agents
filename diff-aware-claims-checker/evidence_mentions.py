"""Deterministic extraction of explicit evidence mentions, never support.

Author: Diff-Aware Claims Checker project. Date: 2026-10-13.
Purpose: explicit evidence-label extraction without support inference.
Status: supported syntactic patterns only; source resolution remains unresolved.
Inputs: original paragraph text.
Outputs: syntactic mentions and three-entity dependency schema. Standard library
only. Reference-label IDs are manuscript/version scoped, not source identities.
"""
import re

LABEL = r'(?:S\d+|\d+)[A-Za-z]?'
NAMED = re.compile(r'\b(?P<kind>Tables?|Figures?|Figs?\.?|References?)\s+'
    r'(?P<labels>'+LABEL+r'(?:(?:\s*,\s*(?:and\s+)?|\s+and\s+|\s*&\s*)'+LABEL+r')*)'
    r'(?!\w|\.\d)', re.IGNORECASE)
BRACKET = re.compile(r'\[(?P<labels>\d+(?:\s*(?:,|[-\u2013])\s*\d+)*)\]')


def extract_mentions(text: str) -> list[dict]:
    """Retain occurrence spans and original mention text; unsupported forms skip."""
    result = []
    for match in NAMED.finditer(text):
        kind = match.group('kind').casefold()
        evidence_type = 'TABLE' if kind.startswith('table') else ('FIGURE' if kind.startswith('fig') else 'REFERENCE')
        if re.match(r'\s*[-\u2013\u2014]', text[match.end():]):
            continue  # Named ranges unsupported; do not silently extract prefix.
        labels = re.findall(LABEL, match.group('labels'), re.IGNORECASE)
        if evidence_type == 'REFERENCE' and any(not label.isdigit() for label in labels):
            continue
        for label in labels:
            prefix = {'TABLE':'Table', 'FIGURE':'Figure', 'REFERENCE':'Reference'}[evidence_type]
            result.append({'evidence_type':evidence_type, 'original_text':match.group(0),
                'normalized_label':prefix+' '+label.upper(), 'label_token':label.upper(),
                'char_start':match.start(), 'char_end':match.end(), 'pattern':'named_label_list'})
    for match in BRACKET.finditer(text):
        labels=[]; valid=True
        for part in match.group('labels').split(','):
            bounds=re.split(r'[-\u2013]',part.strip())
            first=int(bounds[0]); last=int(bounds[-1])
            if first<1 or last<first or last-first>49:
                valid=False;break
            labels.extend(str(i) for i in range(first,last+1))
        if valid:
            for label in dict.fromkeys(labels):
                result.append({'evidence_type':'REFERENCE', 'original_text':match.group(0),
                    'normalized_label':'Reference '+label, 'label_token':label,
                    'char_start':match.start(), 'char_end':match.end(), 'pattern':'bracket_numeric_list_or_range'})
    return sorted(result,key=lambda m:(m['char_start'],m['char_end']))


def dependency_schema(old_claims, new_claims, records):
    """Create Claim Versions, unresolved Evidence Items, and NOT_CHECKED edges."""
    versions=[];items={};edges=[]
    record_ids={}
    for record in records:
        for component in record.get('source_components',[]):
            key=(component['version'], component['location']['input_paragraph'])
            record_ids.setdefault(key,[]).append(record['review_record_id'])
    for claim in list(old_claims)+list(new_claims):
        cv_id=f'{claim.version}:{claim.claim_id}:{claim.input_paragraph}'
        linked=record_ids.get((claim.version,claim.input_paragraph),[])
        actions=[r['action'] for r in records if r['review_record_id'] in linked]
        versions.append({'claim_id':claim.claim_id,'claim_version_id':cv_id,
            'version_id':claim.version,'text':claim.text,'location':claim.location,
            'claim_type':'unknown','review_action':actions[0] if len(set(actions))==1 else None,
            'verification_status':'UNVERIFIED','review_record_ids':linked,
            'provenance':{'method':'original_plain_text_paragraph','identity_scope':'comparison-local paragraph; not semantic identity'}})
        for ordinal,mention in enumerate(extract_mentions(claim.text),1):
            eid=f'mention:{claim.version}:{mention["evidence_type"]}:{mention["label_token"]}'
            items.setdefault(eid,{'evidence_id':eid,'evidence_type':mention['evidence_type'],
                'document_id':None,'display_label':mention['normalized_label'],
                'locator':None,'source_identity':None,'source_version':None,'content_hash':None,
                'identity_status':'UNRESOLVED_LABEL','identity_scope':'manuscript version only; reference numbering is not stable source identity'})
            edges.append({'edge_id':cv_id+f':mention:{ordinal}','claim_id':claim.claim_id,
                'claim_version_id':cv_id,'evidence_id':eid,'relationship_role':'unknown',
                'extraction_method':'deterministic_explicit_mention','evidence_check_status':'NOT_CHECKED',
                'verification_note':None,'reviewer':None,'last_checked_version':None,
                'mention':mention,'source_location':claim.location,'review_record_ids':linked,
                'citation_display_label':mention['label_token'] if mention['evidence_type']=='REFERENCE' else None,
                'provenance':{'pattern':mention['pattern'],'span_basis':'characters in original paragraph','support_inferred':False}})
    return {'schema_version':'0','claim_versions':versions,'evidence_items':list(items.values()),'dependency_edges':edges}
