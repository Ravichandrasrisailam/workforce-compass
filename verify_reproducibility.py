"""Run the required full dataset twice, comparing all exported file checksums."""
import json
import tempfile
from pathlib import Path
from workforce import generate, analyze, export

def main():
    manifests=[]; summaries=[]
    config=dict(employees=5000,skills=300,projects=500,months=12,seed=20261022)
    for _ in range(2):
        t,truth=generate(**config)
        gaps,util,findings=analyze(t); t['GapAnalysis']=gaps
        with tempfile.TemporaryDirectory() as folder:
            summaries.append(export(folder,t,truth,util,findings,config))
            manifests.append(json.loads((Path(folder)/'manifest.json').read_text()))
    assert manifests[0]==manifests[1], 'Checksums differ'
    assert summaries[0]==summaries[1], 'Counts differ'
    assert summaries[0]['passed'] and summaries[0]['known_anomaly_recall']==1
    Path('verification').mkdir(exist_ok=True)
    result=dict(reproducible=True,runs=2,manifest=manifests[0],summary=summaries[0])
    Path('verification/full_scale.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(summaries[0],indent=2))
    print('Two full-scale runs: identical row counts and SHA-256 checksums.')

if __name__=='__main__': main()
