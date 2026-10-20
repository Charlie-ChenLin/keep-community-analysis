"""Independently audit the two new aggregate tables with csv and dictionaries."""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import csv
import json
import math
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def rows(path):
    with (ROOT/path).open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def main():
    checks=[]
    def check(name, condition):
        checks.append({'name':name,'passed':bool(condition)})
        assert condition,name
    topics=rows('results/extension_post_topics.csv');counts=Counter();authors=defaultdict(Counter)
    for r in topics:
        weights=[float(r[f'topic_{i}']) for i in range(5)]
        assert all(math.isfinite(v) and v>=0 for v in weights) and abs(sum(weights)-1)<1e-8
        dominant=max(range(5),key=lambda i:weights[i])
        counts[dominant]+=1;authors[r['author']][dominant]+=1
    published=rows('results/supplemental_topic_author_weighting.csv')
    old={int(r['topic']):r for r in rows('results/extension_topics.csv')}
    check('主题样本范围与既有结果一致',len(topics)==2470 and len(authors)==86 and len({r['postId'] for r in topics})==len(topics))
    for r in published:
        i=int(r['topic']);post_share=counts[i]/len(topics)
        author_share=sum(c[i]/sum(c.values()) for c in authors.values())/len(authors)
        check(f'主题{i+1}的文档数及两种权重直接复算',counts[i]==int(r['documents'])==int(old[i]['dominant_documents'])
              and abs(float(r['post_equal_share'])-post_share)<1e-12
              and abs(float(r['author_equal_share'])-author_share)<1e-12
              and abs(float(r['difference_percentage_points'])-100*(author_share-post_share))<1e-10)
    check('两种主题分布分别加总为一',all(abs(sum(float(r[key]) for r in published)-1)<1e-12 for key in ['post_equal_share','author_equal_share']))
    posts={r['postId']:r['userId'] for r in rows('2026Data/Keep Data/sample_post_2022.csv')}
    raw=rows('2026Data/Keep Data/sample_comment_2022.csv');comments={}
    for r in raw:
        if r['cmtId'] in comments:assert r==comments[r['cmtId']]
        comments[r['cmtId']]=r
    config=json.loads((ROOT/'code/supplemental_config.json').read_text())
    missing=set(config['comment_responses']['missing_id_tokens'])
    roots={k:r for k,r in comments.items() if all(r[f] in missing for f in ['replyUserId','reply','parentId']) and r['author_id']!=posts[r['postId']]}
    rules=json.loads((ROOT/'code/comment_text_config.json').read_text())['features']
    def contains(record, feature):
        text=unicodedata.normalize('NFKC',record['content'].replace('\\n','\n'))
        text=re.sub(r'https?://\S+',' ',text)
        text=re.sub(r'\[[^\[\]]{1,12}\]',' ',text)
        text=' '.join(text.split())
        return any(word in text for word in rules[feature]['terms'])
    def time(record):return datetime.fromisoformat(record['created'].replace('Z','+00:00'))
    first={};direct_events=0;all_events=0;ties=Counter()
    for r in comments.values():
        root=roots.get(r['reply'])
        if root is None or r['author_id']!=posts[r['postId']]:continue
        assert r['parentId']==root['cmtId'] and r['postId']==root['postId'] and r['replyUserId']==root['author_id']
        all_events+=1;delay=(time(r)-time(root)).total_seconds()/3600
        assert delay>=0
        if delay>config['comment_responses']['maximum_delay_hours']:continue
        direct_events+=1;key=root['cmtId'];moment=time(r);thanks=contains(r,'thanks')
        if key not in first or moment<first[key][0]:first[key]=(moment,thanks);ties[key]=1
        elif moment==first[key][0]:first[key]=(moment,thanks or first[key][1]);ties[key]+=1
    scope=json.loads((ROOT/'results/supplemental_summary.json').read_text())['direct_reply_comparison']
    check('外来根评论与既有口径对齐',len(roots)==6609 and len(comments)==11595)
    check('直接回复的指向与时间窗口直接复算',len(first)==scope['roots_with_observed_direct_reply']
          and direct_events==scope['matched_owner_direct_reply_events_within_window']
          and all_events==scope['matched_owner_direct_reply_events_all_delays'])
    check('同一最早时点的处理对齐',sum(v>1 for v in ties.values())==scope['roots_with_tied_first_reply_timestamp'])
    table=rows('results/supplemental_direct_reply_language.csv')
    for r in table:
        chosen=[v for v in roots.values() if r['root_group']=='全部外来根评论'
                or contains(v,'encouragement')==(r['root_group']=='命中鼓励或赞许词')]
        n=len(chosen);replied=sum(v['cmtId'] in first for v in chosen)
        thanks=sum(bool(first.get(v['cmtId'],(None,False))[1]) for v in chosen)
        check(r['root_group']+'：人数、回复及感谢分母独立复核',n==int(r['roots']) and replied==int(r['observed_direct_replies'])
              and thanks==int(r['thanks_in_first_reply'])
              and len({posts[v['postId']] for v in chosen})==int(r['post_authors'])
              and abs(replied/n-float(r['observed_direct_reply_share']))<1e-12
              and abs(thanks/replied-float(r['thanks_among_observed_first_replies']))<1e-12)
    check('命中和未命中分组互斥且覆盖总体',sum(int(r['roots']) for r in table[1:])==len(roots))
    (ROOT/'validation/supplemental_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
    return checks


if __name__ == '__main__':
    result=main();print('Independent supplemental checks passed:',len(result))
