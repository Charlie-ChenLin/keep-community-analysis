"""Describe collected comment texts without exporting raw text or user IDs."""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import logging
import os
import re
import unicodedata

import jieba
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT/'code/comment_text_config.json').read_text())


def prepare():
    posts = pd.read_csv(ROOT/'2026Data/Keep Data/sample_post_2022.csv', usecols=['postId', 'userId'])
    raw = pd.read_csv(ROOT/'2026Data/Keep Data/sample_comment_2022.csv')
    assert posts.postId.is_unique
    assert not (raw.groupby('cmtId').nunique(dropna=False)>1).any().any()
    comments = raw.drop_duplicates('cmtId').copy()
    assert comments.cmtId.notna().all() and comments.author_id.notna().all()
    assert comments.postId.isin(posts.postId).all()
    comments['raw_text'] = comments.content.fillna('').astype(str)
    def clean(value):
        value = unicodedata.normalize('NFKC', value.replace('\\n', '\n'))
        value = re.sub(r'https?://\S+|\[[^\[\]]{1,12}\]', ' ', value)
        return re.sub(r'\s+', ' ', value).strip()
    comments['clean_text'] = comments.raw_text.map(clean)
    comments['lexical'] = comments.clean_text.str.contains(r'[\u4e00-\u9fffA-Za-z0-9]', regex=True)
    comments['length'] = comments.clean_text.str.replace(r'\s', '', regex=True).str.len()
    comments['speaker'] = comments.author_id.eq(comments.postId.map(posts.set_index('postId').userId))
    comments['role'] = comments.speaker.map({True:'帖主发言', False:'其他用户发言'})
    for feature, rule in CFG['features'].items():
        pattern = '|'.join(re.escape(word) for word in rule['terms'])
        comments[feature] = comments.clean_text.str.contains(pattern, regex=True)
    return raw, comments


