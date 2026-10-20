"""Two bounded supplements: author weighting of frozen topics and direct replies.

Only aggregate tables are exported. Original models, figures and result files
are read-only. No sentiment labels or parameters are selected from outcomes.
"""
from pathlib import Path
import hashlib
import json
import re
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT/'code/supplemental_config.json').read_text())
RULES = json.loads((ROOT/'code/comment_text_config.json').read_text())


def topic_author_comparison():
    source = ROOT/CONFIG['topic_comparison']['source']
    if not source.is_file():
        raise FileNotFoundError('缺少本地主题权重缓存；放置课程数据后运行 make experiments。')
    frame = pd.read_csv(source, dtype={'postId':'string', 'author':'string'})
    columns = CONFIG['topic_comparison']['components']
    assert frame.postId.is_unique and frame.author.notna().all()
    weights = frame[columns].to_numpy()
    assert np.isfinite(weights).all() and (weights >= 0).all()
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-8)
    posts = pd.read_csv(ROOT/'2026Data/Keep Data/sample_post_2022.csv',
                        usecols=['postId','userId'], dtype='string')
    assert posts.postId.is_unique
    assert frame.postId.isin(posts.postId).all()
    assert frame.author.eq(frame.postId.map(posts.set_index('postId').userId)).all()
    frame['dominant'] = weights.argmax(axis=1)
    counts = pd.crosstab(frame.author, frame.dominant).reindex(columns=range(len(columns)), fill_value=0)
    author_shares = counts.div(counts.sum(axis=1), axis=0)
    labels = json.loads((ROOT/'code/topic_labels.json').read_text())['labels']
    result = []
    for topic in range(len(columns)):
        documents = int(counts[topic].sum())
        post_share = documents/len(frame)
        author_share = float(author_shares[topic].mean())
        result.append({'topic':topic,'label':labels[str(topic)],'documents':documents,
                       'authors_with_dominant_topic':int(counts[topic].gt(0).sum()),
                       'post_equal_share':post_share,'author_equal_share':author_share,
                       'difference_percentage_points':100*(author_share-post_share)})
    return pd.DataFrame(result), {'documents':len(frame),'authors':len(counts),
                                 'vocabulary_and_model_unchanged':True}


