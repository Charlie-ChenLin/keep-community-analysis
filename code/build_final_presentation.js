/* Source-backed revision using the teammate's eight chapters.
 * Run with NODE_PATH pointing to an installation of pptxgenjs and jszip.
 * Existing analyses and earlier presentations are read only.
 */
const pptxgen=require('pptxgenjs'),JSZip=require('jszip');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..');
const QA=path.join(ROOT,'validation/slides_rq_final');
const OUT=path.join(ROOT,'Keep社区内容表达与互动反馈_最终汇报版');
fs.mkdirSync(QA,{recursive:true});
const pres=new pptxgen();pres.layout='LAYOUT_WIDE';
pres.author='陈霖、董依心';pres.company='社交媒体网络分析课程小组';
pres.title='Keep社区内容表达与互动反馈分析';pres.subject='八章结构与RQ逐项分析；全部为正文';pres.lang='zh-CN';
const FONT='Arial Unicode MS';pres.theme={headFontFace:FONT,bodyFontFace:FONT,lang:'zh-CN'};
const C={ink:'20332F',green:'245C4F',deep:'173F36',muted:'65756F',light:'EDF4F0',pale:'F6F8F7',line:'DFE6E2',orange:'B97339',paleOrange:'F8F0E8',gray:'AAB8B0',white:'FFFFFF'};
const CH=['研究背景、意义与研究问题','数据来源、清洗与分析方法','数据覆盖与描述统计','文字表达与点赞的关联','帖子主题与点赞的关联','评论的主要内容','评论区的网络结构','研究结论与局限'];
const MAIN=25,M=[];
const TIMES=[15,35,25,25,35,35,30,30,35,30,40,45,35,45,35,30,25,35,30,25,30,25,35,30,10];
const SHORT=[10,30,20,20,25,25,20,25,25,25,30,35,25,35,25,25,20,30,25,20,25,20,25,25,10];
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
 s._m={page:M.length+1,title,chapter:ch,chapterName:ch?CH[ch-1]:'封面',subsection:sub,question,rq,source,foot,appendix:false,text:[],charts:[],speech:'',seconds:TIMES[M.length],shortSeconds:SHORT[M.length]};M.push(s._m);
 if(!clean){text(s,question?`${question}  ${headings[question]}`:ch===8?'共同局限与后续改进':'研究设计与数据',.58,.3,8.8,.3,13,dark?'C5D9D0':C.green,true);text(s,sub,9.12,.3,3.62,.3,11,dark?'C5D9D0':C.muted,false,{align:'right'});text(s,title,.58,.88,12.15,.67,28,dark?C.white:C.ink,true);}
 text(s,foot||source,.58,7.09,11.36,.22,9,dark?'BDD3C8':C.muted);
 text(s,`${String(M.length).padStart(2,'0')} / ${MAIN}`,11.99,7.07,.77,.25,10,dark?'BDD3C8':C.muted,false,{align:'right'});
 return s;
}
function note(s,speech,focus){s._m.speech=speech;s._m.focus=focus;s.addNotes(`讲述预算${s._m.seconds}秒；压缩版${s._m.shortSeconds}秒\n\n${speech}\n\n讲述重点：${focus}\n\n来源：${s._m.source}`);}
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
 text(s,'哪些内容获得反馈，评论又如何形成往来？',.8,4.12,11.7,.65,24,'DCEAE1');
 text(s,'陈霖  ·  董依心',.8,5.96,9,.45,21,C.white);
 note(s,'我们围绕三个问题汇报：帖子和点赞怎样分布，文字与主题是否对应反馈差异，以及评论由谁回应、怎样往来。按三个问题依次展开，每一部分讲完即收束回答。','提出研究对象与三条问题线。');
}
// 2. Research design remains the first body slide.
{
 const s=begin('研究背景、问题与预期',1,'RQ1 · RQ2 · RQ3','原报告§1；同伴版研究设计页','预期是待检验的可能解释，后文按相同RQ编号逐项回答。');
 text(s,'健身社区里，什么内容受到关注，人们又怎样交流？',.7,1.78,11.9,.5,25,C.green,true);
 text(s,'Keep既承载训练与打卡，也包含经验和生活分享。点赞是可见反馈，\n评论则记录了谁在留言、谁在接话；理解反馈需要把内容和参与者一起看。',.72,2.43,11.8,.69,17.5);
 text(s,'三个具体问题',.87,3.3,5.6,.33,16,C.green,true);text(s,'对应预期：可能出现的结果',7.02,3.3,5.4,.33,16,C.green,true);
 const rows=[['RQ1  样本主要呈现什么内容，点赞怎样分布？','媒体反馈可能不同，高赞帖可能拉高均值；\n正文也可能同时包含运动与生活分享。'],['RQ2  文字线索与主题是否与点赞有关？','自律、积极表达或提问可能对应较高点赞；\n调整作者与情境后，这些差异也可能减弱。'],['RQ3  评论说什么，谁回应谁，参与面多广？','读者可能更多鼓励，帖主更多回应；\n高评论量也可能来自少数人的反复往来。']];
 rows.forEach((r,i)=>{const y=3.83+i*.97;rect(s,.7,y,11.95,.89,i===1?C.pale:C.light);text(s,r[0],.87,y+.17,5.85,.56,17.5,C.ink,true);text(s,r[1],7.02,y+.12,5.4,.65,16.5);});
 note(s,'总问题是，健身社区里什么内容受到关注，人们怎样交流。Keep既有训练打卡，也有生活分享，因此不能只看某个词或总评论量。我们拆为三个问题：RQ1描述样本内容和点赞分布；RQ2检验文字、主题与点赞的关联；RQ3看评论内容、回复方向和参与范围。右栏是可能的解释，后文通过数据判断是否成立；页眉会持续标出正在回答的RQ。','总问题→三项RQ→对应预期，不提前把预期当结论。');
}
// 3. Data and cleaning.
{
 const s=begin('数据来源与清洗',2,'支撑 RQ1 / RQ2 / RQ3','summary.json；原报告§2—3','课程100位作者样本；帖子发表于2020年11—12月（UTC），评论最晚至2021年8月。');
 stat(s,'9,532','帖子 · 100位作者',.72,1.83);stat(s,'11,595','去重后评论',4.78,1.83);stat(s,'1,323','有采集到评论的帖子',8.85,1.83);
 table(s,['核查发现','处理方式','分析含义'],[['1,916行重复评论','按评论ID去重，无字段冲突','避免同一发言被重复计入'],['3,984帖缺可用正文','保留；文字计数设0并另作标记','不能把缺失当作真实无文字'],['8,286帖点赞高于记录浏览数','使用累计点赞，不计算点赞率','不解释为曝光转化效率'] ],.68,3.35,12,[3.5,4,4.5],{size:15.5,rowH:.62});
 text(s,'先区分“记录没有采到”和“用户没有发生”，再比较反馈。',.75,6.29,11.8,.5,20,C.green,true);
 note(s,'样本有9,532帖、100位作者，评论去重后11,595条，只覆盖1,323帖。重复评论删重，正文缺失保留并标记。由于大量点赞高于记录浏览数，我们只分析累计点赞。这里最重要的判断是：没有采到正文或评论，不等于用户没有写或没有收到评论。','规模与三项处理，避免逐格念表。');
}
// 5. Coverage and its implications.
{
 const s=begin('先明确哪些帖子和作者有可分析的正文',3,'回答 RQ1','extension_coverage_media.csv；extension_summary.json','可见正文按原始正文有可见字符界定；主题分析另用清理后的有效正文。');
 chart(s,[{name:'可见正文覆盖率',labels:['图片','视频','纯文字','无媒体'],values:[75.9758204,89.1350211,100,.1203369]}],.65,2.0,7.25,3.99,{barDir:'col',valAxisMaxVal:110,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:14});
 para(s,'文本分析代表哪些记录？','5,548帖有可见正文，清理后5,414帖非空；文本分析对记录较完整的媒体形式更充分。',8.42,1.98,4.17);
 para(s,'作者覆盖也不均匀','作者正文覆盖率中位数84.3%，5位作者完全没有可见正文。主题结果主要代表正文记录较完整的作者。',8.42,4.02,4.17);
 text(s,'后续主题只针对2,470条有效正文，不能直接当作9,532帖或全平台的内容比例。',.73,6.41,11.9,.48,17,C.green,true);
 note(s,'RQ1先确认我们实际看到了哪些内容。正文覆盖不是均匀的：图片约76%、视频89%，无媒体帖几乎没有可见正文。作者正文覆盖率中位数84.3%，还有五位作者完全没有可见正文。所以后面的内容主题代表正文较完整的记录，不能当成所有帖子的内容比例。在这个范围内，先看媒体和点赞怎样分布，再看有效正文主要在写什么。','先定描述范围，再进入媒体与点赞分布，不展开评论或回归。');
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
 const s=begin('帖子正文主题主要包括运动和生活',3,'回答 RQ1','extension_topics.csv；extension_summary.json；topic_labels.json','TF-IDF + NMF，主题数预先固定为5；名称依据词项与正文确定，不参考点赞。');
 const order=[2,4,3,0,1],labs=order.map(i=>topicNames[i]);
 chart(s,[{name:'主导主题占比',labels:labs,values:order.map(i=>+themes[i].post_equal_share*100)}],.64,2.0,7.15,4.25,{barDir:'bar',valAxisMaxVal:60,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12.5});
 text(s,'2,470帖 · 86位作者',8.28,1.96,4.4,.43,22,C.green,true);
 text(s,'训练交流：运动、减脂、训练、拉伸\n生活问候：人生、生活、早安、美好',8.28,2.74,4.39,1.02,17.5);
 text(s,'前两类合计88.5%。这批有效正文不仅讨论如何训练，也经常写感受、生活和问候，不能把健身社区里的文字都当成运动成绩记录。',8.28,4.1,4.39,1.58,18);
 text(s,'占比按每帖权重最大的主题归类。同一作者可写多个主题，内容量大也可能是某些人写得多。',.74,6.4,11.9,.56,17,C.green,true);
 note(s,'有效正文提取了五类主题，训练交流占52.7%，生活感悟和问候占35.8%，合计88.5%。所以这批Keep文字不只有打卡和运动成绩，也有大量日常表达。这里按每帖权重最大的主题统计篇幅，一人可以贡献很多帖。要判断某种内容是否普遍，还要看它是不是被少数高产作者放大。','先解释两大主题的真实内容，再引出作者等权。');
}
// 12. Author composition as an explanation of a frequent theme.
{
 const s=begin('常见内容，也可能是少数人的高频记录',3,'回答 RQ1','supplemental_topic_author_weighting.csv；extension_topics.csv','两组沿用同一主题分类；作者等权先计算每人的主题比例，再对86位作者平均。');
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
 note(s,'RQ1的回答是两点。反馈上，图片和视频均值较高，整体点赞有长尾，中位数25比均值37更接近一般帖子的位置。内容上，训练和生活共同构成主要篇幅，作者等权后格局仍在；部分小主题却是少数作者持续记录放大的。分布已经说明媒体和作者值得留意。RQ2进一步问，把这些条件纳入比较后，文字和主题与点赞的关联还能保留多少。','在本题结束时给完整描述性回答，再转入关联问题。');
}
// 4. Definitions appear before all feature comparisons.
{
 const s=begin('怎样把文字表达放进点赞比较',4,'回答 RQ2 · 变量定义','text_dictionary.json；analyze.py；extend_analysis.py','文字词表只识别字面线索，不是情绪量表；特征可重叠。');
 table(s,['五项文字变量','定义与例子'],[['正文长度 L','ln(1+清理后字符数)'],['自律 / 目标 D','坚持、自律、目标、第N天等词表或模式'],['社交 / 互助 S','大家、小伙伴、谢谢、一起等词表'],['积极表达 P','开心、快乐、喜欢、哈哈等词表'],['问号 Q','全角或半角问号，出现记1']],.68,1.94,6.6,[2,4.6],{size:15.5,rowH:.59});
 text(s,'除长度外，命中记1；一帖可同时命中多个词类。',.75,5.72,6.5,.6,14.5,C.muted);
 para(s,'比较什么结果？','点赞分布有长尾，因此模型采用 ln(1+点赞数)，减少少量极端高赞对比较的影响。',7.75,2.02,4.85);
 para(s,'怎样判断文字的额外关联？','先看命中与未命中的均值及媒体构成，再同时调整作者、日期和发布情境，检查原始差异是否保留。',7.75,4.25,4.85);
 text(s,'用词检验之后，再加入RQ1已经识别的主题权重，检查整篇内容是否补充点赞关联。',7.75,6.12,4.85,.7,16,C.green,true);
 note(s,'进入RQ2，先定义文字线索。长度取一加字数的对数，自律、社交、积极表达和问号按固定规则命中记一，维度可以重叠。结果变量采用一加点赞的对数，对应RQ1看到的长尾。我们先比较原始均值及媒体构成，再调整作者和发布情境；用词检验完成后，再加入RQ1已经识别的主题权重，检验整篇内容能否补充关联。','本页只建立RQ2的变量、结果和比较顺序。');
}
// 7. Raw means followed by actual composition evidence, not a rhetorical jump.
{
 const s=begin('分组均值较高，但文字与媒体构成混在一起',4,'回答 RQ2 · 原始比较','text_features_summary.csv；既有post_features媒体构成汇总','变量已在第9页定义；组别与特征可重叠，分组均值尚未调整作者和发布情境。');
 chart(s,[{name:'命中',labels:['自律 / 目标','社交 / 互助','积极表达','问号'],values:features.map(r=>+r.raw_mean_likes_hit)},{name:'未命中',labels:['自律 / 目标','社交 / 互助','积极表达','问号'],values:features.map(r=>+r.raw_mean_likes_nohit)}],.63,2.0,7.2,3.8,{barDir:'col',chartColors:[C.green,'AFBCB5'],valAxisMaxVal:130});
 text(s,'积极表达组的进一步比较',8.28,1.91,4.4,.4,20,C.green,true);
 table(s,['组别','帖数','图片/视频'],[['命中','574','94.9%'],['未命中','8,958','69.1%']],8.25,2.58,4.43,[1.43,1.35,1.65],{size:14.5,rowH:.57});
 text(s,'57.29 vs 35.76 个赞，\n同时伴随媒体构成差异。\n命中组分布于64位作者，\n未命中组覆盖100位作者。',8.3,4.69,4.34,1.5,17.5);
 text(s,'下一步：同时控制媒体、作者和日期，比较这些用词是否仍有额外关联。',.73,6.45,11.9,.5,18,C.orange,true);
 note(s,'四类表达的命中组原始均值都更高。进一步看积极表达，命中组57.29个赞，未命中35.76，但图片或视频占比也从69.1%升到94.9%。两组涉及的作者范围同样不同。这是一个实际的构成差异，不只是抽象地担心混杂。下一步需要把文字、媒体、作者与日期一起放入模型，追问文字线索是否还提供额外解释。','先给媒体构成证据，再自然引出下一页控制模型。');
}
// 8. Explicit model equation and successive specifications.
{
 const s=begin('用作者与日期固定效应，进一步改善比较',4,'回答 RQ2 · 回归设定','analyze.py formula()/models()；model_fit.csv','主分析为OLS；N=9,532、100位作者，标准误按作者聚类，五项核心系数采用BH校正。');
 rect(s,.68,1.86,12,.94,C.light);
 text(s,'M3：ln(1 + 点赞数) = β′X + γ′C + α作者 + δ日期 + ε',.89,2.12,11.58,.47,23,C.green,true);
 text(s,'X：长度、自律、社交、积极、问号。C：正文可用、话题、表情数、课程分享，以及媒体、业务类型、时段。',.75,3.03,11.85,.6,15.5);
 table(s,['模型','调整范围','R²','积极表达系数 / 原始p'],[['M1','X + C + 已记录作者属性','0.563','−0.050 / 0.285'],['M2','X + C + 作者固定效应','0.685','−0.087 / 0.016'],['M3 主模型','X + C + 作者、日期固定效应','0.688','−0.086 / 0.016']],.68,3.88,12,[1.42,5.08,1.2,4.3],{size:15.5,rowH:.51,highlight:2});
 text(s,'加入作者固定效应后拟合度提高，提示作者差异值得考虑；积极表达在M1中就已为负。',.75,6.22,11.85,.5,17.5,C.green,true);
 text(s,'这里比较的是调整后的对数结果，不能把与原始均值的差别单独归因于某一个控制项。',.75,6.72,11.85,.25,12.8,C.muted);
 note(s,'这页写出具体方程。M3以一加点赞数的对数为结果，X是五项文字线索，C是已记录情境，另加作者和日期固定效应。作者效应让比较更多利用同一作者不同帖子间的变化。M1到M2的拟合度由0.563升到0.685，说明作者差异有助于拟合。但积极表达在M1中就已为负，不能把原始均值与M3的差别单独归因于加入作者效应。下一页的系数、区间和显著性都对应M3。','读方程的组成，明确下一页是哪一个模型的推断。');
}
// 9. M3 estimates and the meaning of p versus q.
{
 const s=begin('M3没有保留原始用词优势，单项线索也需要校正',4,'回答 RQ2 · 主结果','regression_coefficients.csv M3；summary.json models','表中为M3的作者聚类推断；95%区间与p为原始值，BH q同时考虑五项核心检验。');
 const focal=coef.filter(r=>r.model.startsWith('M3_')).slice(0,5),names=['长度 ln(1+字数)','自律 / 目标','社交 / 互助','积极表达','问号'];
 table(s,['文字特征','系数β','原始95%区间','p','BH q'],focal.map((r,i)=>[names[i],fmt(r.coef),ci(r),fmt(r.p),fmt(r.q_bh_focal)]),.66,1.98,8.3,[2.18,1.03,2.84,1.06,1.19],{size:14.6,rowH:.52,highlight:3});
 text(s,'积极表达：β = −0.086',9.22,2.02,3.42,.77,21,C.orange,true);
 text(s,'原始p = 0.016\nBH q = 0.079',9.22,3.15,3.42,.85,21);
 text(s,'单项区间不跨0，\n但五项一起校正后，\n证据未达到5%标准。',9.22,4.41,3.42,1.25,18);
 text(s,'五项文字线索仅增加0.065个百分点R²，联合检验 p = 0.130。',.73,5.78,11.9,.42,18,C.green,true);
 text(s,'原始均值优势没有在调整后的比较中保留；这不足以推出“积极用词降低点赞”。',.73,6.31,11.9,.44,17);
 text(s,'还要核查：负向方向是否依赖缺失正文、极端高赞帖或某一位作者？',.73,6.78,11.9,.23,12.5,C.muted);
 note(s,'这是M3的完整五项结果。积极表达系数负0.086，原始区间不跨零，p为0.016；但五项一起做BH校正后，q为0.079，未达到5%标准。这两个判断并不矛盾：前者看单项，后者考虑同时尝试多项线索。五项新增解释度仅0.065个百分点，联合p为0.130。我们能说原始用词优势没有保留，不能说积极用词导致点赞下降。接着排查这个负向方向是否由缺失、极端值或单个作者主导。','解释p与q的区别、整组新增解释，以及为什么继续做敏感性分析。');
}
// 10. Restored sensitivity evidence, with uncertainty and interpretation.
{
 const s=begin('换样本和模型后，积极表达的方向是否改变？',4,'回答 RQ2 · 敏感性','regression_coefficients.csv；model_fit.csv；extension_author_influence_summary.csv','聚焦积极表达；区间和p为各设定原始值，不代替M3的BH主分析结论。');
 const specs=[['M3_','M3主模型'],['R1_','仅可见正文'],['R2_','去最高1%点赞'],['R3_','作者等权'],['R4_','PPML计数模型']];
 table(s,['设定','N','系数','原始95%区间','p'],specs.map(([prefix,n])=>{const r=coef.find(r=>r.model.startsWith(prefix)&&r.term==='positive_expression'),f=fit.find(r=>r.model.startsWith(prefix));return[n,Number(f.n).toLocaleString('en-US'),fmt(r.coef),ci(r),fmt(r.p)];}),.68,2.02,8.5,[2.4,1.1,1,2.85,1.15],{size:14.5,rowH:.54,highlight:4});
 para(s,'方向不依赖一种样本处理','可见正文、去高赞、作者等权后均为负；100次逐作者剔除也全部为负。',9.55,2.05,3.1,{size:16.5});
 para(s,'计数尺度上仍不精确','PPML区间跨0，不能把方向一致升级成已验证的稳定负效应。',9.55,4.12,3.1,{color:C.orange,size:16.5});
 text(s,'逐作者剔除系数范围：[−0.100, −0.074]。PPML拟合 E[点赞 | 条件] = exp(线性项)。',.74,6.15,11.9,.4,15.5,C.muted);
 text(s,'沿用RQ1已经识别的主题权重，检验它们能否补充指定用词以外的点赞关联。',.74,6.65,11.9,.33,16.5,C.green,true);
 note(s,'可见正文、去高赞、作者等权后的积极表达系数均为负，逐作者剔除也全部为负，方向不完全依赖一种样本处理。但PPML直接拟合点赞计数，区间跨零；敏感性检验也不能替代主模型的BH判断。词典仍只抓住指定字眼。现在沿用RQ1已经识别的主题权重，直接问整篇内容是否能补充点赞关联。','从用词的敏感性检查转到主题关联，不返回内容分布。');
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
 note(s,'RQ2从原始用词均值出发，先看到媒体和作者构成差异，再用M3调整比较。积极表达的原始高赞优势没有保留，但BH校正后也不足以确认稳定负向差异。敏感性样本方向虽一致，PPML区间仍跨零；加入主题权重后，联合检验也未给出明确的额外关联。合起来，现有证据不足以支持这些词语和主题有稳定点赞优势，不能扩大成文字普遍无效。RQ3接下来研究评论这种更具体的反馈。','把用词、敏感性和主题作为同一关联问题的连续证据。');
}
// 14. Role-specific language and why matching is the next step.
{
 const s=begin('评论长度、词频与发言者角色',6,'回答 RQ3 · 谁说什么','comment_text_features.csv；comment_text_terms.csv；comment_text_summary.json','词类命中率以各角色全部发言为分母，可重叠；角色按所在帖子确定。');
 const labels=['鼓励 / 赞许','感谢','问候','问号'];
 const vals=role=>['encouragement','thanks','greeting','question'].map(f=>+words.find(r=>r.role===role&&r.feature===f).share*100);
 chart(s,[{name:'其他用户（7,192条）',labels,values:vals('其他用户发言')},{name:'帖主（4,403条）',labels,values:vals('帖主发言')}],.64,2.04,7.1,3.85,{barDir:'col',valAxisMaxVal:20,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12.5});
 text(s,'评论长度中位数：6字符',8.2,1.99,4.45,.7,24,C.green,true);
 text(s,'“加油”612条 / 431人\n“谢谢”359条 / 53人',8.2,3.07,4.45,.91,18);
 text(s,'“加油”的使用面更广，“谢谢”的重复使用更集中。再按角色看，读者更常赞许，帖主更常感谢；只看词频，会把参与广度和重复回话混在一起。',8.2,4.42,4.45,1.78,17.5);
 text(s,'所以下一步把根评论与帖主回复配对：鼓励是否更易被回复，回复里又怎样表达？',.74,6.48,11.9,.46,17.5,C.green,true);
 note(s,'评论中位长度只有六个字符。“加油”有612条、431人，“谢谢”359条却只有53人：前者使用面更广，后者重复使用更集中。再按角色看，读者更常赞许，帖主更常感谢。只看词频，会把参与广度和重复回话混在一起。但这些总体分布还没定位某条留言的回应，所以下一步按回复对象配对，分别看留言有没有被回，以及回复里写了什么。','解释人数怎样改变对高频词的理解，再引出具体配对。');
}
// 15. Distinguish direct response and thread participation in the body.
{
 const s=begin('先分清：直接回这条留言，还是在留言串里接话',6,'回答 RQ3 · 回复口径','supplemental_direct_reply_language.csv；extension_summary.json','两个比例来自同一批6,609条根评论，但统计的回复范围与时间不同。');
 text(s,'根评论：其他用户直接发在帖子下、没有指定回复对象的留言。',.74,1.84,11.9,.45,18);
 [{x:.73,title:'直接回复根评论',target:'这条根评论',time:'根评论发出后7天内',pct:'54.0%',n:'3,568 / 6,609条',color:C.green,fill:C.light},{x:6.98,title:'帖主参与留言串',target:'根评论或同串其他留言',time:'不限7天，查看已采集的整串',pct:'57.0%',n:'3,770 / 6,609条',color:C.orange,fill:C.paleOrange}].forEach(a=>{
  text(s,a.title,a.x,2.57,5.6,.4,22,a.color,true);rect(s,a.x,3.27,5.6,.78,a.fill);text(s,'帖主',a.x+.18,3.48,.85,.39,18,C.ink,true);line(s,a.x+1.14,3.65,.72,0,a.color,1.6,true);text(s,a.target,a.x+2.02,3.48,3.39,.39,16.5);
  text(s,a.time,a.x+.03,4.41,5.54,.42,17,a.color,true);text(s,a.pct,a.x+.03,5.12,2.8,.68,34,a.color,true);text(s,a.n,a.x+2.85,5.35,2.7,.4,16);
 });
 text(s,'后面的鼓励留言比较采用左侧规则：每条根评论只取最早观测到的帖主直接回复。',.76,6.23,11.85,.47,18,C.green,true);
 text(s,'未观察到回复，不等于实际没有回复；57%与54%的差额也不能直接解释为“回复别人”的比例。',.76,6.78,11.85,.22,12.5,C.muted);
 note(s,'对6,609条外来根评论，我们分别统计直接回复和线程参与。直接回复必须明确指向这条根评论，且在七天内，观察到54%。线程参与不限七天，只要帖主在同一留言串回过话就算，比例57%。两种时间范围不同，不能直接相减解释。下一页采用左侧较严格规则，每条根评论只看最早一条帖主直接回复。','简短交代两种口径，明确下一页沿用哪一种。');
}
// 16. Restore the analytical question and interpretable differences.
{
 const s=begin('鼓励留言是否更容易得到回应？感谢与回复覆盖不同',6,'回答 RQ3 · 直接配对','supplemental_direct_reply_language.csv','这是描述性组间对照；现有分析未对该差异作显著性或因果检验。');
 text(s,'多少留言观察到7天内直接回复？',.74,1.89,5.8,.4,18.5,C.green,true);text(s,'已回复记录中，最早回复多少含感谢？',7.0,1.89,5.7,.4,18.5,C.orange,true);
 const labels=['鼓励 / 赞许','未命中该词类'];
 chart(s,[{name:'观测回复覆盖',labels,values:[43.4745763,56.2718733]}],.65,2.48,5.8,2.51,{barDir:'bar',valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12,chartColors:[C.green]});
 chart(s,[{name:'首回含感谢',labels,values:[26.705653,6.3829787]}],6.92,2.48,5.8,2.51,{barDir:'bar',valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12,chartColors:[C.orange]});
 text(s,'分母：全部根评论\n513 / 1,180；3,055 / 5,429',.82,5.13,5.5,.68,13.7,C.muted);text(s,'分母：已观察到直接回复的记录\n137 / 513；195 / 3,055',7.09,5.13,5.5,.68,13.7,C.muted);
 text(s,'鼓励组的观测回复覆盖低12.8个百分点；但在已回复记录中，感谢词占比高20.3个百分点。',.76,5.99,11.85,.43,17.5,C.ink,true);
 text(s,'这批记录支持“回复时更常致谢”，不能据此说“鼓励更容易被回”。作者和留言情境可能不同，接着看这些回复是怎样组织起来的。',.76,6.49,11.85,.48,16.5,C.green);
 note(s,'先看左图，鼓励组观察到七天内直接回复的比例是43.5%，低于未命中组56.3%，相差12.8个百分点。右图只看已经有回复的记录，鼓励组的首回含感谢为26.7%，高于6.4%，相差20.3个百分点。因此感谢更常见，不能当成更容易被回复的证据。这是描述性对照，作者、情境和记录覆盖仍可能不同。下面把回复放回账号关系，看看是否形成了参与者之间的广泛交谈。','明确两个问题、两种分母和两项差值，再给结论。');
}
// 17. Network construction plus structural interpretation and a next question.
{
 const s=begin('评论关系网络：间接相连广，直接联系仍稀疏',7,'回答 RQ3 · 网络结构','summary.json network；figures/06_comment_network.png','节点为账号；根评论者→帖主，明确回复者→被回复用户；同向多次互动累加为边权。');
 s.addImage({path:path.join(ROOT,'figures/06_comment_network.png'),x:.61,y:2.05,w:6.92,h:6.92*870/1569});
 text(s,'2,932个有边账号 · 4,069条有向边',7.87,1.95,4.8,.78,21,C.green,true);
 text(s,'排除84次自我互动后，11,511次事件合并成有向边；图中省略箭头，金色为样本帖作者。',7.87,3.04,4.8,1.04,16.5);
 text(s,'共同面向帖主留言，就能把许多账号间接连起。忽略方向后，94.4%处于最大连通部分；密度0.0473%，直接往来仍局限于少量账号配对。',7.87,4.32,4.8,1.4,17.5);
 text(s,'这张图回答了账号怎样被连起来。谁在回复谁，下一页再把明确回复单独取出比较。',7.87,6.03,4.8,.8,17,C.green,true);
 note(s,'网络把根评论连到帖主，把明确回复连到被回复账号，同向多次互动累加次数。排除自我互动后，11,511次事件形成4,069条边、2,932个账号。共同面向帖主留言，就能把许多账号间接连起：忽略方向后94.4%处于最大连通部分。但密度只有0.0473%，直接往来仍局限于少量账号配对。这说明账号怎样连在一起，谁在回复谁则要把明确回复单独取出比较。','说足网络的结构结论，再限定它尚未回答的回复方向。');
}
// 18. Direction identifies the actual conversation pattern.
{
 const s=begin('回话主要围绕帖主展开，用户彼此回复较少',7,'回答 RQ3 · 谁在接话','extension_comment_roles.csv；summary.json network','分母为4,902次非自我明确回复，排除6,609条根评论；89%不是全部评论的回复率。');
 chart(s,[{name:'明确回复构成',labels:['帖主 → 其他用户','其他用户 → 帖主','其他用户 → 其他用户'],values:[4361/4902*100,444/4902*100,97/4902*100]}],.64,2.07,7.1,3.86,{barDir:'bar',valAxisMaxVal:100,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:12.5});
 text(s,'4,361次 · 89.0%',8.22,1.99,4.45,.67,29,C.green,true);
 text(s,'读者面向帖主留言后，明确回话大多由帖主发出。其他用户彼此回复只有97次，占2.0%。',8.22,3.04,4.45,1.3,18);
 text(s,'因此，这批评论更常表现为“向帖主留言—帖主回应”，其他参与者相互回复的份额很小。',8.22,4.73,4.45,1.37,18);
 text(s,'还需要分清：围绕一个账号有很多发言，究竟来自更多人，还是已有发送者反复出现？',.75,6.46,11.85,.49,17.5,C.orange,true);
 note(s,'明确回复中，帖主回复其他用户占89%，其他用户彼此回复只有2%。这让前页网络有了具体解释：常见活动是读者向帖主留言，再由帖主回应，横向接话较少。这里89%是回复事件的构成，不是所有留言的被回率。接着我们再问，围绕一个账号出现很多发言，是否就意味着参与面很广。','用回复方向解释上一页网络，再引出次数与人数。');
}
// 19. Restore all three peer examples and explain why they matter.
{
 const s=begin('高互动量可能来自接触面广，或少数人反复往来',7,'回答 RQ3 · 次数与参与面','network_nodes.csv；summary.json network','次数为收到的非自我互动事件，人数为不同发送者；“非样本帖作者”不等于从不发帖。');
 text(s,'前10位账号接收了54.0%的互动。判断这种集中意味着什么，需把次数和人数放在一起。',.75,1.84,11.9,.58,18,C.green,true);
 const ids=['U1528','U0948','U0112'];
 table(s,['匿名账号','样本帖作者','接收事件次数','不同发送者','这段记录中的突出形态'],ids.map((id,i)=>{const n=nodes.find(r=>r.user===id);return[id,n.sample_post_author==='True'?'是':'否',(+n.weighted_in_degree).toLocaleString('en-US'),(+n.in_degree).toLocaleString('en-US'),['已有发送者反复留言','收到更多不同账号的留言','与极少数账号集中往来'][i]];}),.68,2.72,12,[1.45,1.55,1.9,1.85,5.25],{size:16.5,rowH:.66});
 text(s,'U1528与U0948接收次数接近，前者只有53位发送者，后者有1,091位。相同“声量”背后，可以是很不一样的参与范围。',.76,5.66,11.85,.55,18,C.ink);
 text(s,'U0112的180次只来自4人。总次数不能替代参与广度；它们也没有区分发生早晚，接着看留言集中在发帖后哪个时段。',.76,6.35,11.85,.57,18,C.green,true);
 note(s,'U1528收到1,378次，只有53位发送者；U0948收到1,275次，却来自1,091人。前者的高量更多包含已有发送者反复出现，后者收到更广泛的参与。U0112的180次只来自4人，也说明总次数不能替代人数。这些次数没有区分留言发生的早晚，接着看它们集中在发帖后哪个时段，以及首回速度遗漏了哪些记录。','从接收总量转入留言发生与回应的时间。');
}
// 20. Timing and the conditional nature of the first response statistic.
{
 const s=begin('评论多发生在早期，首回速度只描述已接话的线程',7,'回答 RQ3 · 互动时序','extension_summary.json comments；extension_comment_timing.csv','64.5%与82.2%的分母为11,595条评论，从发帖起算；首回间隔从根评论起算。');
 chart(s,[{name:'累计评论占比',labels:['发帖后24小时内','发帖后7天内'],values:[64.5,82.2]}],.64,2.05,7.05,3.62,{barDir:'bar',valAxisMaxVal:100,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:13.5});
 text(s,'2.05小时',8.18,1.99,4.45,.69,32,C.green,true);text(s,'帖主已参与的线程中，\n根评论至首回的中位间隔',8.18,2.89,4.45,.79,18);
 text(s,'近三分之二的评论出现在前24小时，互动集中于早期。但2.05小时排除了未观察到帖主参与的线程，不能代表所有留言的等待时间。',8.18,4.05,4.45,1.95,18);
 text(s,'评价回应是否及时，应先分清“有没有回”和“回得多快”；只看速度会漏掉未观察到回应的留言。',.75,6.42,11.85,.55,18,C.green,true);
 note(s,'64.5%的评论在发帖后24小时内，82.2%在七天内，互动集中于发布早期。已观察到帖主参与的线程里，根评论到首回的中位间隔是2.05小时。但它排除了未观察到帖主参与的线程，不能代表全部留言的等待。评价回应是否及时，应该先分清有没有回、再看回得多快；只看首回速度，会漏掉没有观察到回应的那部分留言。','把时序解释落到速度统计遗漏了谁。');
}
// RQ3 closes the entire response story; no joint mixed-RQ conclusion follows.
{
 const s=begin('RQ3的回答：评论主要怎样形成往来',7,'回答 RQ3 · 本题结论','评论语言、直接配对、账号网络、参与人数与时序结果','评论与网络均基于已采集记录；未观察到回复不等于实际没有回复。',{dark:true});
 text(s,'读者更常鼓励，帖主更常感谢；逐条配对后，含义更清楚。',.8,1.9,11.65,.46,23,C.white,true);
 text(s,'直接配对进一步说明：鼓励组已回复记录中的感谢占比更高，但观测回复覆盖反而较低。回复怎样表达，与多少留言得到回应，需要分开判断。',.82,2.53,11.6,.88,18.5,'DFEAE3');
 text(s,'这些发言主要围绕帖主组织，热闹的来源也不一样。',.8,3.73,11.65,.46,23,C.white,true);
 text(s,'89%的明确回复由帖主发给其他用户，用户相互回复仅2%。接收次数接近的账号，可以来自53人或1,091人；所以留言量既可能反映广泛参与，也可能是已有发送者反复出现。',.82,4.36,11.6,1.01,18.5,'DFEAE3');
 rect(s,.74,5.89,11.96,.9,'295347');text(s,'64.5%的评论在发帖后24小时内出现。判断回应时，应先看有没有观察到回复，再看回得多快；2.05小时的首回中位数只描述已接话线程。',.95,6.07,11.52,.55,17,'E3ECE6');
 note(s,'RQ3把语言、逐条回应和账号关系接在一起。读者更常鼓励，帖主更常感谢，但配对后可见，回复更常感谢不代表鼓励更容易被回。网络中的回话主要由帖主承担；同样多的发言又可以来自完全不同的人数，次数和参与范围要分开。最后，评论大多发生在发布早期，回应速度却只统计已接话线程。这样才能同时理解谁在说、谁在回、多少人参与，以及哪些留言没有进入速度统计。','只收束RQ3的回应过程，不再回头重复RQ1与RQ2。');
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
 note(s,'最后明确这批记录回答不到哪里。样本只有100位作者且抽样机制不明，不能外推全平台；正文和评论覆盖不全，各分析代表的范围不同。缺少真实曝光和统一采集时点，也意味着回归仍然是关联。词典和主题还只抓住部分内容。后续应先统一发帖后七天的观察窗口，补齐内容、独立参与者与回复记录；如果要判断具体表达或回复做法的效果，需要另外设计验证。','说明限制怎样影响判断，再给出与限制对应的改进。');
}

