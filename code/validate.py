"""Independent numerical checks of main OLS, clustered covariance and counts."""
from pathlib import Path
import json
import zipfile
import numpy as np
import pandas as pd
from scipy import stats

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=pd.read_csv(ROOT/"2026Data/Keep Data/sample_post_2022.csv")
    c=pd.read_csv(ROOT/"2026Data/Keep Data/sample_comment_2022.csv")
    f=pd.read_csv(ROOT/"results/post_features.csv")
    s=json.loads((ROOT/"results/summary.json").read_text())
    checks=[]
    def check(name,passed,detail=""):
        checks.append({"check":name,"passed":bool(passed),"detail":detail})
        if not passed:raise AssertionError(name+": "+str(detail))
    check("帖子行数、主键及特征行数一致",len(p)==len(f)==s["post_rows"] and p.postId.is_unique)
    check("重复评论均完全相同",c.duplicated().sum()==c.cmtId.duplicated().sum()==1916)
    c=c.drop_duplicates("cmtId")
    check("全部评论可关联帖子",c.postId.isin(p.postId).all())
    check("点赞基本统计独立复算",np.isclose(p.likes.mean(),s["likes_mean"]) and p.likes.median()==s["likes_median"])
    check("浏览数异常计数",(p.likes>p.viewCount).sum()==s["likes_exceed_views"])
    check("非覆盖帖评论数量保留缺失",s["posts_with_collected_comments"]==c.postId.nunique()==1323)
    focal=["log_length","self_discipline","social_address","positive_expression","question"]
    numeric=focal+["has_text","has_tag","emoji_count","course_ref"]
    cats=["contentTypeStr","type","time_bin","author","date"]
    # Deliberately avoid statsmodels and its covariance helpers here.
    x=pd.concat([pd.Series(1.,index=f.index,name="const"),f[numeric],pd.get_dummies(f[cats],drop_first=True,dtype=float)],axis=1)
    a=x.to_numpy(float);y=np.log1p(p.likes.to_numpy());n,k=a.shape;g=f.author.nunique()
    beta=np.linalg.lstsq(a,y,rcond=None)[0]
    bread=np.linalg.inv(a.T@a);resid=y-a@beta
    scores=pd.DataFrame(a*resid[:,None]).groupby(f.author).sum().to_numpy()
    cov=bread@(scores.T@scores)@bread * (g/(g-1))*((n-1)/(n-k))
    se=np.sqrt(np.maximum(np.diag(cov),0))
    coef=pd.read_csv(ROOT/"results/regression_coefficients.csv").query("model == 'M3_作者与日期固定效应'").set_index("term")
    errors=[]
    for name in focal:
        i=x.columns.get_loc(name);lo=beta[i]-stats.t.ppf(.975,g-1)*se[i];hi=beta[i]+stats.t.ppf(.975,g-1)*se[i]
        pv=2*stats.t.sf(abs(beta[i]/se[i]),g-1)
        err=max(abs(beta[i]-coef.loc[name,"coef"]),abs(se[i]-coef.loc[name,"se_cluster"]),abs(pv-coef.loc[name,"p"]),abs(lo-coef.loc[name,"ci_low"]),abs(hi-coef.loc[name,"ci_high"]))
        errors.append(err)
    check("独立矩阵算法复核5项系数、聚类标准误、p值及区间",max(errors)<1e-7,{"max_abs_error":max(errors),"clusters":g,"rank":np.linalg.matrix_rank(a)})
    e=pd.read_csv(ROOT/"results/network_edges.csv");nodes=pd.read_csv(ROOT/"results/network_nodes.csv");net=s["network"]
    check("网络事件与评论数核对",int(e.weight.sum())+net["self_loops_removed"]+net["unresolved"]+net["before_post_removed"]==len(c))
    check("网络方向不含自环",e.source.ne(e.target).all())
    check("节点入强度、出强度及边权总和一致",int(nodes.weighted_in_degree.sum())==int(nodes.weighted_out_degree.sum())==int(e.weight.sum()))
    pairs=set(zip(e.source,e.target));recip=sum((v,u) in pairs for u,v in pairs)/len(pairs)
    check("互惠率按有反向边的有向边占比独立复算",np.isclose(recip,net["reciprocity"]))
    check("主模型与PPML设计矩阵满秩",pd.read_csv(ROOT/"results/model_fit.csv").eval("parameters == rank").all())
    check("PPML已收敛",s["models"]["ppml_converged"])
    (ROOT/"validation/numerical_checks.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2,default=lambda x:int(x)))
    print(f"Passed {len(checks)} independent numerical checks.")

if __name__=="__main__":main()
