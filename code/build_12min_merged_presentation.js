/* Source-backed revision using the teammate's eight chapters.
 * Run with NODE_PATH pointing to an installation of pptxgenjs and jszip.
 * Existing analyses and earlier presentations are read only.
 */
const pptxgen=require('pptxgenjs'),JSZip=require('jszip');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..');
const QA=path.join(ROOT,'validation/slides_12min_dyx');
const OUT=path.join(ROOT,'Keep社区内容表达与互动反馈_12分钟合并版');
fs.mkdirSync(QA,{recursive:true});
const pres=new pptxgen();pres.layout='LAYOUT_WIDE';
pres.author='陈霖、董依心';pres.company='社交媒体网络分析课程小组';
pres.title='Keep社区内容表达与互动反馈分析';pres.subject='八章结构与RQ逐项分析；全部为正文';pres.lang='zh-CN';
const FONT='Arial Unicode MS';pres.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'zh-CN'};
const C={ink:'20332F',green:'245C4F',deep:'173F36',muted:'65756F',light:'EDF4F0',pale:'F6F8F7',line:'DFE6E2',orange:'B97339',paleOrange:'F8F0E8',gray:'AAB8B0',white:'FFFFFF'};
const CH=['研究背景、意义与研究问题','数据来源、清洗与分析方法','数据覆盖与描述统计','文字表达与点赞的关联','帖子主题与点赞的关联','评论的主要内容','评论区的网络结构','研究结论与局限'];
const MAIN=23,M=[];
const {addSensitivityPanels,postprocessSensitivityCharts}=require('./sensitivity_native_charts');
const ORIGINAL=[1,2,3,5,6,7,8,9,10,11,12,13,14,15,16,18,19,20,null,21,23,24,25];
const BASE=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,null,19,20,21,22];
const DYX=[1,2,3,5,7,8,9,6,10,11,12,13,14,15,16,17,18,19,21,20,22,23,24];
const TIMES=[8,35,40,32,32,27,12,32,28,40,45,35,42,15,30,45,30,25,30,30,18,25,8];
const SHORT=TIMES.slice();
function csv(name){
 const str=fs.readFileSync(path.join(ROOT,'results',name),'utf8').replace(/^\uFEFF/,'').trim();
 const rows=[];let r=[],cell='',q=false;
 for(let i=0;i<str.length;i++){const c=str[i];if(c==='"'){if(q&&str[i+1]==='"'){cell+='"';i++;}else q=!q;}else if(c===','&&!q){r.push(cell);cell='';}else if(c==='\n'&&!q){r.push(cell.replace(/\r$/,''));rows.push(r);r=[];cell='';}else cell+=c;}
 r.push(cell);rows.push(r);const keys=rows.shift();return rows.map(r=>Object.fromEntries(keys.map((k,i)=>[k,r[i]])));
}
const load=n=>JSON.parse(fs.readFileSync(path.join(ROOT,'results',n),'utf8'));
const summary=load('summary.json'),extension=load('extension_summary.json');
const add=JSON.parse(fs.readFileSync(path.join(QA,'descriptive_additions.json'),'utf8'));
const features=csv('text_features_summary.csv'),coef=csv('regression_coefficients.csv'),fit=csv('model_fit.csv');
const coverage=csv('extension_coverage_media.csv'),themes=csv('supplemental_topic_author_weighting.csv');
const topicReg=csv('extension_topic_regression.csv'),nodes=csv('network_nodes.csv');
const words=csv('comment_text_features.csv'),direct=csv('supplemental_direct_reply_language.csv');
const windows=csv('extension_window_networks.csv');
const topicNames=['靠墙静蹲记录','骑行里程记录','运动与训练交流','跑步与训练打卡','生活感悟与问候'];
const fmt=(n,d=3)=>(+n).toFixed(d).replace('-','−');
const ci=r=>`[${fmt(r.ci_low)}, ${fmt(r.ci_high)}]`;
function text(s,t,x,y,w,h,size=18,color=C.ink,bold=false,extra={}){
 s.addText(t,{x,y,w,h,fontFace:FONT,fontSize:size,color,bold,margin:0,paraSpaceAfterPt:0,valign:'top',breakLine:false,wrap:true,lang:'zh-CN',...extra});
 s._m.text.push({text:t,x,y,w,h,size});
}
function rect(s,x,y,w,h,fill){s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:fill},line:{color:fill,width:0}});}
function dot(s,x,y,d,fill){s.addShape(pres.ShapeType.ellipse,{x,y,w:d,h:d,fill:{color:fill},line:{color:fill,width:0}});}
function line(s,x,y,w,h,color=C.line,width=1,arrow=false){s.addShape(pres.ShapeType.line,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});}
let lastChapter=0;
function begin(title,ch,rq,source,foot='',{dark=false,clean=false}={}){
 if(ch&&ch!==lastChapter){pres.addSection({title:`${String(ch).padStart(2,'0')} ${CH[ch-1]}`});lastChapter=ch;}
 const scope=(rq.match(/RQ[123]/g)||[]); const unique=[...new Set(scope)]; const question=unique.length===1?unique[0]:null;
 const sub=(question==='RQ1'&&/主题主要|高频记录/.test(title))?'帖子主题与作者构成':(ch?CH[ch-1]:'封面');
 const headings={RQ1:'内容与点赞的分布',RQ2:'文字、主题与点赞的关联',RQ3:'评论中的回应与参与'};
 const s=pres.addSlide(ch?{sectionTitle:`${String(ch).padStart(2,'0')} ${CH[ch-1]}`} : {});
 s.background={color:dark?C.deep:C.white};
 s._m={page:M.length+1,originalPage:ORIGINAL[M.length],basePage:BASE[M.length],dyxPage:DYX[M.length],title,chapter:ch,chapterName:ch?CH[ch-1]:'封面',subsection:sub,question,rq,source,foot,appendix:false,text:[],charts:[],speech:'',seconds:TIMES[M.length],shortSeconds:SHORT[M.length]};M.push(s._m);
 if(!clean){text(s,question?`${question}  ${headings[question]}`:ch===8?'共同局限与后续改进':'研究设计与数据',.58,.3,8.8,.3,13,dark?'C5D9D0':C.green,true);text(s,sub,9.12,.3,3.62,.3,11,dark?'C5D9D0':C.muted,false,{align:'right'});text(s,title,.58,.88,12.15,.67,28,dark?C.white:C.ink,true);}
 text(s,foot||source,.58,7.09,11.36,.22,9,dark?'BDD3C8':C.muted);
 text(s,`${String(M.length).padStart(2,'0')} / ${MAIN}`,11.99,7.07,.77,.25,10,dark?'BDD3C8':C.muted,false,{align:'right'});
 return s;
}
function note(s,speech,focus){s._m.speech=speech;s._m.focus=focus;s.addNotes(`12分钟版｜本页预算${s._m.seconds}秒（已含页面阅读停顿）\n\n${speech}\n\n讲述重点：${focus}\n\n来源：${s._m.source}`);}
function table(s,headers,rows,x,y,w,colW,{size=15.5,rowH=.55,highlight=-1}={}){
 const data=[headers.map(t=>({text:t,options:{bold:true,color:C.green,fill:C.light}})),...rows.map((r,i)=>r.map(t=>({text:String(t),options:{fill:i===highlight?C.paleOrange:i%2?C.pale:C.white,color:C.ink}})))];
 s.addTable(data,{x,y,w,colW,rowH,fontFace:FONT,fontSize:size,border:{color:C.white,pt:1},margin:[.09,.12,.09,.12],vertAnchor:'mid',autoPage:false,paraSpaceAfterPt:0});
 s._m.text.push({text:headers.join(' ')+' '+rows.flat().join(' '),x,y,w,h:rowH*(rows.length+1),size});
}
function chart(s,data,x,y,w,h,opts={}){
 const o={x,y,w,h,fontFace:FONT,showTitle:false,showLegend:data.length>1,legendPos:'b',legendFontFace:FONT,legendFontSize:11.5,
  catAxisLabelFontFace:FONT,catAxisLabelFontSize:12,valAxisLabelFontFace:FONT,valAxisLabelFontSize:10.5,
  catAxisLabelColor:C.ink,valAxisLabelColor:C.muted,catAxisLineShow:false,valAxisLineShow:false,
  catGridLine:{style:'none'},valGridLine:{color:'E7ECE9',width:.5},showValue:true,dataLabelPosition:'outEnd',dataLabelFontFace:FONT,dataLabelFontSize:12,dataLabelColor:C.ink,dataLabelFormatCode:'0.0',showCatName:false,showSerName:false,
  chartColors:data.length>1?[C.green,C.orange]:[C.green],showBorder:false,showShadow:false,showMarker:false,valAxisMinVal:0,gapSizePct:75,
  ...(opts.barDir==='bar'?{catAxisOrientation:'maxMin',catAxisLabelPos:'low',valAxisLabelPos:'low'}:{}),...opts};
 s.addChart(pres.ChartType.bar,data,o);s._m.charts.push({type:'bar',data,options:o});
}
function para(s,head,body,x,y,w,{color=C.green,size=18}={}){text(s,head,x,y,w,.36,20,color,true);text(s,body,x,y+.58,w,1.12,size);}
function stat(s,n,l,x,y,w=3.5){text(s,n,x,y,w,.65,34,C.green,true);text(s,l,x,y+.79,w,.45,15.5,C.ink);}

