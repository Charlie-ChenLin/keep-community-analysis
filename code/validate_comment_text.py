"""Independently reconcile comment aggregates against deduplicated input rows."""
from pathlib import Path
import json
import logging
import re
import unicodedata

import jieba
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]


def main():
    cfg=json.loads((ROOT/'code/comment_text_config.json').read_text())
    summary=json.loads((ROOT/'results/comment_text_summary.json').read_text())
    raw=pd.read_csv(ROOT/'2026Data/Keep Data/sample_comment_2022.csv')
    c=raw.drop_duplicates('cmtId').copy()
    p=pd.read_csv(ROOT/'2026Data/Keep Data/sample_post_2022.csv',usecols=['postId','userId'])
    normalized=c.content.fillna('').map(lambda x:unicodedata.normalize('NFKC',str(x).replace('\\n','\n')))
    normalized=normalized.str.replace(r'https?://\S+|\[[^\[\]]{1,12}\]',' ',regex=True).str.replace(r'\s+',' ',regex=True).str.strip()
    own=c.author_id.eq(c.postId.map(dict(zip(p.postId,p.userId))))
    roles=pd.Series(np.where(own,'帖主发言','其他用户发言'),index=c.index)
    checks=[]
    def check(name,passed):
        checks.append({'check':name,'passed':bool(passed)})
    check('唯一评论、去重规模及关联',c.cmtId.is_unique and c.cmtId.notna().all() and c.author_id.notna().all() and len(c)==summary['comments'] and len(raw)-len(c)==summary['duplicate_ids_removed'] and c.postId.isin(p.postId).all())
    check('缺失、用户与帖子分母',int(c.content.isna().sum())==summary['missing_content'] and c.author_id.nunique()==summary['senders'] and c.postId.nunique()==summary['posts'])
    lexical=normalized.str.contains(r'[\u4e00-\u9fffA-Za-z0-9]',regex=True)
    check('仅标记或符号计数',int((~lexical).sum())==summary['markers_or_symbols_only'])
    check('清理后字符数中位数',normalized.str.replace(r'\s','',regex=True).str.len().median()==summary['median_clean_length'])
    features=pd.read_csv(ROOT/'results/comment_text_features.csv')
    for row in features.itertuples():
        eligible=pd.Series(True,index=c.index) if row.role=='全部评论' else roles.eq(row.role)
        terms=cfg['features'][row.feature]['terms']
        hits=normalized.map(lambda s:any(term in s for term in terms)) & eligible
        check(f'{row.role}：{row.label}',len(c.loc[eligible])==row.n and int(hits.sum())==row.hits
              and np.isclose(row.share,hits.sum()/eligible.sum()) and c.loc[hits,'author_id'].nunique()==row.senders_hit)
    jieba.setLogLevel(logging.ERROR);jieba.dt.tmp_dir=str(ROOT/'results')
    stop=set((ROOT/'code/stopwords.txt').read_text(encoding='utf-8-sig').split())
    stop.update('今天 一个 自己 这个 那个 就是 什么 没有 可以 一下 已经 还是 这样 现在 怎么 然后 因为 所以 但是 不是 只是 这些 那些'.split())
    tokens=normalized.map(jieba.lcut).explode().rename('term').to_frame().join(c[['cmtId','author_id']])
    tokens=tokens.loc[tokens.term.str.fullmatch(r'[\u4e00-\u9fff]{2,}') & ~tokens.term.isin(stop)].drop_duplicates(['cmtId','term'])
    expected=tokens.groupby('term').agg(comments=('cmtId','size'),senders=('author_id','nunique'))
    actual=pd.read_csv(ROOT/'results/comment_text_terms.csv').set_index('term')
    check(f'{len(actual)}个词项的独立聚合复算',len(actual)==cfg['max_exported_terms'] and actual[['comments','senders']].equals(expected.loc[actual.index,['comments','senders']]))
    check('词项分母与用户覆盖',np.allclose(actual.share,actual.comments/len(c)) and np.allclose(actual.sender_share,actual.senders/c.author_id.nunique()))
    check('角色评论互斥且覆盖全部记录',sum(s['comments'] for s in summary['roles'].values())==len(c))
    (ROOT/'validation/comment_text_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    assert all(row['passed'] for row in checks),checks
    print('Passed',len(checks),'independent comment-text checks.')
    return checks


if __name__=='__main__':main()
