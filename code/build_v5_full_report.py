#!/usr/bin/env python3
"""Build the editable full-v5 empirical report from auditable aggregates."""
from pathlib import Path
import importlib.util, json, os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/keep-v5-full-report-mpl')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parents[1]
STEM='分析报告_正文多维测量全量版_v5_可编辑'
NAMES={'S_PRESENT':'记录与展示','S_EXPERIENCE':'自身体验','S_APPRAISAL':'对象评价','S_FUTURE':'未来安排与目标',
 'S_EXHORT':'鼓励与提醒','S_REFLECTION':'观点与感悟','S_GUIDANCE':'解释与方法建议','S_SOCIAL':'问候祝愿与致谢',
 'S_REQUEST':'征询与邀请','S_OFFER':'供给告知','T_ACTIVITY':'运动训练','T_BODY':'身体健康',
 'T_FOOD':'饮食营养','T_LIFE':'具体生活','T_TOOLS':'工具服务'}
POL={'positive_only':'仅显性正向','negative_only':'仅显性负向','mixed':'正负并存','neither':'均无显性方向'}
def js(name):return json.loads((ROOT/'results'/name).read_text())
def pc(n,d):return f'{n/d:.1%}' if d else '—'
def num(x):return f'{x:,}'
def f(x):return '—' if x is None else f'{x:.3f}'
def pv(x):return '—' if x is None else '<0.001' if x<.001 else f'{x:.3f}'
def pa(x):return '无可比阳性' if x is None else f'{x:.1%}'
def interval(x):return f"[{x['ci_low']:.3f}, {x['ci_high']:.3f}]"
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
      ['| '+' | '.join(map(str,r))+' |' for r in rows])
def qualified(coef):return [NAMES.get(k,k) for k,v in coef.items() if v['q_bh_within_family']<.05]

def figures(s,a,c):
    font=next((p for p in ['/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'] if Path(p).exists()),None)
    if font:plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams.update({'font.size':11,'axes.unicode_minus':False,'savefig.dpi':180})
    n=s['n_nonempty_posts'];hist=c['historical_same_post_population'];e=s['post_coverage']['axes']['expression']
    vals=[hist[k]['old_positive'] for k in ['legacy_four_lexical','v2_named_expression','v3_nine_expression']]+[e['any_positive'],a['main']['n']]
    labels=['原四项词典：至少一项阳性','历史v2十项：具名表达阳性','历史v3九项：至少一项阳性','本轮v5十项：具名表达阳性','本轮v5主回归：实际纳入']
    fig,ax=plt.subplots(figsize=(11,4.4),layout='constrained')
    bars=ax.barh(labels,vals,color=['#91a1ac','#91a1ac','#c09472','#417d8a','#326b55'],height=.56)
    ax.invert_yaxis();ax.set_xlim(0,n*1.22);ax.set_xticks([0,1000,2000,3000,4000,5000]);ax.set_xlabel('原帖数量；共同参照范围为5,414条非空正文')
    for bar,v in zip(bars,vals):ax.text(v+45,bar.get_y()+bar.get_height()/2,f'{v:,} · {pc(v,n)}',va='center',fontsize=10)
    ax.set_title('表达覆盖与回归纳入：分别回答两个问题',fontweight='bold',pad=12)
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.savefig(ROOT/'figures/v5_full_coverage.png',bbox_inches='tight');plt.close(fig)
    codes=[c for c in NAMES if c.startswith('S_')];counts=[a['variables'][c]['n_positive'] for c in codes]
    fig,ax=plt.subplots(figsize=(10.5,5),layout='constrained')
    bars=ax.barh([NAMES[c] for c in codes],counts,color=['#417d8a' if c in a['main']['codes'] else '#a4afb8' for c in codes],height=.61)
    ax.invert_yaxis();ax.set_xlim(0,max(counts)*1.24+1);ax.set_xlabel('阳性原帖数量；同帖可有多个表达，不相加为总帖数')
    for b,v in zip(bars,counts):ax.text(v+max(counts)*.015,b.get_y()+b.get_height()/2,f'{v:,} · {pc(v,n)}',va='center',fontsize=10)
    ax.set_title('十项表达保留完整描述，主模型采用预先筛选的候选',fontweight='bold',pad=12)
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.savefig(ROOT/'figures/v5_full_expression_support.png',bbox_inches='tight');plt.close(fig)
    co=a['main'].get('coefficients',{});codes=list(co)
    fig,ax=plt.subplots(figsize=(10.5,4.4),layout='constrained')
    for i,code in enumerate(codes):
        r=co[code];color='#326b55' if r['q_bh_within_family']<.05 else '#697e90'
        ax.errorbar(r['beta'],i,xerr=[[r['beta']-r['ci_low']],[r['ci_high']-r['beta']]],fmt='o',color=color,capsize=3,markersize=6)
    ax.axvline(0,color='#a87b6b',linewidth=1,linestyle='--');ax.set_yticks(range(len(codes)),[NAMES[c] for c in codes]);ax.invert_yaxis()
    ax.set_xlabel('log(1＋点赞数)系数与95%作者聚类置信区间')
    ax.set_title(f"联合表达模型：{a['main']['n']:,}帖，{a['main']['n_authors']}位作者",fontweight='bold',pad=12)
    ax.spines[['top','right','left']].set_visible(False);ax.tick_params(axis='y',length=0);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.savefig(ROOT/'figures/v5_full_likes_coefficients.png',bbox_inches='tight');plt.close(fig)