// 1. Cover.
{
 const s=begin('Keep社区内容表达与互动反馈分析',0,'RQ1 · RQ2 · RQ3','课程小组汇报','社交媒体网络分析 · 课程小组汇报',{dark:true,clean:true});
 text(s,'Keep 社区',.75,.7,9,.5,25,'C3D9CE');text(s,'内容表达与\n互动反馈分析',.75,1.72,10.7,1.75,40,C.white,true);
 text(s,'哪些内容获得更多点赞反馈，评论又如何互动？',.8,4.12,11.7,.65,24,'DCEAE1');
 text(s,'陈霖  ·  董依心',.8,5.96,9,.45,21,C.white);
 note(s,'我们看Keep里的内容、点赞和评论，依次回答三个研究问题。','开场点出三个研究问题。');
}
// 2. Research design remains the first body slide.
{
 const s=begin('研究背景、问题与预期',1,'RQ1 · RQ2 · RQ3','原报告§1；同伴版研究设计页','预期是待检验的可能解释，后文按相同RQ编号逐项回答。');
 text(s,'健身社区里，什么内容受到关注，人们又怎样交流？',.7,1.78,11.9,.5,25,C.green,true);
 text(s,'Keep既记录运动，也承载经验、感受与生活分享。点赞体现可见反馈，评论记录谁在接话。\n创作者关心什么内容得到关注；平台则关心互动是否集中在少数账号、是否有更多人参与。',.72,2.38,11.8,.75,17);
 text(s,'三个具体问题',.87,3.3,5.6,.33,16,C.green,true);text(s,'对应预期：可能出现的结果',7.02,3.3,5.4,.33,16,C.green,true);
 const rows=[['RQ1  样本主要呈现什么内容，点赞怎样分布？','媒体反馈可能不同，高赞帖可能拉高均值；\n正文也可能同时包含运动与生活分享。'],['RQ2  文字表达与主题是否与点赞有关？','自律、积极表达或提问可能对应较高点赞；\n调整作者与情境后，这些差异可能变化。'],['RQ3  评论说什么，形成怎样的互动网络？','读者与帖主、读者彼此都可能互动；\n评论量可能来自广泛参与或少数人反复往来。']];
 rows.forEach((r,i)=>{const y=3.83+i*.97;rect(s,.7,y,11.95,.89,i===1?C.pale:C.light);text(s,r[0],.87,y+.17,5.85,.56,17.5,C.ink,true);text(s,r[1],7.02,y+.12,5.4,.65,16.5);});
 note(s,'Keep既记录运动，也包含经验和生活分享。创作者关心什么内容得到反馈，平台关心互动是否集中在少数账号。我们拆为三个问题：先描述内容和点赞，再检验文字及主题与点赞的关联，最后看评论说什么、谁回应谁、由多少人参与。右栏是可能的解释，后文逐项检验。','补充研究意义，总问题与三个RQ一一对应。');
}
// 3. Data and cleaning.
{
 const s=begin('数据来源与清洗',2,'支撑 RQ1 / RQ2 / RQ3','summary.json；analyze.py时间与清洗；dyx第3页','课程100位作者样本；帖子发表于2020年11—12月（UTC），评论最晚至2021年8月。');
 stat(s,'9,532','帖子 · 100位作者',.72,1.83);stat(s,'11,595','去重后评论',4.78,1.83);stat(s,'1,323','采集到评论的帖子',8.85,1.83);
 table(s,['核查发现','处理方式','分析含义'],[
  ['1,916行重复评论','按评论ID去重，无字段冲突','避免同一发言被重复计入'],
  ['3,984帖缺可用正文','保留；文字计数设0并另作标记','不能把缺失当作真实无文字'],
  ['8,286帖点赞高于记录浏览数','使用累计点赞，不计算点赞率','不解释为曝光转化效率'],
  ['仅1,323帖有已采集评论','其余帖子的评论覆盖记为未知','不作评论数的全样本回归'],
  ['原始时间字段按UTC解析','模型日期与时段统一为北京时间','便于按国内用户的发布情境比较']
 ],.68,3.22,12,[3.5,4,4.5],{size:14.5,rowH:.47});
 text(s,'5,414帖清理后有非空正文；主题分析另筛选2,470帖、86位作者。\n正文覆盖随媒体和作者而不同，主题比例不能当作全部9,532帖的内容比例。',.75,6.25,11.8,.63,15.5,C.green,true);
 note(s,'样本有9,532帖、100位作者，以及去重后的11,595条评论。重复评论删重，缺失正文保留并标记；点赞与浏览口径不同，因此不算点赞率。只有1,323帖采到评论，其余覆盖记为未知。模型日期和时段统一用北京时间。主题另有2,470帖的子样本，不能把它当作全部内容。','补齐评论覆盖未知与北京时间处理；表格保留供核对。');
}
// 6. Media differences plus the requested long-tail distribution.
{
 const s=begin('图片和视频帖点赞更高，整体分布同时存在长尾',3,'回答 RQ1','media_summary.csv；descriptive_statistics.csv；既有post_features分布汇总','两图为原始描述；右图显示各点赞区间的帖子数，区间宽度不同，不表示概率密度。');
 text(s,'不同媒体的平均点赞',.75,1.85,5.8,.38,18,C.green,true);text(s,'点赞区间中的帖子数',6.96,1.85,5.8,.38,18,C.green,true);
 chart(s,[{name:'平均点赞',labels:['图片','视频','纯文字','无媒体'],values:[51.03,48.05,7.94,3.91]}],.66,2.36,5.77,2.76,{barDir:'col',valAxisMaxVal:60,dataLabelFormatCode:'0.00',catAxisLabelFontSize:12});
 chart(s,[{name:'帖子数',labels:add.like_histogram.labels,values:add.like_histogram.counts}],6.85,2.36,5.84,2.76,{barDir:'col',showValue:false,valAxisMaxVal:2500,catAxisLabelFontSize:9.5,catAxisLabelRotate:0,gapSizePct:25});
 text(s,'均值37.05  ·  中位数25  ·  95%分位109.45  ·  最高5,126',.76,5.35,11.8,.42,18,C.ink,true);
 text(s,'少量高赞帖拉高平均数，均值不能代表普通帖；媒体均值也相差约一个数量级。',.76,6.02,11.8,.48,18,C.green,true);
 text(s,'媒体形式和点赞分布说明了反馈的基本差异；接着看有正文的帖子主要在写什么。',.76,6.59,11.8,.32,15.5,C.muted);
 note(s,'图片和视频帖平均约51和48个赞，文字与无媒体约8和4个。整体分布中，大量帖子在低区间，少量高赞拖出长尾：均值37，中位数25，最高超过五千。因此描述普通帖不能只报平均数，还要同时看中位数与尾部。媒体和反馈的分布已经看到，接着进入正文内容，看这些帖子主要讨论什么。','只回答分布，不提前讲控制模型。');
}
// 11. Restore the full topic composition before discussing author weights.
{
 const s=begin('帖子正文主题主要包括运动和生活',3,'回答 RQ1','extension_topics.csv；extension_summary.json；topic_labels.json','TF-IDF + 非负矩阵分解（NMF），固定提取5类主题；命名不参考点赞。');
 const order=[2,4,3,0,1],labs=order.map(i=>topicNames[i]);
 chart(s,[{name:'主导主题占比',labels:labs,values:order.map(i=>+themes[i].post_equal_share*100)}],.64,2.0,7.15,4.25,{barDir:'bar',valAxisMaxVal:60,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12.5});
 text(s,'2,470帖 · 86位作者',8.28,1.96,4.4,.43,22,C.green,true);
 text(s,'用非负矩阵分解（NMF）提取主题',8.28,2.46,4.39,.3,14,C.muted);
 text(s,'训练交流：运动、减脂、训练、拉伸\n生活问候：人生、生活、早安、美好',8.28,2.92,4.39,1.02,17.5);
 text(s,'前两类合计88.5%。这批有效正文不仅讨论如何训练，也经常写感受、生活和问候，不能把健身社区里的文字都当成运动成绩记录。',8.28,4.1,4.39,1.58,18);
 text(s,'占比按每帖权重最大的主题归类。同一作者可写多个主题，内容量大也可能是某些人写得多。',.74,6.4,11.9,.56,17,C.green,true);
 note(s,'有效正文提取了五类主题，训练交流占52.7%，生活感悟和问候占35.8%，合计88.5%。所以这批Keep文字不只有打卡和运动成绩，也有大量日常表达。这里按每帖权重最大的主题统计篇幅，一人可以贡献很多帖。要判断某种内容是否普遍，还要看它是不是被少数高产作者放大。','先解释两大主题的真实内容，再引出作者等权。');
}
// 12. Author composition as an explanation of a frequent theme.
{
 const s=begin('常见主题，也可能来自少数人的高频记录',3,'回答 RQ1','supplemental_topic_author_weighting.csv；extension_topics.csv','两组沿用同一主题分类；作者等权先计算每人的主题比例，再对86位作者平均。');
 const order=[2,4,3,0,1],labs=order.map(i=>topicNames[i]);
 chart(s,[{name:'按帖子统计',labels:labs,values:order.map(i=>+themes[i].post_equal_share*100)},{name:'每位作者等权',labels:labs,values:order.map(i=>+themes[i].author_equal_share*100)}],.64,1.98,7.2,4.45,{barDir:'bar',valAxisMaxVal:60,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:11.8,gapSizePct:50});
 text(s,'静蹲：3.4% → 0.6%',8.3,2.0,4.35,.58,26,C.orange,true);
 text(s,'85条主导文档中，78条来自同一作者。按帖看是在统计这种记录出现了多少次；作者等权后，才减少了高产作者的重复贡献。',8.3,2.95,4.35,1.59,18);
 text(s,'训练52.7% → 52.6%，生活35.8% → 38.2%。两条主要内容线仍在，变化集中在部分小主题。',8.3,5.08,4.35,1.27,17.5);
 text(s,'训练和生活是两条主要内容线；部分小主题的份额，则会被少数作者的持续记录放大。',.75,6.56,11.85,.37,17,C.green,true);
 note(s,'静蹲按帖子统计占3.4%，让每位作者等权后只剩0.6%。85帖里78帖来自一人，所以这里的常见更多反映一位作者的持续记录。训练和生活两大主题换权重后仍占主要份额。这一步让RQ1的内容分布更准确：既看到训练与生活并存，也分清一种主题是很多人都在写，还是少数人反复记录。','把作者权重作为内容分布的校准，完成RQ1的描述。');
}
// RQ1 closes before any association model is introduced.
{
 const s=begin('RQ1的回答：这批帖子的内容和点赞怎样分布',3,'回答 RQ1 · 本题结论','样本、媒体分布、主题与作者权重结果','范围：9,532帖；主题比例仅代表2,470条有效正文、86位作者。',{dark:true});
 text(s,'媒体不同，收到的点赞并不均匀。',.78,1.92,11.7,.46,25,C.white,true);
 text(s,'图片和视频帖平均约51、48赞，文字与无媒体约8、4赞。整体均值37.05高于中位数25，少量高赞把分布拉出长尾；单用平均数会高估普通帖子的反馈水平。',.8,2.6,11.65,1.0,19,'DFEAE3');
 text(s,'正文同时包含训练交流和生活分享，篇幅也受作者影响。',.78,4.02,11.7,.48,24,C.white,true);
 text(s,'训练交流52.7%、生活问候35.8%，作者等权后仍是两条主线。静蹲却由3.4%降至0.6%，其中85帖有78帖来自一人：这种记录出现多，不等于很多作者都在写。',.8,4.71,11.65,1.02,19,'DFEAE3');
 rect(s,.74,6.12,11.96,.64,'295347');text(s,'RQ2接着问：把媒体、作者与日期一起纳入比较后，文字或主题与点赞还有多大关联？',.94,6.28,11.55,.36,17,'E3ECE6');
 note(s,'RQ1看到媒体点赞不同、整体有长尾；训练和生活是正文主线，小主题还受高产作者影响。下面检验文字关联。','一句回答后转入RQ2，不重复数字。');
}
// 4. Definitions appear before all feature comparisons.
{
 const s=begin('不同文字表达的原始点赞有差异',4,'回答 RQ2 · 变量与原始比较','text_dictionary.json；text_features_summary.csv；dyx第6页','词表识别字面线索，不是情绪量表；各词类可重叠，图中原始均值未作调整。');
 table(s,['五项文字变量','定义与例子'],[['正文长度 L','ln(1+清理后字符数)'],['自律 / 目标 D','坚持、自律、目标、第N天等'],['社交 / 互助 S','大家、小伙伴、谢谢、一起等'],['积极表达 P','开心、快乐、喜欢、哈哈等'],['问号 Q','全角或半角问号，出现记1']],.68,1.99,6.05,[1.8,4.25],{size:15,rowH:.57});
 text(s,'各词类的原始平均点赞',7.12,1.87,5.5,.35,18,C.green,true);
 chart(s,[{name:'命中',labels:['自律 / 目标','社交 / 互助','积极表达','问号'],values:features.map(r=>+r.raw_mean_likes_hit)},{name:'未命中',labels:['自律 / 目标','社交 / 互助','积极表达','问号'],values:features.map(r=>+r.raw_mean_likes_nohit)}],6.93,2.24,5.8,3.5,{barDir:'col',chartColors:[C.green,'AFBCB5'],valAxisMaxVal:130,catAxisLabelFontSize:11.2,dataLabelFontSize:11.5,gapSizePct:65});
 text(s,'除长度外，命中记1；一帖可同时命中多个词类。',.75,5.68,6.1,.51,14.5,C.muted);
 text(s,'回归结果变量：ln(1+点赞数)，\n用于处理RQ1看到的点赞长尾。',.75,6.28,6.1,.58,16,C.green,true);
 text(s,'四类命中组的原始均值都较高。\n下一步检查：媒体和作者构成是否也不同？',7.12,6.05,5.47,.79,16.5,C.ink);
 note(s,'RQ2先定义五项文字线索：长度取对数，自律、社交、积极表达和问号命中记一，各项可以重叠。右图看到，四类命中组的原始平均点赞都更高。但这还不是用词效果，下一页看组别的媒体和作者构成。回归结果仍用一加点赞的对数。','把变量定义与原始均值放在一起；比较顺序仍属RQ2。');
}
// 7. Raw means followed by actual composition evidence, not a rhetorical jump.
{
 const s=begin('文字与点赞的原始差异，也伴随媒体构成差异',4,'回答 RQ2 · 构成比较','descriptive_additions.json；dyx第10页','变量已在第8页定义；图示为各组图片或视频帖占比，尚未调整作者与发布情境。');
 const groups=add.group_composition.filter(r=>r.feature==='positive_expression').sort((a,b)=>b.hit-a.hit);
 text(s,'积极表达两组的图片 / 视频帖占比',.75,1.87,7,.35,18,C.green,true);
 chart(s,[{name:'图片 / 视频帖占比',labels:['命中积极表达','未命中'],values:groups.map(r=>r.image_video_share*100)}],.65,2.43,7.15,3.49,{barDir:'col',valAxisMaxVal:110,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:14});
 table(s,['组别','帖数','涉及作者'],groups.map(r=>[r.hit?'命中':'未命中',r.posts.toLocaleString('en-US'),String(r.authors)]),8.22,2.13,4.47,[1.4,1.6,1.47],{size:15.5,rowH:.62});
 text(s,'平均点赞：57.29 vs 35.76',8.27,4.42,4.38,.73,20,C.ink,true);
 text(s,'两组的媒体和作者构成都不同，\n不能把原始差异直接归给措辞。',8.27,5.28,4.38,.89,17.5);
 text(s,'下一步：同时纳入媒体、作者和日期，比较文字线索是否仍有额外关联。',.75,6.5,11.87,.43,18,C.orange,true);
 note(s,'积极表达命中组平均约57赞，未命中约36赞。但图片或视频占比也从69.1%升到94.9%，涉及的作者范围同样不同。因此要把文字、媒体、作者和日期一起纳入模型，判断这些用词是否还有额外关联。','用媒体构成的实际差别引出控制模型，不重复上一页原始均值图。');
}
// 8. Explicit model equation and successive specifications.
{
 const s=begin('用作者与日期固定效应，进一步改善比较',4,'回答 RQ2 · 回归设定','analyze.py formula()/models()；model_fit.csv','主分析为OLS；N=9,532、100位作者，标准误按作者聚类，五项核心系数采用BH校正。');
 rect(s,.68,1.86,12,.94,C.light);
 text(s,'主模型 M3：ln(1 + 点赞数) = β′X + γ′C + α作者 + δ日期 + ε',.89,2.12,11.58,.47,23,C.green,true);
 text(s,'X：文本长度（对数）、自律、社交、积极、问号。C：正文可用、话题、表情数、课程分享，以及媒体、业务类型、时段。',.75,3.03,11.85,.6,15.5);
 table(s,['模型','调整范围','R²','积极表达系数 / 原始p'],[['M1','X + C + 已记录作者属性','0.563','−0.050 / 0.285'],['M2','X + C + 作者固定效应','0.685','−0.087 / 0.016'],['M3 主模型','X + C + 作者、日期固定效应','0.688','−0.086 / 0.016']],.68,3.88,12,[1.42,5.08,1.2,4.3],{size:15.5,rowH:.51,highlight:2});
 text(s,'加入作者固定效应后拟合度提高，提示作者差异值得考虑；积极表达在M1中就已为负。',.75,6.22,11.85,.5,17.5,C.green,true);
 text(s,'这里比较的是调整后的对数结果，不能把与原始均值的差别单独归因于某一个控制项。',.75,6.72,11.85,.25,12.8,C.muted);
 note(s,'这页写出具体方程。M3以一加点赞数的对数为结果，X是五项文字线索，C是已记录情境，另加作者和日期固定效应。作者效应让比较更多利用同一作者不同帖子间的变化。M1到M2的拟合度由0.563升到0.685，说明作者差异有助于拟合。但积极表达在M1中就已为负，不能把原始均值与M3的差别单独归因于加入作者效应。下一页的系数、区间和显著性都对应M3。','读方程的组成，明确下一页是哪一个模型的推断。');
}
// 9. M3 estimates and the meaning of p versus q.
{
 const s=begin('M3没有保留原始用词优势',4,'回答 RQ2 · 主结果','regression_coefficients.csv M3；summary.json models','表中为M3的作者聚类推断；95%区间与p为原始值，BH q同时考虑五项核心检验。');
 const focal=coef.filter(r=>r.model.startsWith('M3_')).slice(0,5),names=['长度 ln(1+字数)','自律 / 目标','社交 / 互助','积极表达','问号'];
 table(s,['文字特征','系数β','原始95%区间','p','BH q'],focal.map((r,i)=>[names[i],fmt(r.coef),ci(r),fmt(r.p),fmt(r.q_bh_focal)]),.66,1.98,8.3,[2.18,1.03,2.84,1.06,1.19],{size:14.6,rowH:.52,highlight:3});
 text(s,'积极表达：β = −0.086',9.22,2.02,3.42,.77,21,C.orange,true);
 text(s,'原始p = 0.016\nBH q = 0.079',9.22,3.15,3.42,.85,21);
 text(s,'积极表达单项区间不跨0；\n但BH校正后，五项特征\n均未达到5%标准。',9.22,4.41,3.42,1.25,18);
 text(s,'五项文字线索仅增加0.065个百分点R²，联合检验 p = 0.130。',.73,5.78,11.9,.42,18,C.green,true);
 text(s,'原始均值优势没有在调整后的比较中保留；这不足以推出“积极用词降低点赞”。',.73,6.31,11.9,.44,17);
 text(s,'还要核查：负向方向是否依赖缺失正文、极端高赞帖或某一位作者？',.73,6.78,11.9,.23,12.5,C.muted);
 note(s,'这是M3的完整五项结果。积极表达系数负0.086，原始区间不跨零，p为0.016；但五项一起做BH校正后，q为0.079，未达到5%标准。这两个判断并不矛盾：前者看单项，后者考虑同时尝试多项线索。五项新增解释度仅0.065个百分点，联合p为0.130。我们能说原始用词优势没有保留，不能说积极用词导致点赞下降。接着排查这个负向方向是否由缺失、极端值或单个作者主导。','解释p与q的区别、整组新增解释，以及为什么继续做敏感性分析。');
}
// 10. Restored sensitivity evidence, with uncertainty and interpretation.
{
 const s=begin('敏感性分析：三类表达的方向与区间',4,'回答 RQ2 · 敏感性','regression_coefficients.csv；model_fit.csv；dyx第13页','横线为原始95%区间；M3/R1—R3解释ln(1+点赞)，PPML拟合点赞均值，两者尺度不同。');
 const panel=addSensitivityPanels(pres,s,coef,{...C,font:FONT});
 s._m.sensitivityPanels=panel.panels;
 s._m.charts.push(...panel.panels.map(p=>({type:'scatter',data:p.rows,options:{x:p.x,y:p.y,w:p.w,h:p.h}})));
 s._m.text.push(...panel.panels.map(p=>({text:p.title,x:p.x,y:1.79,w:p.w,h:.32,size:16})));
 ['主模型','仅可见正文','去最高1%','作者等权','PPML计数'].forEach((t,i)=>s._m.text.push({text:t,x:.7,y:2.409+i*.376,w:1.08,h:.25,size:11}));
 const specs=[['M3_','M3主模型'],['R1_','仅可见正文'],['R2_','去最高1%'],['R3_','作者等权'],['R4_','PPML']];
 const pos=specs.map(([p])=>coef.find(r=>r.model.startsWith(p)&&r.term==='positive_expression'));
 const ns=specs.map(([p])=>fit.find(r=>r.model.startsWith(p)).n);
 table(s,['积极表达',...specs.map(r=>r[1])],[['系数β',...pos.map(r=>fmt(r.coef))],['原始95%区间',...pos.map(ci)],['原始p',...pos.map(r=>fmt(r.p))],['N',...ns.map(n=>(+n).toLocaleString('en-US'))]],.68,4.86,12,[1.55,2.09,2.09,2.09,2.09,2.09],{size:12.4,rowH:.36});
 text(s,'积极表达方向较一致，但PPML区间跨0；100次逐作者剔除均为负，范围[−0.100, −0.074]。',.75,6.78,11.87,.22,11.8,C.green,true);
 note(s,'把自律、社交和积极表达放在一起看：不同处理下，积极表达方向都为负，自律和社交则没有同样的一致方向。但PPML的积极表达区间跨零，方向一致仍不足以确认稳定负效应。表中保留了具体系数和区间，接着看整篇内容的主题能否补充关联。','用三联区间图呈现敏感性；只口头解释方向与不确定性，不逐格读表。');
}

