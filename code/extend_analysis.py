"""Exploratory extensions: coverage, NMF, held-out prediction, influence, timing.

The existing five-feature regression remains the primary analysis. This script
does not tune model settings against test outcomes or revise the original lexicon.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import logging
import re
import time

import numpy as np
import pandas as pd
import scipy.linalg as la
from scipy.optimize import linear_sum_assignment
from scipy.stats import spearmanr
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
import networkx as nx
import jieba
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import analyze as base

ROOT=base.ROOT
RESULT=base.RESULT
FIG=base.FIG
CFG=json.loads((ROOT/'code/extension_config.json').read_text())
SEED=CFG['seed']
LABELS={'mean':'训练集均值','structured':'结构化基线','dictionary':'结构化＋词典','char_text':'结构化＋词典＋字符文本'}


def csv(frame,name):base.save_csv(frame,'extension_'+name+'.csv')


def coverage(posts):
    media=posts.groupby('contentTypeStr').agg(posts=('postId','size'),visible=('has_text','sum'),
        mean_likes=('likes','mean')).reset_index()
    media['visible_share']=media.visible/media.posts
    csv(media,'coverage_media')
    author=posts.groupby('author').agg(posts=('postId','size'),visible=('has_text','sum'),mean_likes=('likes','mean'),
        median_likes=('likes','median')).reset_index()
    author['visible_share']=author.visible/author.posts
    anon={u:f'A{i+1:03d}' for i,u in enumerate(sorted(posts.author.unique()))}
    author['author']=author.author.map(anon)
    csv(author,'coverage_authors')
    return {'authors_without_visible_body':int(author.visible.eq(0).sum()),
        'authors_all_bodies_visible':int(author.visible.eq(author.posts).sum()),
        'author_visible_share_median':float(author.visible_share.median()),
        'missing_body_media_counts':{r.contentTypeStr:int(r.posts-r.visible) for r in media.itertuples()},
        'textual_body_rows':int(posts.length.gt(0).sum())}


def tokenize(text):
    return [w for w in jieba.lcut(re.sub(r'@[^\s@]+',' ',text))
            if len(w)>=2 and re.fullmatch(r'[\u4e00-\u9fff]+',w)]


def topic_model(posts):
    settings=CFG['nmf'];k=settings['topics']
    jieba.setLogLevel(logging.ERROR);jieba.dt.tmp_dir=str(RESULT)
    stop=set((ROOT/'code/stopwords.txt').read_text(encoding='utf-8-sig').split())
    stop.update('今天 每天 一个 自己 这个 那个 真的 还是 就是 什么 没有 可以 一下 已经 感觉 一天 还有 这样 不要 现在 时候 怎么 然后 因为 所以 但是 不是 只是 这些 那些'.split())
    tokens=posts.clean_text.map(lambda s:[w for w in tokenize(s) if w not in stop])
    eligible=tokens.map(len).ge(settings['min_tokens'])
    sub=posts.loc[eligible].copy();texts=tokens.loc[eligible].map(' '.join)
    vectorizer=TfidfVectorizer(tokenizer=str.split,token_pattern=None,lowercase=False,
        min_df=settings['min_df'],max_df=settings['max_df'],max_features=settings['max_features'])
    matrix=vectorizer.fit_transform(texts)
    ok=np.asarray(matrix.getnnz(axis=1)>0)
    sub=sub.iloc[np.flatnonzero(ok)].copy();matrix=matrix[ok]
    model=NMF(n_components=k,init='nndsvdar',max_iter=settings['max_iter'],random_state=SEED,tol=1e-4)
    w=model.fit_transform(matrix);h=model.components_
    # Remove NMF's arbitrary component scaling before normalizing document weights.
    contribution=w*h.sum(axis=1)[None,:]
    fitted_document_count=len(sub)
    assigned=contribution.sum(axis=1)>settings['minimum_total_topic_contribution']
    sub=sub.iloc[np.flatnonzero(assigned)].copy();contribution=contribution[assigned]
    weights=contribution/contribution.sum(axis=1,keepdims=True)
    names=vectorizer.get_feature_names_out()
    top_sets=[set(names[row.argsort()[-10:]]) for row in h]
    rows=[]
    dominant=weights.argmax(axis=1)
    for i in range(k):
        author_counts=sub.loc[dominant==i,'author'].value_counts()
        rows.append({'topic':i,'label':f'主题{i+1}','keywords':'、'.join(names[h[i].argsort()[-12:][::-1]]),
            'dominant_documents':int((dominant==i).sum()),'dominant_share':float((dominant==i).mean()),
            'mean_weight':float(weights[:,i].mean()),'dominant_authors':len(author_counts),
            'largest_author_share':float(author_counts.iloc[0]/author_counts.sum()) if len(author_counts) else None})
    csv(pd.DataFrame(rows),'topics')
    stability=[]
    ref=h/np.maximum(np.linalg.norm(h,axis=1,keepdims=True),1e-12)
    for seed in settings['stability_seeds']:
        other=NMF(n_components=k,init='nndsvdar',max_iter=settings['max_iter'],random_state=seed,tol=1e-4).fit(matrix)
        hh=other.components_;norm=hh/np.maximum(np.linalg.norm(hh,axis=1,keepdims=True),1e-12)
        rr,cc=linear_sum_assignment(-(ref@norm.T))
        for i,j in zip(rr,cc):
            other_set=set(names[hh[j].argsort()[-10:]])
            stability.append({'seed':seed,'topic':i,'cosine':float(ref[i]@norm[j]),
                'top10_jaccard':len(top_sets[i]&other_set)/len(top_sets[i]|other_set),
                'iterations':int(other.n_iter_)})
    csv(pd.DataFrame(stability),'topic_stability')
    examples=[]
    for i in range(k):
        # Inspect central documents without exposing outcome values in the naming sample.
        for j in np.argsort(weights[:,i])[-5:][::-1]:
            examples.append({'topic':i,'text':sub.iloc[j].clean_text,'weight':weights[j,i]})
    csv(pd.DataFrame(examples),'topic_examples')
    for i in range(k):sub[f'topic_{i}']=weights[:,i]
    columns=[f'topic_{i}' for i in range(k)]
    csv(sub[['postId','author']+columns],'post_topics')
    # Reference is chosen from text frequencies, without consulting outcomes.
    # Compare a 10-percentage-point weight shift relative to the largest topic.
    reference=int(np.bincount(dominant,minlength=k).argmax())
    compared=[i for i in range(k) if i!=reference]
    topic_rhs=base.formula().replace(' + has_text','')
    fit=smf.ols('log_likes ~ '+topic_rhs+''.join(f' + topic_{i}' for i in compared),data=sub).fit(
        cov_type='cluster',cov_kwds={'groups':sub.author,'use_correction':True,'df_correction':True},use_t=True)
    ci=fit.conf_int();out=[]
    for i in compared:
        term=f'topic_{i}';out.append({'topic':i,'reference_topic':reference,'coef':fit.params[term],
            'se_cluster':fit.bse[term],'p':fit.pvalues[term],'ci_low':ci.loc[term,0],'ci_high':ci.loc[term,1],
            'pct_likes_plus1_per_10pp':100*np.expm1(.1*fit.params[term])})
    out=pd.DataFrame(out);out['q_bh']=multipletests(out.p,method='fdr_bh')[1];csv(out,'topic_regression')
    joint=fit.wald_test(' = 0, '.join(f'topic_{i}' for i in compared)+' = 0',scalar=True)
    return {'documents':len(sub),'fitted_documents':fitted_document_count,
        'near_zero_contribution_documents':int((~assigned).sum()),'authors':sub.author.nunique(),'vocabulary':len(names),'topics':k,
        'iterations':int(model.n_iter_),'converged':bool(model.n_iter_<settings['max_iter']),
        'mean_top10_jaccard':float(pd.DataFrame(stability).top10_jaccard.mean()),
        'reference_topic':reference,'joint_topic_p':float(joint.pvalue),'regression_r2':float(fit.rsquared),
        'regression_rank':int(np.linalg.matrix_rank(fit.model.exog)),'regression_parameters':len(fit.params),
        'note':'主题回归和区间以本次拟合的主题特征为给定输入，未计入主题估计本身的不确定性。'}


def predictive_pipeline(kind):
    categorical=['author','gender','contentTypeStr','type','time_bin','weekday']
    numeric=['keepValue','kgLevel','memberStatus','date_index','has_tag']
    if kind in ['dictionary','char_text']:
        numeric+=base.FOCAL+['has_text','emoji_count','course_ref']
    transformers=[('categories',OneHotEncoder(handle_unknown='ignore'),categorical),
                  ('numeric',StandardScaler(with_mean=False),numeric)]
    if kind=='char_text':
        cfg=CFG['prediction']
        transformers.append(('characters',TfidfVectorizer(analyzer='char',ngram_range=tuple(cfg['char_ngram_range']),
            min_df=cfg['min_df'],max_features=cfg['max_features'],sublinear_tf=True),'clean_text'))
    return Pipeline([('features',ColumnTransformer(transformers)),('regression',Ridge(
        alpha=CFG['prediction']['ridge_alpha'],solver='lsqr',tol=1e-6,max_iter=10000))])


def predictions(posts):
    p=posts.copy();p['weekday']=p.local_time.dt.dayofweek.astype(str)
    p['date_index']=(p.local_time.dt.normalize()-p.local_time.dt.normalize().min()).dt.days
    cfg=CFG['prediction'];models=list(LABELS)
    temporal=p.date.ge(cfg['temporal_test_start']).to_numpy()
    splits={'时间留出':[(np.flatnonzero(~temporal),np.flatnonzero(temporal))],
        '作者分组五折':list(GroupKFold(n_splits=cfg['group_folds']).split(p,groups=p.author))}
    anon={u:f'A{i+1:03d}' for i,u in enumerate(sorted(p.author.unique()))}
    rows=[];folds=[]
    for split_name,split_list in splits.items():
        for fold,(train,test) in enumerate(split_list):
            a,b=p.iloc[train],p.iloc[test]
            if split_name=='作者分组五折':assert set(a.author).isdisjoint(b.author)
            if split_name=='时间留出':assert a.date.max()<b.date.min()
            old_text=set(a.loc[a.length.ge(cfg['novel_text_min_chars']),'clean_text'])
            novel=b.length.ge(cfg['novel_text_min_chars'])&~b.clean_text.isin(old_text)
            folds.append({'split':split_name,'fold':fold,'train_n':len(a),'test_n':len(b),
                'train_authors':a.author.nunique(),'test_authors':b.author.nunique(),
                'author_overlap':len(set(a.author)&set(b.author)),
                'train_date_min':a.date.min(),'train_date_max':a.date.max(),
                'test_date_min':b.date.min(),'test_date_max':b.date.max(),'novel_text_n':int(novel.sum())})
            predicted={}
            for name in models:
                if name=='mean':predicted[name]=np.repeat(a.log_likes.mean(),len(b));continue
                estimator=predictive_pipeline(name)
                estimator.fit(a,a.log_likes)
                predicted[name]=estimator.predict(b)
            for j,index in enumerate(test):
                record={'split':split_name,'fold':fold,'postId':p.iloc[index].postId,
                    'author':anon[p.iloc[index].author],'observed':p.iloc[index].log_likes,
                    'novel_text':bool(novel.iloc[j])}
                record.update({name:float(predicted[name][j]) for name in models});rows.append(record)
            print(f'Prediction: {split_name}, fold {fold+1}/{len(split_list)} completed',flush=True)
    predictions=pd.DataFrame(rows);csv(predictions,'predictions');csv(pd.DataFrame(folds),'prediction_folds')
    metric=[];intervals=[]
    rng=np.random.default_rng(SEED)
    for split_name,data in predictions.groupby('split',sort=False):
        for subset_name,subset in [('全部留出帖',data),('未见过的正文',data.loc[data.novel_text])]:
            for model in models:
                metric.append({'split':split_name,'subset':subset_name,'model':model,'label':LABELS[model],
                    'n':len(subset),'authors':subset.author.nunique(),
                    'mae':mean_absolute_error(subset.observed,subset[model]),
                    'rmse':np.sqrt(mean_squared_error(subset.observed,subset[model])),
                    'r2':r2_score(subset.observed,subset[model])})
        # Paired author-cluster bootstrap on fixed out-of-sample predictions.
        for enhanced,reference in [('dictionary','structured'),('char_text','dictionary'),('char_text','structured')]:
            difference=np.abs(data[enhanced]-data.observed)-np.abs(data[reference]-data.observed)
            grouped=pd.DataFrame({'author':data.author,'difference':difference}).groupby('author').agg(total=('difference','sum'),n=('difference','size'))
            take=rng.integers(0,len(grouped),size=(cfg['bootstrap_repetitions'],len(grouped)))
            boot=grouped.total.to_numpy()[take].sum(axis=1)/grouped.n.to_numpy()[take].sum(axis=1)
            intervals.append({'split':split_name,'enhanced':enhanced,'reference':reference,
                'delta_mae':float(difference.mean()),'ci_low':float(np.quantile(boot,.025)),
                'ci_high':float(np.quantile(boot,.975)),'authors':len(grouped),'repetitions':cfg['bootstrap_repetitions']})
    csv(pd.DataFrame(metric),'prediction_metrics');csv(pd.DataFrame(intervals),'prediction_differences')
    return {'temporal_train_n':int((~temporal).sum()),'temporal_test_n':int(temporal.sum()),
        'group_folds':cfg['group_folds'],'metrics_scale':'ln(1+点赞数)',
        'temporal_test_start':cfg['temporal_test_start'],'hyperparameters_selected_on_test':False,
        'interval_scope':'固定留出预测的作者聚类自助区间，不包含重新训练带来的变异。'}


def author_influence(posts):
    fit=smf.ols('log_likes ~ '+base.formula(),data=posts).fit()
    a=fit.model.exog;y=fit.model.endog;names=fit.model.exog_names
    indices=[names.index(t) for t in base.FOCAL]
    aa=a.T@a;ay=a.T@y
    original=pd.read_csv(RESULT/'regression_coefficients.csv').query("model == 'M3_作者与日期固定效应'").set_index('term')
    fitted=la.pinvh(aa,rtol=1e-12)@ay
    assert np.max(np.abs(fitted[indices]-fit.params.iloc[indices]))<1e-7
    rows=[]
    for j,author in enumerate(sorted(posts.author.unique())):
        keep=posts.author.ne(author).to_numpy();gone=a[~keep];gy=y[~keep]
        gram=aa-gone.T@gone;rhs=ay-gone.T@gy
        inverse=la.pinvh(gram,rtol=1e-12);beta=inverse@rhs
        projection=inverse@gram
        for term,col in zip(base.FOCAL,indices):
            estimable=np.max(np.abs(projection[col]-np.eye(len(names))[col]))<1e-5
            if not estimable:raise ValueError('Focal coefficient not estimable after deletion')
            rows.append({'excluded_author':f'A{j+1:03d}','excluded_posts':int((~keep).sum()),'term':term,
                'coefficient':float(beta[col]),'full_coefficient':original.loc[term,'coef'],
                'change_in_full_cluster_se':float((beta[col]-original.loc[term,'coef'])/original.loc[term,'se_cluster'])})
    out=pd.DataFrame(rows);csv(out,'author_influence')
    summary=out.groupby('term').agg(min_coefficient=('coefficient','min'),max_coefficient=('coefficient','max'),
        positive_runs=('coefficient',lambda x:int(x.gt(0).sum())),negative_runs=('coefficient',lambda x:int(x.lt(0).sum())),
        max_abs_change_in_se=('change_in_full_cluster_se',lambda x:float(x.abs().max()))).reset_index()
    csv(summary,'author_influence_summary')
    return {'deletions':posts.author.nunique(),'focal_terms':len(base.FOCAL),'max_coefficient_error_against_full_ols':float(np.max(np.abs(fitted[indices]-fit.params.iloc[indices])))}


def comment_extensions(posts,comments):
    c=comments.copy();post_index=posts.set_index('postId')
    c['post_author']=c.postId.map(post_index.author)
    c['lag_hours']=(c.local_time-c.postId.map(post_index.local_time)).dt.total_seconds()/3600
    assert c.lag_hours.ge(0).all()
    roots=c.replyUserId.isna()&c.reply.isna()&c.parentId.isna()
    c['target']=c.replyUserId.where(~roots,c.post_author)
    # All explicit replyUserIds are observed in this supplied table.
    assert c.target.notna().all()
    valid=c.author_id.ne(c.target)
    ev=c.loc[valid].copy();ev['is_root']=roots.loc[valid]
    ev['role']=np.select([ev.is_root,ev.author_id.eq(ev.post_author),ev.target.eq(ev.post_author)],
        ['根评论指向帖主','帖主回复其他用户','其他用户回复帖主'],default='其他用户彼此回复')
    role=ev.groupby('role').size().reset_index(name='events');role['share_all']=role.events/len(ev)
    csv(role,'comment_roles')
    lag=[]
    for hours in [1,6,24,72,168,720]:lag.append({'hours':hours,'comments':int(c.lag_hours.le(hours).sum()),'share':float(c.lag_hours.le(hours).mean())})
    csv(pd.DataFrame(lag),'comment_timing')
    networks=[]
    for name,data in [('全部已采集互动',ev),('发帖后7天内',ev.loc[ev.lag_hours.le(CFG['comments']['early_window_hours'])])]:
        edges=data.groupby(['author_id','target']).size().reset_index(name='weight')
        g=nx.from_pandas_edgelist(edges,'author_id','target',edge_attr='weight',create_using=nx.DiGraph())
        received=sorted(dict(g.in_degree(weight='weight')).values(),reverse=True)
        networks.append({'window':name,'events':len(data),'nodes':len(g),'edges':g.number_of_edges(),
            'reciprocity':nx.reciprocity(g),'top10_share':sum(received[:10])/len(data)})
    csv(pd.DataFrame(networks),'window_networks')
    incoming_roots=c.loc[roots & c.author_id.ne(c.post_author)].copy()
    participating=c.loc[c.author_id.eq(c.post_author)&c.parentId.isin(incoming_roots.cmtId)]
    earliest=participating.groupby('parentId').local_time.min()
    incoming_roots['author_reply_time']=incoming_roots.cmtId.map(earliest)
    replied=incoming_roots.author_reply_time.notna()
    delay=(incoming_roots.loc[replied,'author_reply_time']-incoming_roots.loc[replied,'local_time']).dt.total_seconds()/3600
    assert delay.ge(0).all()
    return {'collected_comments':len(c),'median_lag_hours':float(c.lag_hours.median()),
        'within_24_hours_share':float(c.lag_hours.le(24).mean()),'within_7_days_share':float(c.lag_hours.le(168).mean()),
        'reply_events':int((~ev.is_root).sum()),'reply_role_counts':{r.role:int(r.events) for r in role.itertuples()},
        'incoming_root_threads':len(incoming_roots),'threads_with_observed_author_reply':int(replied.sum()),
        'observed_author_reply_thread_share':float(replied.mean()),'conditional_author_reply_median_hours':float(delay.median()),
        'missing_direct_reply_comment_reference':int((c.reply.notna()&~c.reply.isin(c.cmtId)).sum()),
        'missing_parent_reference':int((c.parentId.notna()&~c.parentId.isin(c.cmtId)).sum()),
        'note':'比例以已采集记录为分母；未观测到帖主回应不等于实际未回应，时序也不是完整评论增长曲线。'}


def plot_extensions():
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.ticker import MaxNLocator
    import os
    font=os.environ.get('REPORT_FONT','/Library/Fonts/Arial Unicode.ttf')
    if Path(font).exists():font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,
        'text.color':'#243746','axes.labelcolor':'#243746','figure.facecolor':'white','savefig.facecolor':'white'})
    blue='#356D9A';gold='#B88425';gray='#657680'
    def save(fig,name):fig.savefig(FIG/name,dpi=190,bbox_inches='tight');plt.close(fig)
    d=pd.read_csv(RESULT/'extension_coverage_media.csv')
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.6))
    bars=ax[0].bar([base.MEDIA[x] for x in d.contentTypeStr],100*d.visible_share,color=blue)
    ax[0].bar_label(bars,labels=[f'{x:.1%}' for x in d.visible_share],padding=3);ax[0].set(ylim=(0,113),ylabel='有可用正文的帖子占比（%）',title='A. 正文覆盖随内容形式变化')
    a=pd.read_csv(RESULT/'extension_coverage_authors.csv');ax[1].scatter(a.posts,100*a.visible_share,color=blue,alpha=.7,s=24)
    ax[1].set(xlabel='作者发帖数',ylabel='该作者正文覆盖率（%）',title='B. 每位作者的正文覆盖情况');fig.tight_layout(w_pad=2);save(fig,'08_text_coverage.png')
    d=pd.read_csv(RESULT/'extension_topics.csv');labels=json.loads((ROOT/'code/topic_labels.json').read_text())['labels']
    fig,ax=plt.subplots(figsize=(10.3,3.8));order=d.sort_values('dominant_share')
    labs=[labels.get(str(r.topic),r.label)+'\n'+r.keywords.split('、')[0]+'、'+r.keywords.split('、')[1] for r in order.itertuples()]
    bars=ax.barh(labs,100*order.dominant_share,color=blue);ax.bar_label(bars,labels=[f'{x:.1%}' for x in order.dominant_share],padding=4)
    ax.set(xlabel='主导主题占比（%）；仅主题模型纳入的正文',xlim=(0,100),title='五个NMF主题的文档分布');fig.tight_layout();save(fig,'09_topics.png')
    metrics=pd.read_csv(RESULT/'extension_prediction_metrics.csv');d=metrics.loc[metrics.subset.eq('全部留出帖')]
    fig,axes=plt.subplots(1,2,figsize=(10.8,3.7))
    for ax,split in zip(axes,['时间留出','作者分组五折']):
        z=d.loc[d.split.eq(split)].set_index('model').loc[list(LABELS)].iloc[::-1]
        bars=ax.barh(z.label,z.mae,color=[blue,blue,gray,gold]);ax.bar_label(bars,fmt='%.3f',padding=4)
        ax.set(xlabel='MAE：ln(1+点赞数)，越低越好',title=split,xlim=(0,z.mae.max()*1.18))
    fig.tight_layout(w_pad=2);save(fig,'10_prediction_comparison.png')
    d=pd.read_csv(RESULT/'extension_prediction_differences.csv');fig,axes=plt.subplots(1,2,figsize=(10.8,3.5),sharey=True)
    titles=['词典 − 结构化','字符文本 − 词典','字符文本 − 结构化']
    for ax,split in zip(axes,['时间留出','作者分组五折']):
        z=d.loc[d.split.eq(split)];y=np.arange(len(z));ax.errorbar(z.delta_mae,y,xerr=[z.delta_mae-z.ci_low,z.ci_high-z.delta_mae],fmt='o',color=blue,capsize=4)
        ax.axvline(0,color=gray,ls='--',lw=1);ax.set_yticks(y,titles);ax.set(xlabel='ΔMAE与95%作者聚类自助区间',title=split);ax.grid(axis='x',alpha=.15)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
    fig.tight_layout(w_pad=2);save(fig,'11_prediction_uncertainty.png')
    d=pd.read_csv(RESULT/'extension_author_influence.csv');fig,ax=plt.subplots(figsize=(9.6,3.7))
    vals=[d.loc[d.term.eq(t),'coefficient'] for t in base.FOCAL[::-1]]
    ax.boxplot(vals,vert=False,tick_labels=[base.LABELS[t] for t in base.FOCAL[::-1]],widths=.5,
        medianprops={'color':gold},boxprops={'color':blue},whiskerprops={'color':blue},capprops={'color':blue},flierprops={'marker':'.','markeredgecolor':blue})
    ax.axvline(0,color=gray,ls='--',lw=1);ax.set(xlabel='逐次剔除一位作者后的系数',title='100次作者剔除检验：观察点估计对单一作者的敏感性');fig.tight_layout();save(fig,'12_author_influence.png')
    timing=pd.read_csv(RESULT/'extension_comment_timing.csv');roles=pd.read_csv(RESULT/'extension_comment_roles.csv');roles=roles.loc[roles.role.ne('根评论指向帖主')]
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.6))
    ax[0].plot(timing.hours,100*timing['share'],marker='o',color=blue);ax[0].set_xscale('log');ax[0].set_xticks([1,6,24,72,168,720],['1h','6h','24h','3d','7d','30d'])
    ax[0].set(xlabel='发帖后的时间间隔（对数刻度）',ylabel='已采集评论的累计占比（%）',ylim=(0,100),title='A. 评论发生时间（条件于采集记录）')
    bars=ax[1].barh(roles.role,roles.events,color=blue);ax[1].bar_label(bars,fmt='%d',padding=3);ax[1].set(xlabel='非自我明确回复事件数',title='B. 明确回复中的参与角色',xlim=(0,roles.events.max()*1.2));fig.tight_layout(w_pad=2);save(fig,'13_comment_timing_roles.png')


def main():
    start=time.monotonic();p,c,_=base.read_and_prepare()
    summary={'config_sha256':hashlib.sha256((ROOT/'code/extension_config.json').read_bytes()).hexdigest(),
        'as_of':'2026-10-17','sklearn_version':importlib.metadata.version('scikit-learn')}
    summary['coverage']=coverage(p);print('Coverage completed',flush=True)
    summary['topics']=topic_model(p);print('NMF and exploratory topic regression completed',flush=True)
    summary['prediction']=predictions(p)
    summary['influence']=author_influence(p);print('Author influence completed',flush=True)
    summary['comments']=comment_extensions(p,c);plot_extensions()
    summary['elapsed_seconds']=round(time.monotonic()-start,2)
    (RESULT/'extension_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=lambda x:int(x)))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
