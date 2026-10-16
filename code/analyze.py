"""Reproducible Keep analysis. Run from any directory: python code/analyze.py.

Only writes inside projects/group. All inferential models are observational.
Dictionary rules are explicit, versioned and separate from model results.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import logging
import os
import re
import warnings
from collections import Counter

import numpy as np
import pandas as pd
import scipy.stats as st
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
import networkx as nx
import jieba
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results"
FIG = ROOT / "figures"
SEED = 20261016
DICTIONARY = json.loads((ROOT / "code/text_dictionary.json").read_text())
FOCAL = ["log_length", "self_discipline", "social_address", "positive_expression", "question"]
LABELS = {"log_length": "正文长度 ln(1+字数)", "self_discipline": "自律/目标词命中",
          "social_address": "社交称呼/互助词命中", "positive_expression": "积极表达词命中",
          "question": "问号出现", "has_text": "正文有可见字符", "has_tag": "包含话题标签",
          "emoji_count": "方括号表情数 ln(1+数)", "course_ref": "课程分享标记"}
MEDIA = {"img": "图片", "none": "无媒体", "video": "视频", "txt": "纯文字"}


def save_csv(frame, name):
    frame.to_csv(RESULT / name, index=False, encoding="utf-8-sig")


def clean_text(value):
    """Preserve meaningful punctuation; remove only observable auto suffixes."""
    s = "" if pd.isna(value) else str(value)
    s = s.replace("\\n", "\n").replace("\\r", " ")
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"Ⓚ[^Ⓚ]*Ⓚ", " ", s)
    s = re.sub(r"\[[^\[\]]{1,12}\]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def read_and_prepare():
    p = pd.read_csv(ROOT / "2026Data/Keep Data/sample_post_2022.csv")
    c = pd.read_csv(ROOT / "2026Data/Keep Data/sample_comment_2022.csv")
    original_comment_count = len(c)
    assert p.postId.is_unique and p.postId.notna().all()
    assert not (c.groupby("cmtId").nunique(dropna=False) > 1).any().any(), "Conflicting duplicate comment ID"
    c = c.drop_duplicates("cmtId").copy()
    assert c.postId.isin(p.postId).all()
    p["author"] = p.userId
    p["raw_text"] = p.content.fillna("").str.replace("\\n", "\n", regex=False)
    p["clean_text"] = p.content.map(clean_text)
    p["has_text"] = p.raw_text.str.strip().ne("").astype(int)
    p["length"] = p.clean_text.str.replace(r"\s", "", regex=True).str.len()
    p["log_length"] = np.log1p(p.length)
    p["emoji_count"] = np.log1p(p.raw_text.str.count(r"\[[^\[\]]{1,12}\]"))
    p["course_ref"] = p.raw_text.str.contains("Ⓚ", regex=False).astype(int)
    p["has_tag"] = p.hashTags.ne("[]").astype(int)
    for feature in FOCAL[1:]:
        terms = DICTIONARY[feature]
        pattern = "|".join(terms) if feature == "self_discipline" else "|".join(map(re.escape, terms))
        p[feature] = p.clean_text.str.contains(pattern, regex=True).astype(int)
        p[feature + "_hits"] = p.clean_text.map(lambda s: "|".join(re.findall(pattern, s)))
    p["local_time"] = pd.to_datetime(p.created, utc=True).dt.tz_convert("Asia/Shanghai")
    p["date"] = p.local_time.dt.strftime("%Y-%m-%d")
    p["month"] = p.local_time.dt.strftime("%Y-%m")
    p["hour"] = p.local_time.dt.hour
    p["time_bin"] = pd.cut(p.hour, [-1,5,11,17,23], labels=["00-05", "06-11", "12-17", "18-23"]).astype(str)
    p["log_likes"] = np.log1p(p.likes)
    # Missing comment coverage is never coded as an observed zero.
    counts = c.groupby("postId").size()
    p["observed_comment_count"] = p.postId.map(counts)
    c["local_time"] = pd.to_datetime(c.created, utc=True).dt.tz_convert("Asia/Shanghai")
    stats = {
        "post_rows": len(p), "authors": p.userId.nunique(), "comment_rows_raw": original_comment_count,
        "comment_rows_clean": len(c), "comment_duplicate_rows": original_comment_count - len(c),
        "comment_authors": c.author_id.nunique(), "posts_with_collected_comments": c.postId.nunique(),
        "missing_content": int(p.content.isna().sum()), "content_available": int(p.has_text.sum()),
        "likes_exceed_views": int((p.likes > p.viewCount).sum()),
        "post_time_utc_min": p.created.min(), "post_time_utc_max": p.created.max(),
        "post_time_local_min": str(p.local_time.min()), "post_time_local_max": str(p.local_time.max()),
        "comment_time_local_min": str(c.local_time.min()), "comment_time_local_max": str(c.local_time.max()),
        "likes_zero_share": float(p.likes.eq(0).mean()), "likes_mean": float(p.likes.mean()),
        "likes_median": float(p.likes.median()), "likes_max": int(p.likes.max()),
        "likes_variance_mean": float(p.likes.var()/p.likes.mean()),
        "top_author_post_count": int(p.groupby("author").size().max()),
        "comment_unmatched_posts": 0,
        "source_scope": "课程提供的100位作者样本，抽样机制不明；无抽样框与统一采集时点；非2022年或2026年样本"
    }
    return p, c, stats


def describe(p):
    nums = ["likes", "viewCount", "favoriteCount", "externalShareCount", "length"]
    d = p[nums].describe(percentiles=[.25,.5,.75,.95,.99]).T.reset_index(names="variable")
    save_csv(d, "descriptive_statistics.csv")
    for col, name in [("contentTypeStr", "media_summary.csv"), ("type", "post_type_summary.csv"), ("month", "monthly_summary.csv")]:
        tab = p.groupby(col).agg(n=("postId", "size"), authors=("author", "nunique"), mean_likes=("likes", "mean"),
                                 median_likes=("likes", "median"), text_available=("has_text", "mean")).reset_index()
        tab["share"] = tab.n / len(p)
        save_csv(tab, name)
    feature_rows=[]
    for f in FOCAL[1:]:
        feature_rows.append({"feature": f, "label": LABELS[f], "n_hit": int(p[f].sum()),
            "share_all": p[f].mean(), "share_visible": p.loc[p.has_text.eq(1),f].mean(),
            "authors_hit": p.loc[p[f].eq(1),"author"].nunique(),
            "authors_with_within_variation": int(p.groupby("author")[f].nunique().gt(1).sum()),
            "raw_mean_likes_hit": p.loc[p[f].eq(1),"likes"].mean(),
            "raw_mean_likes_nohit": p.loc[p[f].eq(0),"likes"].mean()})
    save_csv(pd.DataFrame(feature_rows), "text_features_summary.csv")
    stopfile = ROOT / "2026Data/weibo_stock_202312_202404/StopWords/BaiduStopwords.txt"
    if not stopfile.exists(): stopfile = ROOT / "code/stopwords.txt"
    stop = set(stopfile.read_text(encoding="utf-8-sig").split()) if stopfile.exists() else set()
    stop |= set("今天 每天 一个 自己 这个 那个 真的 还是 就是 什么 没有 可以 一下 已经 感觉 一天 还有 这样 不要 现在 时候 怎么 然后 因为 所以 但是 不是 只是 这些 那些 keep Keep".split())
    jieba.setLogLevel(logging.ERROR)
    jieba.dt.tmp_dir = str(RESULT)
    df=Counter()
    for text in p.clean_text:
        terms = {w for w in jieba.lcut(text) if len(w)>=2 and re.fullmatch(r"[\u4e00-\u9fff]+", w) and w not in stop}
        df.update(terms)
    save_csv(pd.DataFrame(df.most_common(60), columns=["term", "document_frequency"]), "word_document_frequency.csv")
    # Outcome-free review sample: 5 hit and 5 non-hit visible bodies per binary feature.
    rows=[]
    for i,f in enumerate(FOCAL[1:]):
        for hit in [1,0]:
            subset=p.loc[(p[f]==hit)&(p.has_text==1)]
            for _,r in subset.sample(min(5,len(subset)),random_state=SEED+i*2+hit).iterrows():
                rows.append({"feature":f,"predicted":hit,"postId":r.postId,"text":r.clean_text,
                             "matched":r[f+"_hits"],"reviewed_semantic": "", "review_note":""})
    review_path=RESULT / "text_coding_review.csv"
    if not review_path.exists(): save_csv(pd.DataFrame(rows),"text_coding_review.csv")


def formula(author_fe=True, date_fe=True, controls=True):
    rhs = " + ".join(FOCAL + ["has_text", "has_tag", "emoji_count", "course_ref"])
    if controls: rhs += " + C(contentTypeStr) + C(type) + C(time_bin)"
    if author_fe: rhs += " + C(author)"
    else: rhs += " + C(gender) + keepValue + kgLevel + memberStatus"
    if date_fe: rhs += " + C(date)"
    return rhs


def models(p, stats):
    fit_rows=[]; coeff=[]; fitted={}
    specs=[("M1_基础关联",p,False,False), ("M2_作者固定效应",p,True,False),
           ("M3_作者与日期固定效应",p,True,True),
           ("R1_仅可见正文",p.loc[p.has_text.eq(1)].copy(),True,True),
           ("R2_去除最高1%点赞",p.loc[p.likes<=p.likes.quantile(.99)].copy(),True,True)]
    # Each author has equal total weight, a check against prolific authors dominating the sample.
    specs.append(("R3_作者等权",p,True,True))
    for name,data,afe,dfe in specs:
        rhs=formula(afe,dfe)
        if name=="R1_仅可见正文": rhs=rhs.replace(" + has_text", "")
        obj = smf.wls("log_likes ~ "+rhs, data=data, weights=1/data.groupby("author").author.transform("size")) if name=="R3_作者等权" else smf.ols("log_likes ~ "+rhs,data=data)
        fit=obj.fit(cov_type="cluster",cov_kwds={"groups":data.author,"use_correction":True,"df_correction":True},use_t=True)
        fitted[name]=fit
        fit_rows.append({"model":name,"n":int(fit.nobs),"authors":data.author.nunique(),"parameters":len(fit.params),
            "rank":int(np.linalg.matrix_rank(fit.model.exog)),"r_squared":fit.rsquared,"adj_r_squared":fit.rsquared_adj,
            "author_fe":afe,"date_fe":dfe,"residual_df":fit.df_resid,"cluster_inference_df":data.author.nunique()-1})
        ci=fit.conf_int()
        for term in FOCAL+["has_text","has_tag","emoji_count","course_ref"]:
            if term not in fit.params:continue
            coeff.append({"model":name,"term":term,"label":LABELS[term],"coef":fit.params[term],"se_cluster":fit.bse[term],
                "t":fit.tvalues[term],"p":fit.pvalues[term],"ci_low":ci.loc[term,0],"ci_high":ci.loc[term,1],
                "pct_on_likes_plus1":100*np.expm1(fit.params[term]),"pct_ci_low":100*np.expm1(ci.loc[term,0]),
                "pct_ci_high":100*np.expm1(ci.loc[term,1])})
    main=fitted["M3_作者与日期固定效应"]
    # Model check: Poisson quasi-maximum likelihood on the count outcome;
    # clustered sandwich inference does not assume conditional Poisson variance.
    fit=smf.glm("likes ~ "+formula(), data=p,family=sm.families.Poisson()).fit(
        maxiter=200,cov_type="cluster",cov_kwds={"groups":p.author,"use_correction":True},use_t=True)
    name="R4_PPML计数模型";ci=fit.conf_int()
    for term in FOCAL:
        coeff.append({"model":name,"term":term,"label":LABELS[term],"coef":fit.params[term],"se_cluster":fit.bse[term],
            "t":fit.tvalues[term],"p":fit.pvalues[term],"ci_low":ci.loc[term,0],"ci_high":ci.loc[term,1],
            "pct_on_likes_plus1":100*np.expm1(fit.params[term]),"pct_ci_low":100*np.expm1(ci.loc[term,0]),
            "pct_ci_high":100*np.expm1(ci.loc[term,1])})
    fit_rows.append({"model":name,"n":int(fit.nobs),"authors":p.author.nunique(),"parameters":len(fit.params),
        "rank":int(np.linalg.matrix_rank(fit.model.exog)),"r_squared":None,"adj_r_squared":None,
        "author_fe":True,"date_fe":True,"residual_df":fit.df_resid,"cluster_inference_df":p.author.nunique()-1,
        "converged":bool(fit.converged)})
    coef=pd.DataFrame(coeff)
    coef["q_bh_focal"]=np.nan
    sel=(coef.model=="M3_作者与日期固定效应")&coef.term.isin(FOCAL)
    coef.loc[sel,"q_bh_focal"]=multipletests(coef.loc[sel,"p"],method="fdr_bh")[1]
    save_csv(coef,"regression_coefficients.csv");save_csv(pd.DataFrame(fit_rows),"model_fit.csv")
    # Residual-fit diagnostics and a joint Wald test restricted to the five focal terms.
    rhs0="has_text + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type) + C(time_bin) + C(author) + C(date)"
    control=smf.ols("log_likes ~ "+rhs0,data=p).fit()
    test=main.wald_test(" = 0, ".join(FOCAL)+" = 0",scalar=True)
    stats["models"]={"incremental_r2_text":float(main.rsquared-control.rsquared),"joint_focal_F":float(test.statistic),
                     "joint_focal_p":float(test.pvalue),"trim_threshold_likes_p99":float(p.likes.quantile(.99)),
                     "ppml_converged":bool(fit.converged), "main_clusters":int(p.author.nunique())}
    resid=pd.DataFrame({"fitted_log_likes":main.fittedvalues,"residual_log_likes":main.resid})
    save_csv(resid,"model_diagnostics.csv")
    # Correlation and condition of the author-demeaned focal features.
    centered=p[FOCAL]-p.groupby("author")[FOCAL].transform("mean")
    save_csv(centered.corr().reset_index(names="term"),"within_author_feature_correlations.csv")
    return coef


def network(p,c,stats):
    # Root comments address the post author. Replies address explicit replyUserId.
    # Resolve an absent replyUserId only from an actually observed referenced comment.
    post_author=p.set_index("postId").userId.to_dict()
    comment_author=c.set_index("cmtId").author_id.to_dict()
    events=[];unresolved=0;invalid=0;self_loops=0;before_post=0
    post_time=p.set_index("postId").local_time.to_dict()
    for r in c.itertuples():
        if r.local_time < post_time[r.postId]: before_post += 1; continue
        if pd.notna(r.replyUserId): target=str(r.replyUserId);kind="explicit_reply"
        elif pd.notna(r.reply):
            target=comment_author.get(r.reply);kind="resolved_reply"
        elif pd.isna(r.parentId):target=post_author[r.postId];kind="root_to_post_author"
        else:target=None;kind="unresolved"
        if not target: unresolved+=1;continue
        if str(r.author_id)==str(target): self_loops+=1;continue
        events.append({"source":r.author_id,"target":target,"kind":kind,"cmtId":r.cmtId,"postId":r.postId})
    ev=pd.DataFrame(events)
    edges=ev.groupby(["source","target"]).size().reset_index(name="weight")
    g=nx.from_pandas_edgelist(edges,"source","target",edge_attr="weight",create_using=nx.DiGraph())
    pagerank=nx.pagerank(g,weight="weight")
    weak=sorted(nx.weakly_connected_components(g),key=len,reverse=True)
    degree=dict(g.in_degree(weight="weight"))
    sample_authors=set(p.author)
    order=sorted(g.nodes)
    pseudonyms={n:f"U{i+1:04d}" for i,n in enumerate(order)}
    nodes=pd.DataFrame([{"user":pseudonyms[n],"sample_post_author":n in sample_authors,
        "in_degree":g.in_degree(n),"out_degree":g.out_degree(n),
        "weighted_in_degree":g.in_degree(n,weight="weight"),"weighted_out_degree":g.out_degree(n,weight="weight"),
        "pagerank":pagerank[n]} for n in order]).sort_values("weighted_in_degree",ascending=False)
    save_csv(nodes,"network_nodes.csv")
    out_edges=edges.replace({"source":pseudonyms,"target":pseudonyms})
    save_csv(out_edges,"network_edges.csv")
    pair_recip=nx.reciprocity(g)
    root_ev=int(ev.kind.eq("root_to_post_author").sum())
    replies=ev.loc[ev.kind.ne("root_to_post_author")]
    rg=nx.from_pandas_edgelist(replies,"source","target",create_using=nx.DiGraph())
    stats["network"]={"nodes":g.number_of_nodes(),"edges":g.number_of_edges(),"events":len(ev),
        "self_loops_removed":self_loops,"unresolved":unresolved,"before_post_removed":before_post,
        "density":nx.density(g),"reciprocity":pair_recip,"weak_components":len(weak),
        "largest_weak_component":len(weak[0]),"largest_weak_component_share":len(weak[0])/len(g),
        "root_comment_events":root_ev,"reply_events":len(replies),
        "reply_only_nodes":len(rg),"reply_only_edges":rg.number_of_edges(),
        "reply_only_reciprocity":nx.reciprocity(rg),
        "top10_received_share":nodes.weighted_in_degree.head(10).sum()/len(ev),
        "top1_received_share":nodes.weighted_in_degree.iloc[0]/len(ev),
        "to_sample_author_share":ev.target.isin(sample_authors).mean(),
        "sample_author_nodes":int(nodes.sample_post_author.sum()),
        "comment_actor_union":int(len(set(c.author_id)|set(p.author)))}
    return g,nodes,pseudonyms


def plot_all(p,coef,g,nodes,pseudonyms):
    font=os.environ.get("REPORT_FONT", "/Library/Fonts/Arial Unicode.ttf")
    if Path(font).exists():font_manager.fontManager.addfont(font);plt.rcParams["font.family"]=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({"font.size":11,"axes.spines.top":False,"axes.spines.right":False,
        "axes.labelcolor":"#263645","text.color":"#263645","axes.edgecolor":"#98A6AE",
        "xtick.color":"#52636C","ytick.color":"#52636C","axes.unicode_minus":False,
        "savefig.facecolor":"white","figure.facecolor":"white"})
    blue="#356D9A";gold="#B88425";gray="#657680"
    def save(fig,name):
        fig.savefig(FIG/(name+".png"),dpi=190,bbox_inches="tight");plt.close(fig)
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.6))
    ax[0].hist(np.log1p(p.likes),bins=25,color=blue,edgecolor="white")
    ax[0].set(xlabel="ln(1+点赞数)",ylabel="帖子数",title="A. 点赞分布：零值与长尾并存")
    daily=p.groupby("date").size(); dates=pd.to_datetime(daily.index)
    ax[1].plot(dates,daily.values,color=blue,lw=1.7);ax[1].set(xlabel="北京时间日期",ylabel="帖子数",title="B. 逐日发帖数")
    idx=[0,15,30,45,len(dates)-1];ax[1].set_xticks(dates[idx]);ax[1].set_xticklabels(dates[idx].strftime("%m-%d"));ax[1].grid(axis="y",alpha=.18)
    fig.tight_layout(w_pad=2);save(fig,"01_sample_and_likes")
    media=p.groupby("contentTypeStr").likes.agg(["size","mean","median"]).sort_values("size",ascending=False)
    fig,ax=plt.subplots(1,2,figsize=(10.5,3.5))
    labs=[MEDIA.get(x,x) for x in media.index]
    bars=ax[0].bar(labs,media["size"],color=blue);ax[0].bar_label(bars,fmt="%.0f",padding=3);ax[0].set(ylabel="帖子数",title="A. 内容形式")
    x=np.arange(len(media));ax[1].bar(x-.18,media["mean"],.36,color=blue,label="均值");ax[1].bar(x+.18,media["median"],.36,color=gold,label="中位数")
    ax[1].set_xticks(x,labs);ax[1].set(ylabel="点赞数",title="B. 不同形式的点赞描述统计");ax[1].legend(frameon=False)
    fig.tight_layout(w_pad=2);save(fig,"02_media_summary")
    counts=pd.DataFrame({"feature":FOCAL[1:],"count":[p[x].sum() for x in FOCAL[1:]]}).sort_values("count")
    words=pd.read_csv(RESULT/"word_document_frequency.csv").head(10).iloc[::-1]
    fig,ax=plt.subplots(1,2,figsize=(10.8,3.8))
    ax[0].barh([LABELS[x] for x in counts.feature],counts["count"],color=blue)
    for i,n in enumerate(counts["count"]):ax[0].text(n+18,i,f"{n:,} ({n/len(p):.1%})",va="center",fontsize=9)
    ax[0].set_xlim(0,counts["count"].max()*1.55);ax[0].set(xlabel="命中帖子数；分母=全部9,532帖",title="A. 文本特征出现规模（可重叠）")
    ax[1].barh(words.term,words.document_frequency,color=gray);ax[1].set(xlabel="包含该词的正文数（每帖至多计1次）",title="B. 分词后的高频词")
    fig.tight_layout(w_pad=2.5);save(fig,"03_text_features")
    main=coef.loc[(coef.model=="M3_作者与日期固定效应")&coef.term.isin(FOCAL)].set_index("term").loc[FOCAL].iloc[::-1]
    fig,ax=plt.subplots(figsize=(9.2,3.7));x=main.coef;y=np.arange(len(main))
    ax.errorbar(x,y,xerr=[x-main.ci_low,main.ci_high-x],fmt="o",color=blue,ecolor=blue,capsize=4,ms=6)
    ax.axvline(0,color=gray,lw=1,ls="--");ax.set_yticks(y,main.label);ax.set(xlabel="对 ln(1+点赞数) 的系数与95%置信区间",title="主模型：控制作者、日期、内容形式与其他文本特征")
    ax.grid(axis="x",alpha=.15);fig.tight_layout();save(fig,"04_main_coefficients")
    model_names=["M3_作者与日期固定效应","R1_仅可见正文","R2_去除最高1%点赞","R3_作者等权","R4_PPML计数模型"]
    short=["主模型","仅可见正文","去除最高1%","作者等权","PPML计数"]
    fig,axes=plt.subplots(1,3,figsize=(11.4,3.6),sharey=True)
    for ax,f in zip(axes,FOCAL[1:4]):
        s=coef.loc[coef.term.eq(f)].set_index("model").loc[model_names].iloc[::-1]
        y=np.arange(len(s)); ax.errorbar(s.coef,y,xerr=[s.coef-s.ci_low,s.ci_high-s.coef],fmt="o",capsize=3,color=blue,ms=5)
        ax.axvline(0,color=gray,lw=1,ls="--");ax.set_yticks(y,short[::-1]);ax.set_title(LABELS[f],fontsize=11);ax.set_xlabel("系数（各模型尺度见正文）");ax.grid(axis="x",alpha=.15)
    fig.tight_layout();save(fig,"05_robustness")
    # Whole observed network. Position/size are visual aids, not statistical evidence.
    fig,ax=plt.subplots(figsize=(10.4,5.4))
    pos=nx.spring_layout(g,seed=SEED,iterations=55,weight="weight",k=.09)
    sample=pseudonyms
    sample_auth=set(p.author)
    colors=[gold if n in sample_auth else blue for n in g]
    size=[9+32*np.log1p(g.in_degree(n,weight="weight")) for n in g]
    nx.draw_networkx_edges(g,pos,ax=ax,arrows=False,alpha=.08,width=.4,edge_color=gray)
    nx.draw_networkx_nodes(g,pos,ax=ax,node_size=size,node_color=colors,alpha=.72,linewidths=0)
    top=sorted(g.in_degree(weight="weight"),key=lambda x:x[1],reverse=True)[:5]
    nx.draw_networkx_labels(g,pos,{n:pseudonyms[n] for n,_ in top},font_size=9,font_color="#172A39",ax=ax)
    ax.scatter([],[],s=30,c=gold,label="样本帖子作者");ax.scatter([],[],s=30,c=blue,label="其他参与者")
    ax.legend(loc="upper right",frameon=False);ax.set_title("去重评论构成的有向互动网络（箭头省略以便阅读）",fontsize=12);ax.axis("off")
    save(fig,"06_comment_network")
    fig,ax=plt.subplots(1,2,figsize=(10.5,3.6))
    top=nodes.head(10).iloc[::-1]
    ax[0].barh(top.user,top.weighted_in_degree,color=blue);ax[0].set(xlabel="收到的评论/回复事件数",title="A. 互动接收量前10位（匿名编号）")
    share=np.sort(nodes.weighted_in_degree.to_numpy());curve=np.r_[0,np.cumsum(share)/share.sum()]
    pop=np.linspace(0,1,len(curve));ax[1].plot(pop,curve,color=blue,lw=2,label="观察到的互动");ax[1].plot([0,1],[0,1],color=gray,lw=1,ls="--",label="均等参考线")
    ax[1].set(xlabel="按接收量从低到高排列的节点累计占比",ylabel="累计接收事件占比",title="B. 互动接收的集中程度",xlim=(0,1),ylim=(0,1));ax[1].legend(frameon=False)
    fig.tight_layout(w_pad=2);save(fig,"07_network_concentration")


def main():
    RESULT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
    p,c,stats=read_and_prepare()
    describe(p)
    print("Prepared data and descriptive tables",flush=True)
    coef=models(p,stats)
    print("Fitted OLS and PPML sensitivity models",flush=True)
    g,nodes,pseudonyms=network(p,c,stats)
    plot_all(p,coef,g,nodes,pseudonyms)
    # Export model-ready rows with deterministic anonymous authors, without the full raw text.
    anonym={u:f"A{i+1:03d}" for i,u in enumerate(sorted(p.author.unique()))}
    features=p[["postId","author","date","month","time_bin","likes","log_likes","contentTypeStr","type"]+FOCAL+["has_text","has_tag","emoji_count","course_ref","length"]].copy()
    features["author"]=features.author.map(anonym)
    save_csv(features,"post_features.csv")
    sources=[ROOT/"2026Data/Keep Data/sample_post_2022.csv",ROOT/"2026Data/Keep Data/sample_comment_2022.csv",ROOT/"code/text_dictionary.json",ROOT/"code/stopwords.txt"]
    stats["provenance"]=[{"file":str(f.relative_to(ROOT)),"sha256":hashlib.sha256(f.read_bytes()).hexdigest(),"bytes":f.stat().st_size} for f in sources]
    stats["versions"]={lib:importlib.metadata.version(lib) for lib in ["pandas","numpy","scipy","statsmodels","networkx","jieba","matplotlib"]}
    (RESULT/"summary.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,"item") else str(x)))
    print(json.dumps(stats,ensure_ascii=False,indent=2,default=str))


if __name__=="__main__":main()