// 13. Restore topic regression with its actual continuous parameterization.
{
 const s=begin('主题权重能否补充用词以外的点赞关联？',5,'回答 RQ2 · 主题回归','extension_topic_regression.csv；extend_analysis.py；extension_summary.json','同一子样本N=2,470、86位作者；按作者聚类。回归使用连续主题权重，不是主导主题虚拟变量。');
 rect(s,.68,1.83,12,.69,C.light);text(s,'主题模型：M3原有线性项 + Σ θₖwₖ（省去“运动与训练交流”权重作为参照）',.86,2.03,11.63,.35,18,C.green,true);
 const r=topicReg.map(t=>[topicNames[+t.topic],fmt(t.coef),ci(t),fmt(t.p),fmt(t.q_bh)]);
 table(s,['相对训练交流的主题权重','系数θ','原始95%区间','p','BH q'],r,.68,2.92,12,[3.4,1.5,3.8,1.6,1.7],{size:16,rowH:.51,highlight:3});
 text(s,'生活问候权重相对训练交流增加10个百分点时，“1+点赞”的条件几何均值点估计约低1.4%。',.76,5.66,11.83,.48,17);
 text(s,'但其原始p = 0.035、BH q = 0.107；四项主题联合 p = 0.166，尚不能把点估计当成稳定的主题反馈排序。',.76,6.24,11.83,.48,16.5,C.orange,true);
 text(s,'权重范围0–1，系数按100个百分点计；区间未计入主题估计本身的不确定性。',.76,6.86,11.83,.2,11.2,C.muted);
 note(s,'在M3原有项之外增加四项连续主题权重，以训练交流为参照。生活问候相对训练增加十个百分点，点估计对应一加点赞的条件几何均值约低1.4%；但校正后q为0.107，主题联合p为0.166。宽区间和校正结果不足以支持稳定的主题点赞排序。把它与前面的用词结果合起来，才能完成RQ2关于文字和主题关联的回答。','只检验主题与点赞的关联，不复述RQ1的主题份额。');
}
// RQ2 closes after the word and topic tests, before the comment evidence.
{
 const s=begin('RQ2的回答：用词和主题与点赞的关联有多稳',5,'回答 RQ2 · 本题结论','M3、敏感性与连续主题权重回归结果','结果为观察性关联；词典与主题只覆盖部分文字信息，缺少真实曝光等条件。',{dark:true});
 text(s,'原始用词差异同时带着媒体与作者差异。',.78,1.91,11.7,.47,24,C.white,true);
 text(s,'积极表达命中组的图片/视频占比94.9%，未命中组69.1%。M3调整后积极表达系数为−0.086、BH q=0.079；五项文字线索仅新增0.065个百分点R²，联合p=0.130。',.8,2.58,11.65,1.0,18.5,'DFEAE3');
 text(s,'换样本后的方向较一致，主题也没有补出稳定优势。',.78,3.99,11.7,.47,24,C.white,true);
 text(s,'积极表达在多种处理下均为负，但PPML区间跨0；主题权重联合p=0.166。现有记录对这些用词和主题的额外点赞关联，仍缺少足够稳定的证据；这不等于证明文字内容普遍无效。',.8,4.65,11.65,1.04,18.5,'DFEAE3');
 rect(s,.74,6.1,11.96,.67,'295347');text(s,'RQ3转向另一种反馈：评论里，用户说了什么，留言怎样被回应，又由多少人参与？',.94,6.27,11.55,.37,17,'E3ECE6');
 note(s,'RQ2没有找到这些用词和主题具有稳定点赞优势的证据。调整后的负向结果也不能解释成积极表达降低点赞，更不能说文字普遍无效。下面看评论这种更具体的反馈。','给出RQ2回答与解释边界，不重复表中数字。');
}
// 14. Role-specific language and why matching is the next step.
{
 const s=begin('评论长度、词频与发言者角色',6,'回答 RQ3 · 谁说什么','comment_text_features.csv；comment_text_terms.csv；comment_text_summary.json','词类命中率以各角色全部发言为分母，可重叠；角色按所在帖子确定。');
 const labels=['鼓励 / 赞许','感谢','问候','问号'];
 const vals=role=>['encouragement','thanks','greeting','question'].map(f=>+words.find(r=>r.role===role&&r.feature===f).share*100);
 chart(s,[{name:'其他用户（7,192条）',labels,values:vals('其他用户发言')},{name:'帖主（4,403条）',labels,values:vals('帖主发言')}],.64,2.04,7.1,3.85,{barDir:'col',valAxisMaxVal:20,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12.5});
 text(s,'评论较短：中位数6字符',8.2,1.99,4.45,.7,24,C.green,true);
 text(s,'“加油”612条 / 431人\n“谢谢”359条 / 53人',8.2,3.07,4.45,.91,18);
 text(s,'“加油”的使用面更广，\n“谢谢”的重复使用更集中。',8.2,4.38,4.45,.78,18);
 text(s,'按角色看：读者更常赞许，\n帖主更常感谢。',8.2,5.45,4.45,.78,18,C.green,true);
 text(s,'所以下一步把根评论与帖主回复配对：鼓励是否更易被回复，回复里又怎样表达？',.74,6.48,11.9,.46,17.5,C.green,true);
 note(s,'评论中位长度六个字符。“加油”涉及431人，“谢谢”只有53人，前者使用面更广，后者更集中。按角色看，读者更常赞许，帖主更常感谢。但总体词频还不能告诉我们某条留言怎样被回，所以下一步逐条配对。','解释发言人数与角色差异，不逐项读图中比例。');
}
// 16. Restore the analytical question and interpretable differences.
{
 const s=begin('鼓励留言是否更容易得到回应？感谢与回复覆盖不同',6,'回答 RQ3 · 直接配对','supplemental_direct_reply_language.csv','描述性对照，未作显著性或因果检验；未观察到回复，不等于实际没有回复。');
 rect(s,.68,1.74,12,.76,C.light);
 text(s,'配对规则：6,609条外来根评论；从留言发出起7天内，查找明确指向该条留言的帖主直接回复。\n根评论指直接发在帖子下、未指定回复对象的留言；有回复时，只取最早一条。',.85,1.87,11.64,.5,14.5,C.ink);
 text(s,'多少留言观察到7天内直接回复？',.74,2.65,5.8,.36,18.5,C.green,true);text(s,'已回复记录中，最早回复多少含感谢？',7.0,2.65,5.7,.36,18.5,C.orange,true);
 const labels=['鼓励 / 赞许','未命中该词类'];
 chart(s,[{name:'观测回复覆盖',labels,values:[43.4745763,56.2718733]}],.65,3.15,5.8,1.87,{barDir:'bar',valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12,chartColors:[C.green]});
 chart(s,[{name:'首回含感谢',labels,values:[26.705653,6.3829787]}],6.92,3.15,5.8,1.87,{barDir:'bar',valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12,chartColors:[C.orange]});
 text(s,'分母：各组全部外来根评论\n513 / 1,180；3,055 / 5,429',.82,5.13,5.5,.68,13.7,C.muted);text(s,'分母：已观察到直接回复的记录\n137 / 513；195 / 3,055',7.09,5.13,5.5,.68,13.7,C.muted);
 text(s,'鼓励组的观测回复覆盖低12.8个百分点；但在已回复记录中，感谢词占比高20.3个百分点。',.76,5.99,11.85,.43,17.5,C.ink,true);
 text(s,'回复时更常致谢，不等于鼓励更容易被回。作者和留言情境可能不同；接下来看看谁在接话。',.76,6.49,11.85,.48,16.5,C.green);
 note(s,'以6,609条外来根评论为单位，从留言发出起七天内查找帖主的直接回复，有回复时只取最早一条。左图看全部根评论：鼓励组的观测回复比例是43.5%，低于56.3%。右图只看已回复记录：鼓励组首回含感谢为26.7%，高于6.4%。所以，更常感谢不等于更容易被回。这只是描述性对照，接着看回复怎样形成账号之间的往来。','先交代配对规则，再解释两张图的不同分母；不讲线程参与。');
}
// 17. Network construction plus structural interpretation and a next question.
{
 const s=begin('评论关系网络：间接相连广，直接联系仍稀疏',7,'回答 RQ3 · 网络结构','summary.json network；figures/06_comment_network.png','节点为账号；根评论者→帖主，明确回复者→被回复用户；同向多次互动累加为边权。');
 s.addImage({path:path.join(ROOT,'figures/06_comment_network.png'),x:.61,y:2.05,w:6.92,h:6.92*870/1569});
 text(s,'2,932个有边账号 · 4,069条有向边',7.87,1.95,4.8,.78,21,C.green,true);
 text(s,'排除84次自我互动后，11,511次事件合并成有向边；图中省略箭头，金色为样本帖作者。',7.87,3.04,4.8,1.04,16.5);
 text(s,'共同面向帖主留言，就能把许多账号间接连起。忽略方向后，94.4%处于最大连通部分；密度0.0473%，直接往来仍局限于少量账号配对。',7.87,4.32,4.8,1.4,17.5);
 text(s,'这张图回答了账号怎样被连起来。谁在回复谁，下一页再把明确回复单独取出比较。',7.87,6.03,4.8,.8,17,C.green,true);
 note(s,'根评论连到帖主，明确回复连到被回复账号，多次互动累加为边权，并排除自我互动。忽略方向后，94.4%的账号处于最大连通部分，但密度仅0.0473%：许多人通过帖主间接相连，直接往来却很稀疏。下一页再看谁在接话。','说明建边规则与结构结论，账号数和边数留在图旁核对。');
}
// 18. Direction identifies the actual conversation pattern.
{
 const s=begin('回话主要围绕帖主展开，用户彼此回复较少',7,'回答 RQ3 · 谁在接话','extension_comment_roles.csv；summary.json network','分母为4,902次非自我明确回复，排除6,609条根评论；89%不是全部评论的回复率。');
 chart(s,[{name:'明确回复构成',labels:['帖主 → 其他用户','其他用户 → 帖主','其他用户 → 其他用户'],values:[4361/4902*100,444/4902*100,97/4902*100]}],.64,2.07,7.1,3.86,{barDir:'bar',valAxisMaxVal:100,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12.5});
 text(s,'4,361次 · 89.0%',8.22,1.99,4.45,.67,29,C.green,true);
 text(s,'读者面向帖主留言后，明确回话大多由帖主发出。其他用户彼此回复只有97次，占2.0%。',8.22,3.04,4.45,1.3,18);
 text(s,'因此，这批评论更常表现为“向帖主留言—帖主回应”，其他参与者相互回复的份额很小。',8.22,4.73,4.45,1.37,18);
 text(s,'读者留言、帖主回话，会不会在账号之间形成双向连接？接着比较不同建边规则与观察窗口。',.75,6.46,11.85,.49,17.5,C.orange,true);
 note(s,'明确回复中，89%由帖主发给其他用户，用户彼此回复只有2%。这些往来主要是读者面向帖主留言、帖主接话。注意，89%是回复事件构成，不是留言被回率。下一页进一步看这些留言和回话怎样形成双向连接。','用回复方向解释网络，再转入次数和参与人数。');
}
// New from dyx: reciprocity depends on edge rules and observation windows.
{
 const s=begin('留言与回话形成双向连接，互惠率随观察范围变化',7,'回答 RQ3 · 双向往来与窗口','summary.json network；extension_window_networks.csv；dyx第21页','互惠率按有向边计：有反向连接的边数 / 全部有向边数；每边等权，排除自我互动。');
 text(s,'全部互动 49.6%  →  仅明确回复 29.9%',.78,1.89,11.75,.57,27,C.green,true);
 text(s,'读者向帖主留言，帖主再回话给同一用户，就会形成双向连接。\n去掉根评论后互惠率降低，“留言＋回话”是这些双向往来的重要组成。',.79,2.72,11.74,.81,18);
 table(s,['观察窗口','非自我事件','有边账号','有向边','互惠率','前10位接收占比'],windows.map(r=>[r.window==='发帖后7天内'?'各帖发布后7天内':r.window,(+r.events).toLocaleString('en-US'),(+r.nodes).toLocaleString('en-US'),(+r.edges).toLocaleString('en-US'),(+r.reciprocity*100).toFixed(1)+'%',(+r.top10_share*100).toFixed(1)+'%']),.68,3.79,12,[3.05,1.75,1.45,1.45,1.45,2.85],{size:14.8,rowH:.55,highlight:1});
 text(s,'首周的双向连接占比更高，事件接收也略分散；但窗口内的账号和边同时改变，\n不能把差异解释为同一批关系后来变淡。首周从每条帖子的发布时间起算7天。',.79,5.9,11.73,.81,17.5,C.green,true);
 note(s,'全部互动中，49.6%的有向边同时有反向连接；只看明确回复降到29.9%，说明根评论加回话构成了不少双向往来。首周互惠率为74.1%，但账号和边的构成也换了，不能解释成同一批关系后来变淡。接着看高互动量由多少人贡献。','分清边层面的互惠率、事件集中度和两种观察窗口。');
}
// 19. Restore all three peer examples and explain why they matter.
{
 const s=begin('高互动量可能来自接触面广，或少数人反复往来',7,'回答 RQ3 · 次数与参与面','network_nodes.csv；summary.json network','次数为收到的非自我互动事件，人数为不同发送者；“非样本帖作者”不等于从不发帖。');
 text(s,'前10位账号接收了54.0%的互动。判断这种集中意味着什么，需把次数和人数放在一起。',.75,1.84,11.9,.58,18,C.green,true);
 const ids=['U1528','U0948','U0112'];
 table(s,['匿名账号','样本帖作者','接收事件次数','不同发送者','这段记录中的突出形态'],ids.map((id,i)=>{const n=nodes.find(r=>r.user===id);return[id,n.sample_post_author==='True'?'是':'否',(+n.weighted_in_degree).toLocaleString('en-US'),(+n.in_degree).toLocaleString('en-US'),['已有发送者反复留言','收到更多不同账号的留言','与极少数账号集中往来'][i]];}),.68,2.72,12,[1.45,1.55,1.9,1.85,5.25],{size:16.5,rowH:.66});
 text(s,'U1528与U0948接收次数接近，前者只有53位发送者，后者有1,091位。相同“声量”背后，可以是很不一样的参与范围。',.76,5.66,11.85,.55,18,C.ink);
 text(s,'U0112的180次只来自4人。看评论区有多热闹，不能只数留言，还要看有多少人在参与。',.76,6.35,11.85,.57,18,C.green,true);
 note(s,'U1528收到1,378次，来自53人；U0948收到1,275次，却来自1,091人。两者次数接近，参与范围差别很大。U0112的180次只来自4人，也说明高互动量可能是少数人反复出现。次数和不同发送者人数要一起看，才能判断这些留言由多广的参与面构成。','用两个主要账号解释次数与人数；第三例点到即可，直接收束RQ3。');
}
// RQ3 closes the entire response story; no joint mixed-RQ conclusion follows.
{
 const s=begin('RQ3的回答：评论主要怎样形成往来',7,'回答 RQ3 · 本题结论','评论语言、直接配对、双向关系、窗口比较与参与人数结果','评论与网络均基于已采集记录；未观察到回复不等于实际没有回复。',{dark:true});
 text(s,'读者更常鼓励，帖主更常感谢；逐条配对后，含义更清楚。',.8,1.9,11.65,.46,23,C.white,true);
 text(s,'直接配对进一步说明：鼓励组已回复记录中的感谢占比更高，但观测回复覆盖反而较低。回复怎样表达，与多少留言得到回应，需要分开判断。',.82,2.53,11.6,.88,18.5,'DFEAE3');
 text(s,'这些发言主要围绕帖主组织，热闹的来源也不一样。',.8,3.73,11.65,.46,23,C.white,true);
 text(s,'89%的明确回复由帖主发给其他用户，用户相互回复仅2%。接收次数接近的账号，可以来自53人或1,091人；所以留言量既可能反映广泛参与，也可能是已有发送者反复出现。',.82,4.36,11.6,1.01,18.5,'DFEAE3');
 rect(s,.74,5.89,11.96,.9,'295347');text(s,'互惠率随建边规则和观察窗口变化；评论多或双向连接多，都还需要结合不同参与者人数判断。',.95,6.07,11.52,.55,17,'E3ECE6');
 note(s,'更常感谢不等于更容易被回。回话主要围绕帖主，互惠率随规则和窗口变化；高留言量也可能来自少数人，因此还要看参与人数。','串起语言、回复、双向关系与参与广度。');
}
// 22. Restore a separate limitations section and explain its consequences.
{
 const s=begin('研究局限：哪些判断还不能由这批记录回答',8,'解释范围与后续改进','原报告§9.3—9.4；数据与模型口径核查','下一步是补齐记录和统一观察窗口；若检验表达或回复做法的效果，需要另行设计实验。');
 table(s,['限制','它怎样影响结论','下一步需要什么'],[
  ['100位作者，抽样机制不明','不能把样本内容比例和回复结构直接推广到全Keep','更清楚的抽样框与作者覆盖'],
  ['正文、评论覆盖不全','主题与网络代表不同子样本；未采到不等于未发生','补齐正文、评论、图像和视频内容'],
  ['曝光、粉丝与采集时点缺失','累计点赞仍受未观测差异影响，固定效应不等于因果识别','统一发帖后7天，并记录实际曝光'],
  ['词典与主题只是内容的部分表征','不能据用词判断情绪；主题区间未计入模型估计不确定性','语义复核、重复抽样与独立验证']
 ],.68,1.96,12,[3.06,5.18,3.76],{size:15.5,rowH:.83});
 text(s,'后续先统一观察窗口，完整记录内容、参与人数和实际回复，再检验具体做法能否改变反馈。',.76,6.43,11.85,.58,18,C.green,true);
 note(s,'这些结论来自100位作者，正文和评论覆盖也不完整，不能推广到全平台。缺少曝光和统一观察时点，回归仍然是关联。后续需要补齐记录、统一观察窗口，再验证具体做法能否改变反馈。','只讲样本与覆盖、观察性关联以及对应改进。');
}