// Credit is the only new content after the accepted 24 research slides.
{
 const s=begin('成员分工 / Credit',0,'','用户确认的实际分工','成员分工 · Credit',{dark:true,clean:true});
 s._m.kind='credit';s._m.chapterName='成员分工';s._m.subsection='Credit';
 text(s,'成员分工 / Credit',.78,.78,11.8,.7,35,C.white,true);
 rect(s,.75,2.22,5.76,3.94,'295347');rect(s,6.82,2.22,5.76,3.94,'295347');
 text(s,'陈霖',1.03,2.61,5.18,.6,31,C.white,true);
 text(s,'问题的提出\n数据清洗\nRQ1：内容与点赞的分布',1.03,3.57,5.18,1.98,21,'DFEAE3',false,{paraSpaceAfterPt:13});
 text(s,'董依心（dyx）',7.1,2.61,5.18,.6,31,C.white,true);
 text(s,'RQ2：文字、主题与点赞的关联\nRQ3：评论中的回应与参与',7.1,3.57,5.18,1.98,20.5,'DFEAE3',false,{paraSpaceAfterPt:13});
 note(s,'本次分工：陈霖负责问题提出、数据清洗和RQ1的回答；董依心负责RQ2与RQ3的回答。','按实际分工署名，不增加未经确认的贡献。');
}

