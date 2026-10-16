"""Independently verify extension counts, held-out metrics, intervals and deletion fits."""
from collections import Counter
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests
import analyze
import extend_analysis as ext

ROOT=analyze.ROOT


def main():
    s=json.loads((ROOT/'results/extension_summary.json').read_text());p,c,_=analyze.read_and_prepare()
    load=lambda name:pd.read_csv(ROOT/'results'/f'extension_{name}.csv')
    checks=[]
    def check(name,passed,detail=None):
        checks.append({'check':name,'passed':bool(passed),'detail':detail})
        if not passed:raise AssertionError(name+': '+str(detail))
    check('扩展配置哈希对应本次分析',s['config_sha256']==hashlib.sha256((ROOT/'code/extension_config.json').read_bytes()).hexdigest())
    coverage=load('coverage_media').set_index('contentTypeStr')
    expected=p.groupby('contentTypeStr').has_text.agg(['size','sum'])
    check('按媒体正文覆盖计数核对',np.array_equal(coverage.posts,expected['size']) and np.array_equal(coverage.visible,expected['sum']))
    weights=load('post_topics');cols=[f'topic_{i}' for i in range(5)]
    check('主题权重非负且逐帖归一',weights[cols].ge(-1e-10).all().all() and np.allclose(weights[cols].sum(axis=1),1))
    topic=load('topics');dominant=weights[cols].to_numpy().argmax(axis=1)
    check('主导主题数与占比核对',np.array_equal(np.bincount(dominant,minlength=5),topic.dominant_documents) and np.isclose(topic.dominant_share.sum(),1))
    check('主题回归设计矩阵满秩',s['topics']['regression_rank']==s['topics']['regression_parameters'])
    reg=load('topic_regression')
    check('探索性主题回归BH校正复算',np.allclose(reg.q_bh,multipletests(reg.p,method='fdr_bh')[1]))
    pred=load('predictions');folds=load('prediction_folds')
    check('作者分组训练测试无重叠',folds.loc[folds.split.eq('作者分组五折'),'author_overlap'].eq(0).all())
    check('作者分组每帖恰好一次留出',pred.loc[pred.split.eq('作者分组五折'),'postId'].is_unique and len(pred.loc[pred.split.eq('作者分组五折')])==len(p))
    temporal=folds.loc[folds.split.eq('时间留出')].iloc[0]
    check('时间留出日期严格分离',temporal.train_date_max<temporal.test_date_min and temporal.test_date_min==ext.CFG['prediction']['temporal_test_start'])
    metrics=load('prediction_metrics');max_error=0.
    for r in metrics.itertuples():
        data=pred.loc[pred.split.eq(r.split)]
        if r.subset=='未见过的正文':data=data.loc[data.novel_text]
        residual=data[r.model]-data.observed
        actual=[float(np.abs(residual).mean()),float(np.sqrt((residual**2).mean())),float(1-(residual**2).sum()/((data.observed-data.observed.mean())**2).sum())]
        max_error=max(max_error,float(np.max(np.abs(np.array(actual)-[r.mae,r.rmse,r.r2]))))
    check('全部16组留出MAE、RMSE、R²独立复算',max_error<1e-10,{'max_error':max_error})
    # Recalculate percentile intervals with multinomial author multiplicities.
    differences=load('prediction_differences');rng=np.random.default_rng(ext.SEED);errors=[]
    for split,data in pred.groupby('split',sort=False):
        for enhanced,reference in [('dictionary','structured'),('char_text','dictionary'),('char_text','structured')]:
            delta=np.abs(data[enhanced]-data.observed)-np.abs(data[reference]-data.observed)
            codes,authors=pd.factorize(data.author,sort=True);g=len(authors)
            totals=np.bincount(codes,weights=delta);sizes=np.bincount(codes)
            draws=rng.integers(0,g,size=(ext.CFG['prediction']['bootstrap_repetitions'],g))
            estimates=[]
            for take in draws:
                count=np.bincount(take,minlength=g)
                estimates.append(float(count@totals/(count@sizes)))
            r=differences.loc[differences.split.eq(split)&differences.enhanced.eq(enhanced)&differences.reference.eq(reference)].iloc[0]
            errors.append(max(abs(delta.mean()-r.delta_mae),abs(np.quantile(estimates,.025)-r.ci_low),abs(np.quantile(estimates,.975)-r.ci_high)))
    check('配对作者聚类自助区间用重复次数法复算',max(errors)<1e-10,{'max_error':max(errors)})
    influence=load('author_influence');fit=smf.ols('log_likes ~ '+analyze.formula(),data=p).fit()
    x=fit.model.exog;y=fit.model.endog;columns=fit.model.exog_names
    authors=sorted(p.author.unique());probe=[0,int(np.argmax(p.groupby('author').size().reindex(authors).to_numpy())),len(authors)-1]
    errors=[]
    for j in set(probe):
        keep=p.author.ne(authors[j]).to_numpy();beta=np.linalg.lstsq(x[keep],y[keep],rcond=None)[0]
        part=influence.loc[influence.excluded_author.eq(f'A{j+1:03d}')].set_index('term')
        for t in analyze.FOCAL:errors.append(abs(beta[columns.index(t)]-part.loc[t,'coefficient']))
    check('作者剔除的三例与直接最小二乘一致',max(errors)<1e-7,{'max_error':max(errors)})
    # Verify the actual character feature pipeline's IDF against training-document counts.
    train=p.loc[p.date.lt(ext.CFG['prediction']['temporal_test_start'])].copy()
    train['weekday']=train.local_time.dt.dayofweek.astype(str)
    train['date_index']=(train.local_time.dt.normalize()-p.local_time.dt.normalize().min()).dt.days
    pipeline=ext.predictive_pipeline('char_text').fit(train,train.log_likes)
    vectorizer=pipeline.named_steps['features'].named_transformers_['characters']
    df=Counter();analyzer=vectorizer.build_analyzer()
    for text in train.clean_text:df.update(set(analyzer(text)))
    vocabulary=vectorizer.get_feature_names_out()
    expected=np.array([np.log((1+len(train))/(1+df[word]))+1 for word in vocabulary])
    check('预测TF-IDF的IDF仅对应训练正文计数',np.allclose(vectorizer.idf_,expected) and all(df[w]>=3 for w in vocabulary),{'training_documents':len(train),'vocabulary':len(vocabulary)})
    roles=load('comment_roles');check('回复角色加总对应原网络事件',int(roles.events.sum())==11511 and int(roles.loc[roles.role.ne('根评论指向帖主'),'events'].sum())==4902)
    time=c.local_time-c.postId.map(p.set_index('postId').local_time)
    actual=(time.dt.total_seconds()/3600).le(168).sum()
    check('7天评论占比以全部去重评论复算',np.isclose(actual/len(c),s['comments']['within_7_days_share']))
    windows=load('window_networks').set_index('window')
    check('全部窗口网络与原结果一致',int(windows.loc['全部已采集互动','events'])==11511 and np.isclose(windows.loc['全部已采集互动','reciprocity'],json.loads((ROOT/'results/summary.json').read_text())['network']['reciprocity']))
    (ROOT/'validation/extension_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
    print(f'Passed {len(checks)} extension checks.')


if __name__=='__main__':main()