// Credit remains after the 21 research slides in this shorter version.
{
 const s=begin('成员分工 / Credit',0,'','用户确认的实际分工','成员分工 · Credit',{dark:true,clean:true});
 s._m.kind='credit';s._m.chapterName='成员分工';s._m.subsection='Credit';
 text(s,'成员分工 / Credit',.78,.78,11.8,.7,35,C.white,true);
 rect(s,.75,2.22,5.76,3.94,'295347');rect(s,6.82,2.22,5.76,3.94,'295347');
 text(s,'陈霖',1.03,2.61,5.18,.6,31,C.white,true);
 text(s,'问题的提出\n数据清洗\nRQ1：内容与点赞的分布',1.03,3.57,5.18,1.98,21,'DFEAE3',false,{paraSpaceAfterPt:13});
 text(s,'董依心（dyx）',7.1,2.61,5.18,.6,31,C.white,true);
 text(s,'RQ2：文字、主题与点赞的关联\nRQ3：评论中的回应与参与',7.1,3.57,5.18,1.98,20.5,'DFEAE3',false,{paraSpaceAfterPt:13});
 note(s,'陈霖负责问题提出、清洗和RQ1，董依心负责RQ2与RQ3。谢谢大家。','按确认分工署名。');
}

async function main(){
 if(M.length!==MAIN)throw Error('Expected 22 research slides and one Credit slide');
 const expected={RQ1:[4,5,6,7],RQ2:[8,9,10,11,12,13,14],RQ3:[15,16,17,18,19,20,21]};
 for(const [q,pages] of Object.entries(expected))if(JSON.stringify(M.filter(s=>s.question===q).map(s=>s.page))!==JSON.stringify(pages))throw Error('Noncontiguous or mixed answer block: '+q);
 await pres.writeFile({fileName:OUT+'.pptx'});
 const z=await JSZip.loadAsync(fs.readFileSync(OUT+'.pptx'));const repairs=[];
 const forestRepairs=await postprocessSensitivityCharts(z);
 fs.writeFileSync(path.join(QA,'sensitivity_chart_checks.json'),JSON.stringify(forestRepairs,null,2));
 for(const n of Object.keys(z.files).filter(n=>/^ppt\/charts\/chart\d+\.xml$/.test(n))){
  let x=await z.file(n).async('string');const axes=new Set([...x.matchAll(/<c:(?:catAx|valAx|serAx)\b[^>]*>([\s\S]*?)<\/c:(?:catAx|valAx|serAx)>/g)].map(m=>m[1].match(/<c:axId\s+val="([^"]+)"\s*\/>/)[1]));let removed=0;
  x=x.replace(/<c:barChart\b[^>]*>[\s\S]*?<\/c:barChart>/g,b=>b.replace(/<c:axId\s+val="([^"]+)"\s*\/>/g,(all,id)=>{if(axes.has(id))return all;removed++;return '';}));z.file(n,x);repairs.push({part:n,removed});
 }
 for(const n of Object.keys(z.files).filter(n=>/^ppt\/slides\/_rels\/slide\d+\.xml\.rels$/.test(n)))z.file(n,(await z.file(n).async('string')).replace(/Target="\/ppt\/charts\//g,'Target="../charts/'));
 fs.writeFileSync(OUT+'.pptx',await z.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
 fs.writeFileSync(path.join(QA,'chart_axis_repairs.json'),JSON.stringify(repairs,null,2));
 fs.writeFileSync(path.join(QA,'slides_manifest.json'),JSON.stringify(M,null,2));
 const clock=s=>`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;let elapsed=0;
 const scripts=M.map(s=>{const a=elapsed;elapsed+=s.seconds;return `第${s.page}页｜${s.chapter ? '第'+s.chapter+'章 ' : ''}${s.chapterName}${s.rq ? '｜'+s.rq : ''}\n${s.title}\n${clock(a)}—${clock(elapsed)}；讲述预算${s.seconds}秒\n\n${s.speech}\n\n讲述重点：${s.focus}\n来源：${s.source}`;}).join('\n\n');
 const blocks=['RQ1','RQ2','RQ3'].map(question=>({question,pages:M.filter(s=>s.question===question).map(s=>s.page)}));
 const timing={rq_blocks:blocks,main_slides:MAIN,appendix_slides:0,hidden_slides:0,chapters:CH.map((title,i)=>({number:i+1,title,pages:M.filter(s=>s.chapter===i+1).map(s=>s.page)})),speech_seconds:elapsed,transition_seconds:30,target_seconds:elapsed+30,short_seconds:SHORT.reduce((a,b)=>a+b,0)+30,narration_characters:M.reduce((a,s)=>a+s.speech.length,0),note:'23页dyx合并版；讲述预算11分04秒，另留30秒转场，总目标11分34秒，距12分钟余26秒。表格和窗口比较供核对，口头解释关键发现；时长以排练为准。'};
 fs.writeFileSync(path.join(QA,'timing_plan.json'),JSON.stringify(timing,null,2));
 const reflection='基于main的22页12分钟版，合入dyx提交1e751bd的研究意义、评论覆盖与北京时间口径、三词类敏感性区间图、互惠与首周窗口分析及文字排版改进。新增1页互惠分析，共23页；仍按RQ1、RQ2、RQ3连续回答，不恢复文字均值的跨RQ重复。旧文件全部保留。纠正“更多感谢”为“已回复时更常含感谢”，维持观察性关联与不同分母的边界。';
 const mapping=M.map(s=>`${s.basePage?'22页版第'+s.basePage+'页':'新增互惠分析'} / dyx第${s.dyxPage}页 → 本版第${s.page}页｜${s.title}`).join('\n');
 fs.writeFileSync(OUT+'_逐页讲稿与修改说明.txt',`Keep社区内容表达与互动反馈｜12分钟dyx合并版\n\n22页研究汇报＋1页成员分工（Credit），无答疑或隐藏页。\n讲述预算${clock(elapsed)}，另留30秒转场，总目标${clock(elapsed+30)}；12分钟上限余${720-elapsed-30}秒。时长需排练校准。\n讲稿已写入各页备注。统计表供看与核对，不逐行念。\n\n本次修改\n${reflection}\n\n新旧页码对照（分别标注22页版与dyx版；原答疑清单仍对应25页完整稿）\n${mapping}\n25页完整稿第4页→本版第3页；第17页→本版第16页；第21页→本版第20页；RQ3总结第23页→本版第21页。旧首回速度时序页仍只留在旧版与答疑清单中；本版新增的是互惠与窗口比较。\n\n逐页讲稿\n${scripts}`);
 const files=[path.join(ROOT,'Keep社区内容表达与互动反馈_12分钟版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_12分钟版.pdf'),path.join(ROOT,'Keep社区内容表达与互动反馈_最终汇报版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_最终汇报版.pdf'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分题讲述版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分题讲述版.pdf'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分析增强版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分析增强版.pdf'),...['Keep社区内容表达与互动反馈_10-15分钟正文整合版.pptx','Keep社区内容表达与互动反馈_10-15分钟正文整合版.pdf','results/summary.json','results/regression_coefficients.csv','results/extension_topic_regression.csv','results/post_features.csv'].map(f=>path.join(ROOT,f))];
 const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
 fs.writeFileSync(path.join(QA,'protected_inputs.json'),JSON.stringify(files.filter(file=>fs.existsSync(file)).map(file=>({file,sha256:sha(file)})),null,2));
 console.log(JSON.stringify({file:OUT+'.pptx',slides:M.length,nativeCharts:M.reduce((a,s)=>a+s.charts.length,0),timing},null,2));
}
main().catch(e=>{console.error(e);process.exit(1);});