def analyze():
    raw, comments = prepare()
    jieba.setLogLevel(logging.ERROR);jieba.dt.tmp_dir = str(ROOT/'results')
    stop = set((ROOT/'code/stopwords.txt').read_text(encoding='utf-8-sig').split())
    stop.update('今天 一个 自己 这个 那个 就是 什么 没有 可以 一下 已经 还是 这样 现在 怎么 然后 因为 所以 但是 不是 只是 这些 那些'.split())
    documents = Counter(); senders = defaultdict(set)
    for text, author in zip(comments.clean_text, comments.author_id):
        terms = {word for word in jieba.lcut(text)
                 if len(word)>=2 and re.fullmatch(r'[\u4e00-\u9fff]+', word) and word not in stop}
        documents.update(terms)
        for term in terms:senders[term].add(author)
    rows = [{'term':term, 'comments':count, 'share':count/len(comments),
             'senders':len(senders[term]), 'sender_share':len(senders[term])/comments.author_id.nunique()}
            for term,count in sorted(documents.items(), key=lambda item:(-item[1],item[0]))
            if len(senders[term])>=CFG['minimum_term_senders']][:CFG['max_exported_terms']]
    terms = pd.DataFrame(rows)
    terms.to_csv(ROOT/'results/comment_text_terms.csv', index=False, encoding='utf-8-sig')
    rows = []
    for role, part in [('全部评论',comments), *list(comments.groupby('role',sort=True))]:
        for feature, rule in CFG['features'].items():
            hits = part.loc[part[feature]]
            rows.append({'role':role, 'feature':feature, 'label':rule['label'], 'n':len(part),
                         'hits':len(hits), 'share':len(hits)/len(part),
                         'senders_hit':hits.author_id.nunique(), 'senders':part.author_id.nunique()})
    features = pd.DataFrame(rows)
    features.to_csv(ROOT/'results/comment_text_features.csv', index=False, encoding='utf-8-sig')
    repeated = comments.raw_text.map(lambda value:re.sub(r'\s+','',unicodedata.normalize('NFKC',value)))
    summary = {
        'analysis_date':CFG['analysis_date'], 'raw_comments':len(raw), 'comments':len(comments),
        'duplicate_ids_removed':len(raw)-len(comments), 'missing_content':int(comments.content.isna().sum()),
        'senders':int(comments.author_id.nunique()), 'posts':int(comments.postId.nunique()),
        'lexical_comments':int(comments.lexical.sum()), 'markers_or_symbols_only':int((~comments.lexical).sum()),
        'markers_or_symbols_only_share':float((~comments.lexical).mean()),
        'bracket_marker_comments':int(comments.raw_text.str.contains(r'\[[^\[\]]{1,12}\]',regex=True).sum()),
        'median_clean_length':float(comments.length.median()), 'p75_clean_length':float(comments.length.quantile(.75)),
        'repeated_normalized_text_comments':int(repeated.duplicated(keep=False).sum()),
        'unique_normalized_texts':int(repeated.nunique()),
        'roles':{role:{'comments':len(part),'senders':int(part.author_id.nunique())}
                 for role,part in comments.groupby('role',sort=True)},
        'features':{row.feature:{'label':row.label,'hits':int(row.hits),'share':float(row.share),
                    'senders_hit':int(row.senders_hit)} for row in features.loc[features.role.eq('全部评论')].itertuples()},
        'source_sha256':{str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [ROOT/'2026Data/Keep Data/sample_comment_2022.csv',
                                      ROOT/'2026Data/Keep Data/sample_post_2022.csv',ROOT/'code/comment_text_config.json',
                                      ROOT/'code/stopwords.txt']},
        'definitions':{'term_frequency':'含该词的评论数，每条评论至多计一次；另报告去重发言用户数。',
            'roles':'发言者是否为所属帖子作者；包括根评论、明确回复和自我互动，不等同于网络中的回复角色。',
            'features':'四项规则可重叠，分母均为该角色全部已采集评论；未命中不等于没有该语义。',
            'text_scope':'保留不同评论ID下的重复短句和84次自我互动；与非自我网络事件分母不同。'}
    }
    (ROOT/'results/comment_text_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    plot(terms, features)
    return summary


def plot(terms, features):
    font=Path(os.environ.get('REPORT_FONT','/Library/Fonts/Arial Unicode.ttf'))
    if font.exists():
        font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,
                         'axes.unicode_minus':False,'text.color':'#243746','axes.labelcolor':'#243746'})
    top=terms.head(12).iloc[::-1];fig,ax=plt.subplots(figsize=(10.2,4.2))
    ax.barh(top.term, top.share, color='#356D9A',height=.68)
    for y,row in enumerate(top.itertuples()):ax.text(row.share+.002,y,f'{row.share:.1%}',va='center',fontsize=10)
    ax.set(xlabel='占全部已采集评论的比例',title='评论中的常见词语：按评论文档频数排序',xlim=(0,top.share.max()*1.22))
    ax.xaxis.set_major_formatter(PercentFormatter(1));fig.tight_layout()
    fig.savefig(ROOT/'figures/14_comment_words.png',dpi=190,bbox_inches='tight');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10.2,3.5));order=list(CFG['features'])
    for offset,(role,color) in enumerate([('帖主发言','#B88425'),('其他用户发言','#356D9A')]):
        part=features.loc[features.role.eq(role)].set_index('feature').loc[order]
        y=[i+(offset-.5)*.34 for i in range(len(order))]
        ax.barh(y,part.share,height=.30,color=color,label=f'{role}（n={int(part.n.iloc[0]):,}）')
        for yy,value in zip(y,part.share):ax.text(value+.003,yy,f'{value:.1%}',va='center',fontsize=10)
    ax.set_yticks(range(len(order)),[CFG['features'][key]['label'] for key in order]);ax.invert_yaxis()
    ax.set(xlabel='占该角色全部已采集评论的比例',title='不同发言角色的字面表达命中率')
    ax.set_xlim(0,features.share.max()*1.25);ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc='lower right',frameon=False);fig.tight_layout()
    fig.savefig(ROOT/'figures/15_comment_expressions.png',dpi=190,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':
    result=analyze()
    print(json.dumps({key:result[key] for key in ['comments','senders','markers_or_symbols_only','median_clean_length','features']},ensure_ascii=False,indent=2))
