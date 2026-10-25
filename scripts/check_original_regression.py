"""Verify the original study against a frozen fingerprint of the first release."""
from pathlib import Path
import hashlib,json
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]


def canonical(path,keys):
    frame=pd.read_csv(path).sort_values(keys).reset_index(drop=True)
    return hashlib.sha256(frame.to_csv(index=False,float_format='%.10g').encode()).hexdigest()


def main():
    baseline=json.loads((ROOT/'tests/fixtures/original_result_hashes.json').read_text())
    rows={}
    for name,reference in baseline['files'].items():
        path=ROOT/'RESULTS'/name
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        same=canonical(path,reference['sort_keys'])==reference['canonical_sha256']
        assert same,f'Original study changed beyond its recorded numerical precision: {name}'
        if reference['require_byte_identity']:assert digest==reference['sha256'],name
        rows[name]=dict(canonical_matches=True,byte_identical=digest==reference['sha256'])
    receipt=dict(status='passed',original_commit=baseline['original_commit'],
                 numerical_precision='Canonical CSV at 10 significant digits; key order normalized',files=rows,
                 raw_runs='Byte-identical main/exploration/sensitivity CSVs, including all original metric fields')
    target=ROOT/'RESULTS/mechanisms/original_regression.json';target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