def clean_text(value):
    text = unicodedata.normalize('NFKC', str(value).replace('\\n','\n'))
    text = re.sub(r'https?://\S+|\[[^\[\]]{1,12}\]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def comment_response_comparison():
    posts = pd.read_csv(ROOT/'2026Data/Keep Data/sample_post_2022.csv',
                        usecols=['postId','userId'], dtype='string')
    columns = ['cmtId','postId','author_id','content','created','replyUserId','reply','parentId']
    raw = pd.read_csv(ROOT/'2026Data/Keep Data/sample_comment_2022.csv', usecols=columns, dtype='string')
    assert not (raw.groupby('cmtId').nunique(dropna=False)>1).any().any()
    comments = raw.drop_duplicates('cmtId').copy()
    assert comments.cmtId.notna().all() and comments.author_id.notna().all()
    assert posts.postId.is_unique and comments.postId.isin(posts.postId).all()
    comments['post_author'] = comments.postId.map(posts.set_index('postId').userId)
    comments['time'] = pd.to_datetime(comments.created, utc=True)
    assert comments.time.notna().all()
    comments['text'] = comments.content.fillna('').map(clean_text)
    for feature in ['encouragement','thanks']:
        pattern = '|'.join(re.escape(w) for w in RULES['features'][feature]['terms'])
        comments[feature] = comments.text.str.contains(pattern, regex=True)
    root_mask = comments[['replyUserId','reply','parentId']].isna().all(axis=1)
    roots = comments.loc[root_mask & comments.author_id.ne(comments.post_author)].copy().set_index('cmtId')
    replies = comments.loc[comments.author_id.eq(comments.post_author) & comments.reply.isin(roots.index)].copy()
    # The reply must address this exact root comment and its sender, not merely
    # another participant within the same thread.
    assert replies.postId.eq(replies.reply.map(roots.postId)).all()
    assert replies.parentId.eq(replies.reply).all()
    assert replies.replyUserId.eq(replies.reply.map(roots.author_id)).all()
    replies['delay_hours'] = (replies.time-replies.reply.map(roots.time)).dt.total_seconds()/3600
    assert replies.delay_hours.ge(0).all()
    eligible = replies.loc[replies.delay_hours.le(CONFIG['comment_responses']['maximum_delay_hours'])].copy()
    first_time = eligible.groupby('reply').time.min()
    first = eligible.loc[eligible.time.eq(eligible.reply.map(first_time))]
    first_thanks = first.groupby('reply').thanks.any()
    roots['observed_direct_reply'] = roots.index.isin(first_time.index)
    roots['thanks_in_first_reply'] = roots.index.isin(first_thanks.loc[first_thanks].index)
    rows = []
    for label, mask in [('全部外来根评论',pd.Series(True,index=roots.index)),
                        ('命中鼓励或赞许词',roots.encouragement),
                        ('未命中鼓励或赞许词',~roots.encouragement)]:
        part = roots.loc[mask]
        n = len(part); replied = int(part.observed_direct_reply.sum()); thanks = int(part.thanks_in_first_reply.sum())
        rows.append({'root_group':label,'roots':n,'post_authors':int(part.post_author.nunique()),
                     'root_senders':int(part.author_id.nunique()),'observed_direct_replies':replied,
                     'observed_direct_reply_share':replied/n if n else None,
                     'thanks_in_first_reply':thanks,
                     'thanks_among_observed_first_replies':thanks/replied if replied else None,
                     'thanks_first_reply_share_all_roots':thanks/n if n else None})
    audit = {'raw_comments':len(raw),'deduplicated_comments':len(comments),
             'all_roots_including_self':int(root_mask.sum()),'external_roots':len(roots),
             'eligible_post_authors':int(roots.post_author.nunique()),
             'matched_owner_direct_reply_events_all_delays':len(replies),
             'matched_owner_direct_reply_events_within_window':len(eligible),
             'roots_with_observed_direct_reply':len(first_time),
             'roots_with_tied_first_reply_timestamp':int(first.groupby('reply').size().gt(1).sum()),
             'window_hours_after_root_comment':CONFIG['comment_responses']['maximum_delay_hours'],
             'missing_direct_reply_reference_all_comments':int((comments.reply.notna() & ~comments.reply.isin(comments.cmtId)).sum()),
             'note':'未见符合条件的直接回复不等于实际未回复。根评论起算窗口不同于原网络的发帖后7天窗口。'}
    return pd.DataFrame(rows), audit


def run():
    topics, topic_scope = topic_author_comparison()
    threads, thread_scope = comment_response_comparison()
    topics.to_csv(ROOT/'results/supplemental_topic_author_weighting.csv',index=False,encoding='utf-8-sig')
    threads.to_csv(ROOT/'results/supplemental_direct_reply_language.csv',index=False,encoding='utf-8-sig')
    paths = ['2026Data/Keep Data/sample_post_2022.csv','2026Data/Keep Data/sample_comment_2022.csv',
             'results/extension_post_topics.csv','code/comment_text_config.json','code/topic_labels.json',
             'code/supplemental_config.json']
    summary = {'analysis_date':CONFIG['analysis_date'],'topic_comparison':topic_scope,
               'direct_reply_comparison':thread_scope,
               'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
               'interpretation':'两项描述性补充，不重新估计主回归或主题模型；不进行显著性检验，不识别语义链条或因果。',
               'export_scope':'仅导出聚合表；逐条文本、用户ID及根评论—回复配对不公开。'}
    (ROOT/'results/supplemental_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return topics, threads, summary


if __name__ == '__main__':
    tables = run()
    print(tables[0].to_string(index=False))
    print(tables[1].to_string(index=False))
    print(json.dumps(tables[2]['direct_reply_comparison'],ensure_ascii=False,indent=2))