def main():
    s=js('v5_full_coding_summary.json');a=js('v5_full_analysis.json');c=js('v5_full_measurement_comparison.json')
    review=js('v5_full_additional_ai_review.json');audit=js('v5_full_independent_audit.json')
    n=s['n_nonempty_posts'];u=s['n_unique_texts'];p=s['post_coverage'];e=p['axes']['expression'];t=p['axes']['topic'];either=p['axes']['either']
    ue=s['unique_text_coverage']['axes']['expression'];m=a['main'];co=m.get('coefficients',{});v=a['main_collinearity']
    figures(s,a,c)
    sig=qualified(co);signal='、'.join(sig) if sig else '无'
    main_finding=(f"主模型中，{'、'.join(sig)}与点赞存在组内BH q＜0.05的条件关联。" if sig else
      '控制作者、日期、正文形式及其他表达后，七项表达均未呈现明确的点赞关联；三种稳健性检查也未改变这一判断。')
    coverage_rows=[['至少一项具名表达',e['any_positive'],pc(e['any_positive'],n),'表达类别的阳性范围'],
      ['至少两项具名表达',e['two_or_more_positive'],pc(e['two_or_more_positive'],n),'保留同帖的多种明确表达'],
      ['十项表达全部可判',e['all_known'],pc(e['all_known'],n),'各项明确阳性或阴性'],
      ['十项表达全为明确阴性',e['all_negative'],pc(e['all_negative'],n),'可比较的无阳性，不等于整帖没有信息'],
      ['无具名表达阳性且含未知',e['no_positive_some_unknown'],pc(e['no_positive_some_unknown'],n),'不能把未知填成阴性'],
      ['至少一项具名内容对象',t['any_positive'],pc(t['any_positive'],n),'运动、身体、饮食、生活或工具'],
      ['内容或表达至少一项阳性',either['any_positive'],pc(either['any_positive'],n),'两个轴的并集，其他类不计入'],
      ['本轮表达主模型实际纳入',m['n'],pc(m['n'],n),'仅要求该模型变量和控制项可用']]
    hist=c['historical_same_post_population'];histrows=[]
    for key,name in [('legacy_four_lexical','原四项词典'),('v2_named_expression','历史v2十项表达'),('v3_nine_expression','历史v3九项表达')]:
        r=hist[key];histrows.append([name,r['old_positive'],pc(r['old_positive'],n),r['new_only_positive'],r['old_only_positive'],r['new_positive']-r['old_positive']])
    erows=[]
    for code in [c for c in NAMES if c.startswith('S_')]:
        r=a['variables'][code];erows.append([NAMES[code],r['n_positive'],pc(r['n_positive'],n),r['n_unknown_nonempty'],r['positive_authors'],r['authors_within_variation'],'主模型' if code in m['codes'] else '保留描述'])
    trows=[]
    for code in [c for c in NAMES if c.startswith('T_')]:
        r=a['variables'][code];trows.append([NAMES[code],r['n_positive'],pc(r['n_positive'],n),r['n_unknown_nonempty']])
    cr=[]
    for code,r in co.items():cr.append([NAMES[code],f(r['beta']),interval(r),pv(r['p']),pv(r['q_bh_within_family'])])
    ag=review['agreement'];ar=[]
    for code in [c for c in NAMES if c.startswith('S_')]:
        r=ag['per_label'][code];ar.append([NAMES[code],r['both_positive'],r['comparable_positive_union'],pa(r['positive_agreement_known_only']),r['either_unknown'],f"{r['three_state_exact']}/80"])
    fixed=c['fixed_pilot_comparisons'];fixedrows=[]
    for part,title in [('random','原200条随机诊断'),('targeted_no_v3_positive','原60条困难诊断')]:
        r=fixed[part];nn=r['n']
        fixedrows.append([title,nn,r['production']['axes']['expression']['any_positive'],
          f"{r['against_pilot_a']['expression_positive_and_unknown_set_exact']}/{nn}",f"{r['against_pilot_b']['expression_positive_and_unknown_set_exact']}/{nn}"])
    topic=a['topic_adjustment'];topictext='内容补充模型未能保留主变量的支持，详见聚合结果。';topic_table=''
    if topic['status']=='evaluated':
        tc=topic['with_topics'].get('coefficients',{});sc=topic['expression_only_same_sample'].get('coefficients',{})
        topictext=f"内容补充模型使用{topic['n']:,}帖，比主模型少{topic['n_excluded_from_main']:,}帖。下表先在这同一批帖子上重新估计表达模型，再加入具名内容对象，避免把换样本造成的变化算成内容解释。加入内容后，表达检验组内q＜0.05的有：{'、'.join(NAMES[k] for k in m['codes'] if k in tc and tc[k]['q_bh_within_family']<.05) or '无'}。"
        topic_table=table(['表达','同样本未加内容β','同样本加入内容β','加入内容后q'],[[NAMES[k],f(sc[k]['beta']),f(tc[k]['beta']),pv(tc[k]['q_bh_within_family'])] for k in m['codes'] if k in sc and k in tc])
    pol=a['polarity'];polrows=[[POL[k],pol['counts'].get(k,0),'纳入条件比较' if k in pol['retained_levels'] else '支持不足，仅描述'] for k in POL]
    poltext='本轮条件组合未满足至少两组的估计支持，未强行估计差异。';poltable=''
    if 'model' in pol and pol['model'].get('coefficients'):
        ref=POL[pol['reference']];poltext=f"条件模型最终纳入{pol['n_retained']:,}帖，以“{ref}”为参照。它只比较体验或评价明确、两个方向均明确、且组合支持足够的帖子；沿用正文形式、作者、日期等控制，没有额外控制七项表达父变量，不能解释为所有表达类型相同下的纯情绪效应。"
        poltable=table(['相对参照的组合','β','95%区间','组内BH q'],[[r['label'],f(r['beta']),interval(r),pv(r['q_bh_within_family'])] for r in pol['model']['coefficients'].values()])
    vr=[[NAMES[k],f(x)] for k,x in v.get('vif',{}).items()]
    robustrows=[]
    for code,r in co.items():
        row=[NAMES[code],f(r['beta'])]
        for k in ['drop_top_1_percent_likes','authors_min_10','author_equal_weight']:
            q=a['robustness'][k].get('coefficients',{}).get(code)
            row.append(f"{q['beta']:.3f} / {pv(q['q_bh_within_family'])}" if q else '未估计')
        robustrows.append(row)
    jr=ag['joint_polarity'];added=either['any_positive']-e['any_positive']
    text=f'''# Keep社区正文多维测量：全量重读与点赞关联

**v5全量实证版 · 可编辑报告 · 2026年11月5日**

本轮已按同一冻结手册重新阅读全部{u:,}种不同正文，回填到{n:,}条非空原帖；原四项词典退出新主模型。十项表达识别出至少一项明确表达的有{e['any_positive']:,}帖（{pc(e['any_positive'],n)}），其中{e['two_or_more_positive']:,}帖同时有至少两项表达（{pc(e['two_or_more_positive'],n)}）。表达主模型实际纳入{m['n']:,}帖（非空正文的{pc(m['n'],n)}、全部9,532帖的{pc(m['n'],9532)}），这个数包括可明确判断为阴性的帖子。

{main_finding} 本轮恢复了四项词典与v3未能覆盖的许多表达，数据没有支持某一种表达能稳定获得更多点赞的说法。覆盖高低不等于分类正确：新增80条盲读的完整表达集合一致率为73.8%，鼓励、体验评价及方法建议仍有边界分歧。当前测量来自AI阅读，独立人工语义复核为0。

## 1. 数据范围与正文利用率

全部样本有9,532帖。其中3,984帖没有可观察的原始正文，134帖在清理后为空，剩余5,414帖正文非空。前两部分保留在元数据描述中，不能凭空补出语义；因此任何正文方案都应先以5,414帖作为语义分析的参照范围。非空正文占全样本{pc(n,9532)}，不是新分类只利用了这么多可读数据。

本轮对4,156种不同正文统一重读，再按原帖映射恢复重复文本，回归单位仍是帖子。去重节省的是相同文字的重复编码，没有删除相同正文对应的不同帖子。不同正文中具名表达阳性为{ue['any_positive']:,}/{u:,}（{pc(ue['any_positive'],u)}）；帖子层面的比例受重复次数影响，下面统一用原帖作分母。

{table(['口径','原帖数','占5,414帖','回答的问题'],coverage_rows)}

具名表达没有阳性的共有{n-e['any_positive']:,}帖，要区分“十项都明确没有”与“没有阳性但仍有未知”。纯符号、语义无法识别的片段可以保留未知；不能为了接近100%就塞进展示或积极表达。其他明确表达另记，不计入具名覆盖。正文形式、长度、表情等信息仍可用于各自适合的描述。

![同范围覆盖与主模型纳入](figures/v5_full_coverage.png)

图1　前三项与v5阳性项均为同一5,414帖的具名阳性比较；最后一项为v5回归纳入数，含明确阴性，与前四项含义不同。

{table(['历史口径','原阳性帖','原阳性比例','v5阳性而原无','原阳性而v5无','v5阳性净变化'],histrows)}

这些是定义与实际编码同时变化后的标签转移，不能直接称为纠正了多少错误。v2原本就覆盖题注、观点和建议，不能因为v5比v3覆盖广就声称超越全部旧方案。新方案的价值还包括把内容对象、表达行为与条件细节分开，并明确保留阴性和未知。

具体到本轮，v5比v3净增加1,375帖、约25.4个百分点；比v2少36帖、约0.7个百分点。v2阳性而v5无具名阳性的70帖中，15帖在v5十项全未知，37帖十项明确阴性，18帖已知与未知并存。这个差别说明测量边界仍会改变，不能把覆盖略降直接等同于利用数据更差，也不能只归因为纯表情被排除。

## 2. 变量设计与正文表达分布

研究要比较正文怎样表达与互动反馈的关系。一个帖子可以记录训练、写出疲惫、再鼓励继续；强制分到唯一主类会丢掉实际信息。因此本轮使用可重叠指标：内容轴回答谈什么，表达轴回答正文在完成什么交流行为，条件属性记录相应表达中的细节。它们是研究问题下的操作化测量，不是穷尽所有表达风格的天然分类。

四项词典的原意被重新拆解：自律或目标词分到安排目标、鼓励及事件断言等不同信息；称呼不直接推断互助；积极词改为体验/评价语境中的正负方向；问号保留为形式信息，明确征询或邀请才进入请求表达。新定义有实际变化，所以点赞模型必须重估，旧系数不能改名继承。

{table(['表达行为','阳性帖','占非空正文','未知帖','阳性作者数','作者内有变化数','本轮位置'],erows)}

七项主候选来自此前冻结规则下的200条随机双编码筛查；本轮再按阳性、阴性各至少40帖、至少10位作者有作者内变化检验支持，并在联合样本复查。解释建议、征询邀请、供给告知仍完整描述：此前试点阳性太少，不因全量出现更多就追认其已通过一致性验证，也不按点赞显著性临时替换主变量。

![全量表达分布](figures/v5_full_expression_support.png)

图2　蓝绿色为进入本轮主模型的表达，灰色保留描述。多标签允许共存，柱高不能相加为总帖数。多标签比例本身既不证明分类有问题，也不证明边界清楚，需结合规则与重复盲读。

{table(['内容对象','阳性帖','占非空正文','未知帖'],trows)}

内容对象与表达的阳性并集比单独表达增加{added:,}帖。这是内容轴带来的实际增量；两个轴仍分别保存，不能要求内容明确才允许表达入模。具体纳入与排除边界见[冻结编码手册](正文多维测量方案_v5_编码手册.md)。

记录与展示覆盖2,914帖（53.8%），是最常见的表达；评价、体验、观点、鼓励和问候各有数百帖。征询邀请有67帖，供给告知只有4帖，后者不足以支撑稳定的单独回归。内容轴只比表达轴多覆盖20帖，其主要用途是区分讨论对象，而不是大幅增加正文覆盖。

## 3. AI辅助编码与一致性检查

本轮由大模型按84批实际阅读全文，对每个标签逐项判断，并为每项阳性保留精确原文证据；模型只看匿名正文与冻结手册，不看点赞、旧标签或原帖身份。完成的批次在中断后保留，其余由新上下文续读。全部260条试点正文也重新编码，没有把旧试点答案作为生产答案导入。代码用于核对字段、证据子串、父子逻辑、批次与映射，不用关键词规则替代这次语义阅读。

全量归并核对了全部4,156条的阳性证据与条件属性逻辑，回填数与9,532帖状态一致。编码者主动报告的问题按冻结手册再读，共记录{s.get('n_coder_reported_recording_corrections',0)}处个别编码或证据纠错，含{s.get('n_coder_reported_boundary_flags',0)}处边界个案的AI复查，保留改前内容、原因与哈希；这些修正均在查看全量分布及本轮点赞结果前完成。结构通过只能说明格式和证据可追溯，不能证明证据足以支持语义标签，个案AI复查也不等于独立人工效度验证。

原200条随机诊断和60条困难诊断保留为固定对照。本轮生产编码与原A、B分别比较，不能把三份同基座AI结果称为人类投票真值。

{table(['固定对照组','不同正文数','本轮具名表达阳性','与原A全表达三状态集合相同','与原B全表达三状态集合相同'],fixedrows)}

又从排除已有记录的开发与复核材料后剩余的2,833种正文中随机抽80条，交给新的独立上下文盲读。抽样在生产已完成{review['sampling_metadata']['production_batches_present_at_freeze']}批时冻结，发生于查看生产标签分布和本轮点赞结果之前，属于补充检查，不冒充最初试点的一部分，也不是从未接触过的新语料。

80条中，两次编码的完整表达阳性及未知集合相同{ag['expression_positive_and_unknown_set_exact']}条（{pc(ag['expression_positive_and_unknown_set_exact'],80)}）；至少同意一项相同具名表达的有{ag['at_least_one_same_named_expression']}条。逐项结果如下。

{table(['表达','共同阳性','双方可比阳性并集','阳性一致','任一未知','三状态相同'],ar)}

阳性一致按2×共同阳性÷（2×共同阳性＋两方向单方阳性）计算，只在双方都可判的比较中使用，不能称为准确率。支持很少的项不因一致率高就获得可靠保证；支持较多仍有分歧的项，解释时应降低信心。补充检查不改变已经冻结的本轮模型名单，也不把分歧答案看过后回填成更好看的覆盖率。

这次盲读的结论是“主要范围能复现，部分边界仍不稳”。展示阳性一致94.3%，观点感悟93.8%；体验80.0%、评价81.1%，鼓励75.0%且有4条只有生产编码标为阳性。方法建议仅在4条可比阳性并集中有1条共同阳性，阳性一致40.0%，支持虽少，仍提示不能把它视为已稳定的测量。问候的100%来自10条可比阳性，请求的100%只来自1条，不能据此宣布后者完全可靠。这些结果限制了“分类合理性已经得到充分核实”的说法，后续应优先核对上述边界及罕见类。

正负方向还取决于父集合是否识别一致：80条中双方都认为有体验或评价的为{jr['both_parent_positive']}条，父集合状态不同{jr['parent_set_disagreement']}条；双方父集合为阳性且两个方向均明确的{jr['both_coders_both_attributes_known']}条中，正负组合相同{jr['exact_combination_on_known']}条。同基座模型可能共享误判，本轮独立人工语义复核为0。因此这些是可复查的AI辅助测量，不能宣称四类或十类已经得到人工效度认证。

## 4. 正文表达与点赞数的关联

主模型在{m['n']:,}帖、{m['n_authors']}位作者上联合放入{len(m['codes'])}项表达。比较某项表达出现与未出现时，同时考虑其他已测表达、正文长度对数、tag、表情数、课程引用、内容形式、帖子类型、时段以及作者与日期固定效应。原四项词典没有进入新控制项；未知不填0，未要求所有条件属性齐全才入模。

因变量为log(1＋点赞数)，标准误按作者聚类，并使用有限样本修正和作者簇数减1的t自由度。下表区间为逐项95%聚类区间，BH q只在本模型的表达检验组内校正；区间并未做同时推断校正。这些区间以本轮AI标签为给定输入，未计入语义编码误差或标签不确定性。系数不是点赞率，也不直接表示平均点赞数变化百分比。

{table(['表达','β','95%作者聚类区间','p','表达组内BH q'],cr)}

![联合表达模型的点赞系数](figures/v5_full_likes_coefficients.png)

图3　点为联合模型系数，线为逐项95%作者聚类区间；绿色表示本模型表达组内BH q＜0.05。区间较宽或跨0的结果保留，不把未达阈值解释为没有任何关系。

七项表达的区间均包含0，最小组内q为{min(r['q_bh_within_family'] for r in co.values()):.3f}。例如未来安排与目标的估计值为0.090，区间为[-0.022, 0.203]：方向偏正，但现有数据仍允许没有差异或一定负向差异，不能写成目标表达能带来更多点赞。自身体验、对象评价和观点感悟的点估计接近0，也不能据此证明所有可能的实际关系都为零。

逐项最大可用样本为5,235—5,244帖，同主样本逐项模型为5,217帖；两组逐项结果也均未达到表达组内q＜0.05。因此“联合放入后彼此抵消”不是当前数据已支持的解释。发布后的曝光、粉丝规模变化、采集时的累计时间和图片视频内容没有被完整控制，任何条件关联都不能改写成采用这种表达就会获得更多或更少点赞。

## 5. 内容对象与显性正负方向的补充分析

{topictext}

{topic_table}

这里加入的是本轮按冻结规则、由AI读取的可重叠内容对象指标，含义与旧NMF成分不同。内容指标允许多项为1，不是和为1的组成权重；不能套用NMF省略参照主题的解释。表达与内容的q分别在各自检验组内校正，内容补充模型仍属于探索性检查。

加入五项内容对象后，表达仍没有达到组内q＜0.05；五项内容对象本身也没有达到各自检验组内q＜0.05。当前结果没有显示“先控制内容，就会出现明确的表达关联”。

正负方向只在自身体验或对象评价明确时判定。负向包括疲惫、疼痛等身体不适，因此不能简单称为负面心理情绪。两项都没有只表示没有显性正负方向，不表示作者心理中性；无相应父表达记为不适用，不能当成“没有负向”。

共有{pol['parent_positive']:,}帖有明确体验或评价，其中两个方向都可判的有{pol['n_known_both_polarity']:,}帖。

{table(['条件组合','原帖数','本轮使用'],polrows)}

{poltext}

{poltable}

条件组须有足够阳性、对照和作者内变化才估计。在{pol['parent_positive']:,}帖父阳性中，{pol['parent_positive']-pol['n_known_both_polarity']:,}帖因方向属性未知未进入条件比较；其余{pol['n_known_both_polarity']:,}帖四组均满足支持，没有因组合稀少再排除帖子。属性未知的帖子仍可用于其他信息明确的分析，不能把条件模型的较小样本说成整套方案只利用了这些帖子。事件断言、计划目标、问候与感谢本轮保留描述，逐项计数见公开汇总，不追加大量结果导向检验。

本轮四组都满足支持门槛。与仅显性正向相比，负向、正负并存和均无显性方向均未显示明确差异；仅负向与仅正向的点估计尤其接近0。这个结果不能支持“写积极内容更容易获赞”，也不意味着身体不适的自述没有交流价值，因为点赞不是交流价值的完整测量。

## 6. 共线性检验与稳健性分析

同帖允许多种表达共存，表达指标也可能与正文长度、作者习惯等控制项相关。这些关系如果接近线性重复，会放大系数不确定性，因此在实际回归样本中检验完整设计的共线性。VIF使用主模型的{v['n']:,}帖，包含表达、全部控制项和作者日期固定效应，矩阵秩为{v['rank']}/{v['columns']}。VIF通过完整相关矩阵逆与逐项残差回归两种计算交叉核对；数值范围{v.get('min_vif',float('nan')):.2f}—{v.get('max_vif',float('nan')):.2f}。

{table(['表达','完整设计VIF'],vr)}

VIF达到5的表达为：{'、'.join(NAMES[x] for x in v.get('vif_ge_5',[])) or '无'}。低VIF只说明给定设计中的线性重复不强，不能证明概念完整、分类准确或估计没有偏差。高重叠也不直接要求合并：应先分辨同帖确有多种表达，还是同一句话被不清楚的边界重复计数。

另按预定安排检查三种变化：剔除主样本点赞数高于99分位点的帖子；只留在主样本至少发10帖的作者；以主样本作者帖数的倒数加权，让每位作者总权重相同。前两项分别使用{a['robustness']['drop_top_1_percent_likes']['n']:,}与{a['robustness']['authors_min_10']['n']:,}帖，等权模型仍为{a['robustness']['author_equal_weight']['n']:,}帖。

{table(['表达','主模型β','去最高点赞：β / q','作者至少10帖：β / q','作者等权：β / q'],robustrows)}

各敏感性模型的q分别在该模型表达组内校正，不覆盖全部历史探索。方向、区间或q随处理变化的表达应如实写为敏感；不能只挑一个显著版本当作最后结论。作者固定效应和按作者聚类都不能代替测量效度，也不能排除未观测的曝光差异。

三种检查均未发现表达组内q＜0.05的项，未得到明确表达关联的总体判断一致。剔除极端点赞、排除少帖作者后，估计值与主模型接近；作者等权时，自身体验由接近0变为0.080，鼓励由0.055变为0.007，说明部分点估计受作者权重影响，不能把“都未达阈值”扩大成系数完全稳定。

## 7. 研究结论与既有结果的衔接

第一，新方案覆盖了大多数可观察正文，主回归使用96.4%的非空原帖；3,984帖原始正文缺失和134帖清理后为空，仍是语义分析范围的主要限制。第二，30.5%的非空原帖有至少两项表达，应保留多标签结构；完整设计VIF没有显示严重线性重复。第三，在本轮测量与控制条件下，七项表达、内容补充及条件正负组合都没有提供明确的点赞差异证据，稳健性分析延续了这一判断。覆盖的改善不能以获得显著结果为标准。

可以继承的是清洗口径、正文可观察状态、元数据与点赞分布，以及在原定义下计算的评论文本和回复网络；本轮没有用新标签改写这些结果。原四项词典及v2、v3的标签和系数继续作为历史比较，新方案的点赞结果来自本轮实际重估。

旧NMF主题回归仍保留为独立历史探索，**回归使用连续主题权重，不用最大权重的主类代替**。五个权重和为1时，带截距模型省去一个参照成分；系数表示在其他非参照成分权重与协变量不变时，把权重从参照成分移向所述成分的关联。原分词模型使用2,470帖、86位作者，字符表示实验的5,273帖属于另一方案，不能说原主题模型已扩到该范围。这次全量正文重读也没有重新训练NMF。

本版已完成全部非空正文的统一重读、帖子映射、覆盖与重叠统计、实际设计共线性、点赞重估和预定敏感性。变量没有为了追求100%阳性而扩类，也没有根据点赞结果挑选。其适合用作可追溯的探索性正文测量与条件关联报告；涉及类别合理性的强结论，仍受边界分歧与没有独立人工效度证据的限制。

自动文本测量需要围绕具体研究问题检查，而不能以计算规模替代效度证据；参见[Grimmer与Stewart（2013）](https://www.cambridge.org/core/journals/political-analysis/article/text-as-data-the-promise-and-pitfalls-of-automatic-content-analysis-methods-for-political-texts/F7AAC8B2909441603FEB25C156448F20)。发现测量方式与估计关系使用同一批语料的风险可参见[Egami等（2022）](https://naokiegami.com/paper/CausalText.pdf)；本轮冻结后重读不消除此前多轮探索，也不等于完成该文的分样本因果识别。

正文与表格均可在Word中直接修改，Markdown是重新生成本报告的文字来源；直接改Word不会自动写回Markdown。原始正文、逐项证据、盲包与原帖映射只保存在被Git忽略的私有目录，公开文件提供规则、代码与汇总。

{table(['用途','公开文件'],[
 ['标签定义与边界','[冻结编码手册](正文多维测量方案_v5_编码手册.md)'],
 ['全量分析安排','[冻结分析协议](code/v5_full_analysis_protocol.json)'],
 ['覆盖、未知与条件属性计数','[全量编码汇总](results/v5_full_coding_summary.json)'],
 ['历史范围及原试点对照','[测量对照](results/v5_full_measurement_comparison.json)'],
 ['80条独立上下文盲读','[补充AI一致性](results/v5_full_additional_ai_review.json)'],
 ['完整系数、支持和敏感性','[全量分析](results/v5_full_analysis.json)'],
 ['独立数值与映射复算','[复算审计](results/v5_full_independent_audit.json)']])}
'''
    (ROOT/f'{STEM}.md').write_text(text)
    spec=importlib.util.spec_from_file_location('renderer',ROOT/'code/build_phase2_report.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
    renderer.STEM=STEM;_,soup,headings=renderer.read_manuscript();html=renderer.write_html(soup,headings);renderer.write_docx(html,headings)
    print(json.dumps({'markdown':str(ROOT/f'{STEM}.md'),'docx':str(ROOT/f'{STEM}.docx'),'headings':len(headings)},ensure_ascii=False))

if __name__=='__main__':main()
