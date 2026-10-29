"""Build separate local-only A/B review handoffs; never publishes post bodies."""
from pathlib import Path
import csv
import hashlib
import io
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'


def main():
    target=PRIVATE/'handoff'
    target.mkdir(parents=True,exist_ok=True)
    required=[ROOT/'人工编码开始这里.md',ROOT/'docs/human-review/字段与代码速查.md',ROOT/'分类编码手册_v1.pdf',
              ROOT/'分类编码手册_v1.md',ROOT/'code/classification_codebook_v1.json']
    assert all(p.is_file()for p in required),'Missing reviewer instructions or codebook.'
    codebook=ROOT/'code/classification_codebook_v1.json'
    bookhash=hashlib.sha256(codebook.read_bytes()).hexdigest()
    output=[]
    for coder in ['A','B']:
        source=PRIVATE/f'human_review_{coder}.csv'
        with source.open(encoding='utf-8-sig',newline='')as f:
            reader=csv.DictReader(f);rows=list(reader);fields=reader.fieldnames
        assert len(rows)==160
        mutable=[k for k in fields if k not in ['sample_id','fulltext','codebook_sha256']]
        assert all(not row[k].strip()for row in rows for k in mutable),'Preserve filled reviews: refuse to package them as blank sheets.'
        assert all(r['codebook_sha256']==bookhash for r in rows)
        notes=io.StringIO(newline='')
        writer=csv.DictWriter(notes,fieldnames=['sample_id','label_code','evidence','note'])
        writer.writeheader()
        writer.writerows({'sample_id':r['sample_id'],'label_code':'','evidence':'','note':''}for r in rows)
        manifest={'coder':coder,'n':160,'codebook_sha256':bookhash,
                  'blank_review_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                  'contains':'Only this reviewer blank sheet, blank evidence notes and shared instructions; no AI predictions, other reviewer or outcomes.',
                  'sharing':'Local-only private handoff to authorized project reviewers; do not upload to public GitHub.'}
        destination=target/f'人工编码_{coder}_v1.zip'
        with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED)as archive:
            archive.write(source,source.name)
            archive.writestr(f'human_evidence_{coder}.csv','\ufeff'+notes.getvalue())
            for p in required:archive.write(p,p.relative_to(ROOT).as_posix())
            archive.writestr('交接版本.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        with zipfile.ZipFile(destination)as archive:
            assert archive.testzip()is None
            names=archive.namelist()
            assert f'human_review_{coder}.csv'in names
            assert not any('coder_'in name or 'prediction'in name or 'agreement'in name for name in names)
            assert len(names)==8
        output.append({'coder':coder,'file':str(destination.relative_to(ROOT)),'rows':160,'contents_checked':True})
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