async function main(){
 if(M.length!==MAIN)throw Error('Expected 24 research slides and one Credit slide');
 const expected={RQ1:[4,5,6,7,8],RQ2:[9,10,11,12,13,14,15],RQ3:[16,17,18,19,20,21,22,23]};
 for(const [q,pages] of Object.entries(expected))if(JSON.stringify(M.filter(s=>s.question===q).map(s=>s.page))!==JSON.stringify(pages))throw Error('Noncontiguous or mixed answer block: '+q);
 await pres.writeFile({fileName:OUT+'.pptx'});
 const z=await JSZip.loadAsync(fs.readFileSync(OUT+'.pptx'));const repairs=[];
 for(const n of Object.keys(z.files).filter(n=>/^ppt\/charts\/chart\d+\.xml$/.test(n))){
  let x=await z.file(n).async('string');const axes=new Set([...x.matchAll(/<c:(?:catAx|valAx|serAx)\b[^>]*>([\s\S]*?)<\/c:(?:catAx|valAx|serAx)>/g)].map(m=>m[1].match(/<c:axId\s+val="([^"]+)"\s*\/>/)[1]));let removed=0;
  x=x.replace(/<c:barChart\b[^>]*>[\s\S]*?<\/c:barChart>/g,b=>b.replace(/<c:axId\s+val="([^"]+)"\s*\/>/g,(all,id)=>{if(axes.has(id))return all;removed++;return '';}));z.file(n,x);repairs.push({part:n,removed});
 }
 for(const n of Object.keys(z.files).filter(n=>/^ppt\/slides\/_rels\/slide\d+\.xml\.rels$/.test(n)))z.file(n,(await z.file(n).async('string')).replace(/Target="\/ppt\/charts\//g,'Target="../charts/'));
 fs.writeFileSync(OUT+'.pptx',await z.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
 fs.writeFileSync(path.join(QA,'chart_axis_repairs.json'),JSON.stringify(repairs,null,2));
 fs.writeFileSync(path.join(QA,'slides_manifest.json'),JSON.stringify(M,null,2));
 const clock=s=>`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;let elapsed=0;
 const scripts=M.map(s=>{const a=elapsed;elapsed+=s.seconds;return `第${s.page}页｜第${s.chapter}章 ${s.chapterName}｜${s.rq}\n${s.title}\n${clock(a)}—${clock(elapsed)}；讲述预算${s.seconds}秒\n\n${s.speech}\n\n讲述重点：${s.focus}\n来源：${s.source}`;}).join('\n\n');
 const blocks=['RQ1','RQ2','RQ3'].map(question=>({question,pages:M.filter(s=>s.question===question).map(s=>s.page)}));
 const timing={rq_blocks:blocks,main_slides:MAIN,appendix_slides:0,hidden_slides:0,chapters:CH.map((title,i)=>({number:i+1,title,pages:M.filter(s=>s.chapter===i+1).map(s=>s.page)})),speech_seconds:elapsed,transition_seconds:30,target_seconds:elapsed+30,short_seconds:SHORT.reduce((a,b)=>a+b,0)+30,narration_characters:M.reduce((a,s)=>a+s.speech.length,0),note:'每页以半分钟左右为基础；方程与主要推断页可稍长。表格保留供看与核对，口头只解释关键比较。时间需排练校准。'};
 fs.writeFileSync(path.join(QA,'timing_plan.json'),JSON.stringify(timing,null,2));
 const reflection='在已确认的24页分题讲述版后，仅追加成员分工页：陈霖负责问题提出、数据清洗与RQ1；董依心（dyx）负责RQ2与RQ3。前24页只更新总页码。答疑材料另成独立PDF。';
 fs.writeFileSync(OUT+'_逐页讲稿与修改说明.txt',`Keep社区内容表达与互动反馈｜RQ分题讲述版\n\n24页研究汇报＋1页成员分工（Credit）。前三个RQ的内容与顺序保持不变，无答疑或隐藏页。\n标准讲述预算${clock(elapsed)}，另留30秒转场，总目标${clock(elapsed+30)}。\n讲稿已写入各页备注。\n\n这次的反思与修改\n${reflection}\n\n${scripts}`);
 const files=[path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分题讲述版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分题讲述版.pdf'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分析增强版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_RQ分析增强版.pdf'),...['Keep社区内容表达与互动反馈_10-15分钟正文整合版.pptx','Keep社区内容表达与互动反馈_10-15分钟正文整合版.pdf','results/summary.json','results/regression_coefficients.csv','results/extension_topic_regression.csv','results/post_features.csv'].map(f=>path.join(ROOT,f))];
 const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
 fs.writeFileSync(path.join(QA,'protected_inputs.json'),JSON.stringify(files.filter(file=>fs.existsSync(file)).map(file=>({file,sha256:sha(file)})),null,2));
 console.log(JSON.stringify({file:OUT+'.pptx',slides:M.length,nativeCharts:M.reduce((a,s)=>a+s.charts.length,0),timing},null,2));
}
main().catch(e=>{console.error(e);process.exit(1);});
