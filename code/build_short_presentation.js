/* New presentation derived from the layout-optimized Phase 2 report.
 * Dependencies: pptxgenjs (set NODE_PATH if installed outside this project).
 * This script never rewrites the source report or the previous presentation.
 */
const pptxgen = require('pptxgenjs');
const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, '演示文稿_Phase2_15-20分钟精简版');
const QA = path.join(ROOT, 'validation', 'slides_insight_short');
fs.mkdirSync(QA, { recursive: true });

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Keep 社区研究小组';
pptx.subject = '基于排版优化版分析报告的章节化中文汇报';
pptx.title = 'Keep社区内容表达与互动反馈';
pptx.company = '课程小组项目';
pptx.lang = 'zh-CN';
pptx.theme = { headFontFace: 'Arial Unicode MS', bodyFontFace: 'Arial Unicode MS', lang: 'zh-CN' };
const C = { ink:'252338', purple:'6550B8', deep:'292044', lilac:'EFECF8', muted:'6C697D', green:'288475', paleGreen:'E8F4F0', orange:'B66A35', paleOrange:'F8EEE5', line:'DDD9E7', white:'FFFFFF', grey:'F5F5F8' };
const W=13.333333, H=7.5, FONT='Arial Unicode MS';
const chapters = [
 ['研究设计与样本','报告第1—3章'], ['文字表达与点赞','报告第4章'],
 ['主题与作者构成','报告第5章'], ['评论语言与直接承接','报告第6章'],
 ['评论网络与互动形态','报告第7章'], ['综合结论与建议','报告第8—9章'],
];
const manifest=[];
const MAIN_COUNT=18;
let section='导读'; pptx.addSection({title:section});
function txt(s,text,x,y,w,h,size=18,color=C.ink,bold=false,extra={}) {
 s.addText(text,{x,y,w,h,fontFace:FONT,fontSize:size,color,bold,margin:0,breakLine:false,
  valign:'top',align:'left',wrap:true,paraSpaceAfterPt:6,lang:'zh-CN',...extra});
 s._audit.text.push({text:typeof text==='string'?text:JSON.stringify(text),x,y,w,h,size});
}
function box(s,x,y,w,h,fill=C.lilac,rad=true,line=null) {
 s.addShape(rad?pptx.ShapeType.roundRect:pptx.ShapeType.rect,{x,y,w,h,rectRadius:.12,radius:.12,
  fill:{color:fill},line:{color:line||fill,width:line?.7:0},radius:.12});
}
function line(s,x1,y1,x2,y2,color=C.line,width=1.3,arrow=false){
 s.addShape(pptx.ShapeType.line,{x:Math.min(x1,x2),y:Math.min(y1,y2),w:Math.abs(x2-x1),h:Math.abs(y2-y1),
  flipH:x2<x1,flipV:y2<y1,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});
}
function circle(s,x,y,d,fill,text='',color=C.white,size=20){
 s.addShape(pptx.ShapeType.ellipse,{x,y,w:d,h:d,fill:{color:fill},line:{color:fill,width:0}});
 if(text)txt(s,text,x,y+.02,d,d-.02,size,color,true,{align:'center',valign:'mid'});
}
function network(s,x,y,scale=1,dark=false){
 const points=[[1.5,1.25,.8],[0,.05,.46],[2.9,.1,.5],[.2,2.55,.6],[3.1,2.6,.48],[3.4,1.35,.35],[1.6,3.15,.4]];
 for(let i=1;i<points.length;i++)line(s,x+(points[i][0]+points[i][2]/2)*scale,y+(points[i][1]+points[i][2]/2)*scale,x+1.9*scale,y+1.65*scale,dark?'6D608D':'C2B8E0',2);
 points.forEach((p,i)=>circle(s,x+p[0]*scale,y+p[1]*scale,p[2]*scale,i===0?C.green:(dark?'8775C5':'B3A3DA')));
}
function begin(title,ch,source='',options={}){
 const s=pptx.addSlide({sectionTitle:section});
 s.background={color:options.dark?C.deep:C.white};
 s._audit={page:manifest.length+1,title,chapter:ch,source,text:[],charts:[],notes:'',seconds:0};
 manifest.push(s._audit);
 if(!options.clean){
  txt(s,`KEEP 社区研究  /  ${ch?String(ch).padStart(2,'0')+'  '+chapters[ch-1][0]:'汇报导读'}`,.55,.28,11.9,.25,11.5,options.dark?'C8BFDF':C.muted);
  txt(s,title,.55,.83,12.15,.69,options.titleSize||30,options.dark?C.white:C.ink,true);
 }
 txt(s,source||'基于《分析报告_Phase2_中文新版_insight_v2_修改版_排版优化》',.55,7.08,11.7,.22,9.5,options.dark?'B6ADC9':C.muted);
 txt(s,String(manifest.length).padStart(2,'0')+' / '+MAIN_COUNT,11.98,7.05,.81,.25,11,options.dark?'D5CEE4':C.muted,false,{align:'right'});
 return s;
}
function note(s,body,seconds=0){
 s._audit.seconds=seconds;
 s._audit.speech=body;
 const n='【建议 '+seconds+' 秒】\n'+body;
 s.addNotes(n);s._audit.notes=n;
}
function startChapter(n){section=String(n).padStart(2,'0')+' '+chapters[n-1][0];pptx.addSection({title:section});}

function para(s,label,body,x,y,w,h=1.03){
 txt(s,label,x,y,w,.28,15,C.purple,true);
 txt(s,body,x,y+.37,w,h-.33,17.5,C.ink,false,{paraSpaceAfterPt:3});
}
function narrative(s,items,x=8.45,y=1.82,w=4.28,totalH=3.85){
 const gap=.19,h=(totalH-gap*(items.length-1))/items.length;
 items.forEach((p,i)=>para(s,p[0],p[1],x,y+i*(h+gap),w,h));
}
function takeaway(s,label,text,y=6.12){
 box(s,.55,y,12.23,.64,C.lilac);
 txt(s,label,.76,y+.16,1.02,.28,14,C.purple,true);
 txt(s,text,1.86,y+.15,10.65,.37,17,C.deep,true);
}
function stat(s,num,label,x,y,w=3.7,fill=C.lilac){
 box(s,x,y,w,1.19,fill);
 txt(s,num,x+.2,y+.12,w-.4,.55,32,C.purple,true);
 txt(s,label,x+.2,y+.76,w-.4,.28,13.5,C.muted);
}
function table(s,headers,rows,x,y,w,widths,size=15.5,rowH=.6){
 const data=[headers.map(text=>({text,options:{bold:true,color:C.white,fill:C.purple}})),
 ...rows.map((row,i)=>row.map(text=>({text:String(text),options:{fill:i%2?C.white:C.grey,color:C.ink}})))];
 s.addTable(data,{x,y,w,colW:widths,rowH,fontFace:FONT,fontSize:size,border:{type:'solid',color:C.white,pt:2},
  margin:[.09,.12,.09,.12],color:C.ink,breakLine:false,vertAnchor:'mid',autoPage:false,
  bold:false,paraSpaceAfterPt:0});
 s._audit.text.push({text:headers.join(' | ')+'\n'+rows.map(r=>r.join(' | ')).join('\n'),x,y,w,h:rowH*(rows.length+1),size});
}
function chart(s,type,data,x,y,w,h,options={}){
 const o={x,y,w,h,fontFace:FONT,showBorder:false,showTitle:false,showLegend:data.length>1,
  legendFontFace:FONT,legendFontSize:12,legendPos:'b',
  catAxisLabelFontFace:FONT,catAxisLabelFontSize:12,valAxisLabelFontFace:FONT,valAxisLabelFontSize:11,
  catAxisLabelColor:C.muted,valAxisLabelColor:C.muted,valGridLine:{color:'E8E5EE',width:.6},
  catGridLine:{style:'none'},chartColors:data.length===1?[C.purple]:[C.purple,C.green,'A697CE','8BB8AB','BC906D'],
  showValue:true,dataLabelColor:C.ink,dataLabelFormatCode:'0.0',dataLabelPosition:'outEnd',dataLabelBkgrdColor:C.white,
  dataLabelFormatCodeSourceLinked:false,dataLabelFontSize:13,
  showCatName:false,showSerName:false,showMarker:false,showShadow:false,
  catAxisLineShow:false,valAxisLineShow:false,
  valAxisMinVal:0,gapSizePct:70,showLegendKey:false,
  ...options};
 s.addChart(type,data,o); s._audit.charts.push({type,data,options:o});
}

// Every slide below is part of the timed talk. No appendix or hidden slides.
{
 const s=begin('Keep社区内容表达与互动反馈',0,'课程小组汇报 · 基于排版优化版分析报告',{dark:true,clean:true});
 txt(s,'KEEP COMMUNITY',.65,.63,8,.4,18,'BAAED3',true);
 txt(s,'内容怎样获得反馈，\n评论怎样形成往来',.65,1.55,8.9,1.65,35,C.white,true);
 txt(s,'Keep社区内容表达与互动反馈分析',.69,3.51,8.9,.55,25,'E5DDF0');
 txt(s,'从帖子文字、作者构成与评论关系，\n理解这批社区记录中的反馈差异与交流方式。',.69,4.38,8.5,.92,19,'CEC4DF');
 txt(s,'两条分析线：表达与点赞的关联，以及评论中的留言与回应。',.69,6.05,11.9,.47,18,C.white,true);
 network(s,9.55,2.5,.7,true);
 note(s,'本次汇报研究Keep社区中的内容表达与互动反馈。我们主要回答两个问题：帖子怎样写，与点赞有什么关联；评论区中的留言，又是怎样被接住和组织起来的。接下来会沿着内容与互动两条主线，介绍分析方法和核心发现。',25);
}
{
 const s=begin('汇报路线：从内容比较走向评论往来',0,'六章依次对应报告第1—3、4、5、6、7、8—9章');
 const subs=['数据清洗与比较范围','原始差异与调整后关联','内容产量与作者平均构成','语言角色与直接回复配对','回话角色、参与人数与时序','证据支持什么，下一步验证什么'];
 chapters.forEach((c,i)=>{
  const x=.55+(i%3)*4.17,y=1.85+Math.floor(i/3)*1.86;
  box(s,x,y,3.9,1.57,i<3?C.lilac:C.paleGreen);
  circle(s,x+.18,y+.2,.43,i<3?C.purple:C.green,String(i+1).padStart(2,'0'),C.white,13);
  txt(s,c[0],x+.77,y+.23,2.92,.38,19,C.ink,true);
  txt(s,subs[i],x+.2,y+.88,3.5,.47,16,C.ink);
 });
 takeaway(s,'研究问题','先看哪些内容获得反馈，再看评论由谁发起、向谁集中，以及如何得到回应。');
 note(s,'汇报分为六章。第一章说明样本和比较范围；第二章分析具体文字表达与点赞；第三章进一步看整篇正文的主题。第四章从评论语言追踪到直接回复，第五章把这些发言放进用户关系网络。最后整合结果，提出建议与研究边界。这样的顺序也是实际分析过程：先核清数据，再比较内容，最后理解互动。',45);
}

startChapter(1);
{
 const s=begin('数据与覆盖：先明确哪些记录能够比较',1,'源报告 §2.1、§3.1 · PDF第4、6页；发帖日期与时段统一为北京时间');
 stat(s,'9,532帖','来自100位课程样本作者',.55,1.82,3.88);
 stat(s,'11,595条','评论去重后规模；原始13,511行',4.72,1.82,3.88);
 stat(s,'1,323帖','有已采集评论，其余覆盖未知',8.89,1.82,3.89);
 table(s,['核查发现','采用的处理','对分析的影响'],[
  ['3,984帖没有可用正文','保留帖子，文本计数设0，另加正文可用标记','主回归使用全部帖子；主题另筛有效正文'],
  ['8,286帖点赞大于记录浏览数','不计算点赞率，使用累计点赞数','不能直接比较曝光转化效率'],
  ['正文与评论记录各有缺口','5,548帖可见正文，清理后非空5,414帖','未采到评论不等于没有评论'],
 ],.55,3.33,12.23,[3.25,4.55,4.43],14.5,.60);
 takeaway(s,'比较范围','帖子发表于2020年11—12月（UTC）；抽样机制与统一采集时点未提供。');
 note(s,'分析使用100位作者的9,532条帖子。评论原有13,511行，按评论ID删除1,916行重复记录后，剩下11,595条，分布在1,323帖下。这里有两个关键处理：没有可用正文的帖子仍保留，另记录正文是否可用；由于大量帖子点赞高于记录浏览数，我们使用累计点赞，而不计算点赞率。可见正文与清理后非空正文也要区分，分别是5,548和5,414帖。其余帖子没有采到评论，不能当成零评论。后面的内容与互动结论，都只针对这批实际记录。',60);
}
{
 const s=begin('比较背景：点赞长尾，媒体与作者也有差异',1,'源报告 §3.2、附录A.5 · PDF第7、25页');
 chart(s,pptx.ChartType.bar,[{name:'平均点赞',labels:['图片','视频','纯文字','无媒体'],values:[51.03,48.05,7.94,3.91]}],.55,1.88,7.25,3.78,{barDir:'col',showLegend:false,valAxisMaxVal:60,dataLabelFormatCode:'0.00',catAxisLabelFontSize:14});
 narrative(s,[
  ['少量高赞拉高平均水平','平均点赞37.05，中位数25，最高5,126；描述普通帖子时，也需要看中位数。'],
  ['媒体形式的反馈基准不同','图片和视频帖平均约51和48个赞，纯文字与无媒体帖约8和4个，差距明显。'],
  ['高产作者会被反复计入','作者发帖数中位数66帖，最多783帖；其表达习惯会在按帖统计中出现更多次。'],
 ]);
 takeaway(s,'分析起点','讨论文字差异时，必须把媒体形式、作者和已记录的发布情境一起考虑。');
 note(s,'点赞分布具有明显长尾：均值37.05，中位数25，最高超过五千。图中不同媒体形式的基准也很不一样，图片和视频帖平均约五十个赞，纯文字和无媒体帖只有个位数。此外，一位高产作者最多发布783帖，表达习惯会被重复计入。因此，某种措辞对应更多点赞，可能同时反映媒体和作者差异。下一章会通过逐步控制，改变比较条件。',45);
}

startChapter(2);
{
 const s=begin('分析过程：文字编码后，逐步控制作者与日期',2,'源报告 §2.2—2.3、附录A.1 · PDF第5、23页；因变量为ln(1+点赞数)');
 const vars=[['正文长度','ln(1+清理后字数)'],['自律或目标','坚持、目标、打卡'],['社交或互助','大家、一起、谢谢'],['积极表达','开心、喜欢、哈哈'],['问号','半角或全角问号']];
 vars.forEach((a,i)=>{const x=.55+i*2.5;box(s,x,1.83,2.23,1.07,C.lilac);txt(s,a[0],x+.14,2.0,1.95,.35,18,C.purple,true);txt(s,a[1],x+.14,2.5,1.95,.25,12.5,C.ink);});
 const models=[['M1','基础关联','控制媒体形式、业务类型、时段和作者属性'],['M2','加作者固定效应','扣除作者间不随帖子变化的差别，利用作者内变化'],['M3','再加日期固定效应','扣除各日期共有差别，作为主模型']];
 models.forEach((a,i)=>{const x=.55+i*4.17;box(s,x,3.39,3.9,1.94,i===2?C.paleGreen:C.grey);circle(s,x+.18,3.59,.48,i===2?C.green:C.purple,a[0],C.white,14);txt(s,a[1],x+.85,3.66,2.85,.35,19,C.ink,true);txt(s,a[2],x+.18,4.35,3.54,.72,17,C.ink);});
 txt(s,'固定词表命中记1，维度可重叠；标准误按作者聚类，五项核心系数做BH多重比较校正。',.66,5.6,12,.43,16,C.ink);
 takeaway(s,'方法含义','词典识别字面线索；固定效应改善可比性，实际曝光和完整内容仍未观测。');
 note(s,'我们先把正文清理，再编码五项特征：正文长度，自律目标词、社交互助词、积极表达词和问号。词表命中记为一，不同维度可以重叠，但这些只是字面线索，不能直接当作心理状态。然后依次估计三个模型。M1控制媒体形式等已记录条件；M2加入作者固定效应，扣除作者之间相对稳定的差别；M3再控制发帖日期，作为主模型。因变量是ln一加点赞数，推断时按作者聚类，并做五项多重比较校正。模型仍缺少真实曝光和完整内容，所以估计的是调整后的关联。',75);
}
{
 const s=begin('核心变化：原始表达优势在调整后发生反转',2,'源报告 §4.1—4.2 · PDF第8—9页；各特征可以重叠');
 chart(s,pptx.ChartType.bar,[
  {name:'命中该表达',labels:['自律或目标','社交或互助','积极表达','问号'],values:[63.67,89.96,57.29,111.15]},
  {name:'未命中',labels:['自律或目标','社交或互助','积极表达','问号'],values:[34.36,36.16,35.76,36.07]},
 ],.55,1.88,7.35,3.97,{barDir:'col',grouping:'clustered',valAxisMaxVal:130,dataLabelFormatCode:'0.0',catAxisLabelFontSize:12});
 narrative(s,[
  ['原始分组：四类均有优势','积极表达帖平均57.29个赞，未命中帖35.76个；其他三类也对应更高原始均值。'],
  ['调整后：积极表达转为负向','控制作者、日期和已记录情境后，“1+点赞数”的条件几何均值约低8.2%。'],
  ['改变的是比较对象','组间差异混合着作者和内容构成；作者内比较进一步追问同一作者何时这样写。'],
 ]);
 takeaway(s,'解释线索','反转提示应结合作者与发布情境理解，不能解释成积极用词本身降低点赞。');
 note(s,'先看左图，四类表达的命中帖都具有原始平均点赞优势。以积极表达为例，是57.29对35.76。但控制作者、日期和其他已记录条件后，积极表达的关联转为负向，对应一加点赞数的条件几何均值约低8.2%。这里改变的是比较对象：原始分组把不同作者和内容放在一起；调整后的模型更多利用同一作者不同帖子的变化。高反馈作者可能较常使用积极词，同一作者也可能在不同情境里这样表达。反转因此是理解作者与内容构成的线索，还不能说积极用词降低点赞。',75);
}
{
 const s=begin('结果强度：方向有线索，稳定关键词效果尚无证据',2,'源报告 §4.2—4.3、附录A.1—A.2 · PDF第9—10、23—24页；表中为原始95%区间');
 table(s,['核心文字线索','M3系数','原始95%置信区间','BH q值'],[
  ['正文长度 ln(1+字数)','0.028','[-0.008, 0.064]','0.293'],
  ['自律或目标词','−0.119','[-0.293, 0.054]','0.293'],
  ['社交称呼或互助词','−0.004','[-0.131, 0.122]','0.946'],
  ['积极表达词','−0.086','[-0.155, −0.016]','0.079'],
  ['问号','0.108','[-0.100, 0.316]','0.383'],
 ],.55,1.84,7.45,[3.0,1.15,2.25,1.05],14.5,.60);
 narrative(s,[
  ['单项与整组都要报告','积极表达原始p=0.016，但BH q=0.079；其他四项原始区间都包含0。'],
  ['文本的新增信息很少','五项特征只增加0.065个百分点R²，联合检验p=0.130。'],
  ['敏感性支持方向而非因果','样本调整、100次逐作者剔除均保留负向；PPML点估计为负，区间跨0。'],
 ],8.4,1.84,4.38,3.95);
 takeaway(s,'阶段结论','作者和情境调整改变了表达的原始优势，现有证据不足以支持稳定的文案模板。');
 note(s,'方向变化之外，还要看证据强度。积极表达原始p值是0.016，但五项检验一起做BH校正后，q值为0.079，未达到百分之五标准；其他四项原始区间都包含零。五项文字特征只增加0.065个百分点的解释度，整组联合检验p值为0.130。敏感性检验中，只看可见正文、去掉最高百分之一点赞、作者等权以及逐一剔除作者，积极表达都保留负向；不过计数模型PPML的区间跨零。因此可以说方向较一致，但幅度和精度会变化，更不能形成某个词稳定提高或降低点赞的策略。',75);
}

startChapter(3);
{
 const s=begin('主题分析：有效正文同时容纳训练与生活',3,'源报告 §5.1、附录A.3 · PDF第11、24页；描述占比以2,470帖、86位作者为范围');
 chart(s,pptx.ChartType.bar,[{name:'主导主题占比',labels:['运动与训练交流','生活感悟与问候','跑步与训练打卡','靠墙静蹲记录','骑行里程记录'],values:[52.7,35.8,4.6,3.4,3.4]}],.55,1.91,7.3,3.88,{barDir:'bar',showLegend:false,valAxisMaxVal:65,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:13});
 narrative(s,[
  ['补充词典之外的内容信息','至少3个有效词的2,478条正文构建TF-IDF矩阵，用NMF提取预先固定的五个主题。'],
  ['最终聚焦有效正文','排除8条近零贡献正文，最终2,470帖、86位作者；按权重最大的主题描述占比。'],
  ['两条主要内容线索','训练交流占52.7%，生活感悟与问候占35.8%；主题按关键词和正文命名，不参考点赞。'],
 ]);
 takeaway(s,'内容发现','只看运动项目和打卡记录，会漏掉有效正文中相当重要的生活感受与问候。');
 note(s,'词典只能识别指定的表达，我们再用主题模型概括整篇正文。先筛选至少三个有效词的文本，构建TF-IDF矩阵，用NMF提取预先固定的五个主题。排除八条成分贡献接近零的正文后，最终分析2,470帖、86位作者。图中按每帖权重最大的主题归类，训练交流占52.7%，生活感悟与问候占35.8%，其余是三类具体运动记录。主题名称不参考点赞。这说明社区有效正文既谈训练，也容纳日常感受，不能只用打卡次数概括内容。',60);
}
{
 const s=begin('作者等权：区分内容产量与作者平均构成',3,'源报告 §5.2—5.3、附录A.3 · PDF第11—12、24页；两组沿用同一主题分配');
 chart(s,pptx.ChartType.bar,[
  {name:'按帖子统计',labels:['靠墙静蹲','骑行记录','训练交流','跑步打卡','生活问候'],values:[3.4,3.4,52.7,4.6,35.8]},
  {name:'每位作者等权',labels:['靠墙静蹲','骑行记录','训练交流','跑步打卡','生活问候'],values:[0.6,2.9,52.6,5.7,38.2]},
 ],.55,1.9,7.3,3.95,{barDir:'bar',grouping:'clustered',valAxisMaxVal:65,dataLabelFormatCode:'0.0"%"',dataLabelFontSize:12,catAxisLabelFontSize:12});
 narrative(s,[
  ['改变权重，检验作者影响','先计算每位作者内部的主题比例，再对86位作者平均，避免高产作者重复贡献。'],
  ['小主题收缩，主要格局保留','静蹲从3.4%降至0.6%，最大作者贡献91.8%；训练与生活仍占主要篇幅。'],
  ['常见主题不等于反馈优势','主题加入回归后的联合p=0.166，所有单项BH q值均大于0.05，增量证据有限。'],
 ]);
 takeaway(s,'阶段结论','训练与生活并存较稳定；少数人的持续记录，也会塑造看起来常见的内容主题。');
 note(s,'主题出现得多，还可能因为少数作者反复记录。为此，我们先算每位作者内部的主题比例，再让86位作者等权。静蹲从按帖统计的3.4%降至0.6%，其85帖中，最大作者贡献了91.8%。训练与生活表达的主要份额则仍然保留。所以按帖看的是内容产量，等权看的是平均作者构成。最后把连续主题权重加入回归，整体联合p值为0.166，单项校正后也未达到标准。内容常见与具有反馈优势，仍然要分别判断。',60);
}

startChapter(4);
{
 const s=begin('评论语言：读者更常赞许，帖主更常感谢',4,'源报告 §6.1—6.2 · PDF第13—14页；角色按每条发言所在帖子确定，词类可重叠');
 chart(s,pptx.ChartType.bar,[
  {name:'其他用户（7,192条）',labels:['鼓励或赞许词','感谢词'],values:[16.9,0.6]},
  {name:'帖主（4,403条）',labels:['鼓励或赞许词','感谢词'],values:[4.5,7.9]},
 ],.55,1.9,7.35,3.95,{barDir:'col',grouping:'clustered',valAxisMaxVal:20,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:13});
 narrative(s,[
  ['简短发言承载日常交流','清理后评论长度中位数只有6个字符，常见赞许、感谢与招呼，交流经常通过少量文字完成。'],
  ['词频还需结合参与人数','“加油”612条、431人；“谢谢”359条、53人。高频既可能来自面广，也可能来自反复使用。'],
  ['角色分工需要继续配对','赞许更多出现在其他用户发言，感谢更多出现在帖主发言；总体分布尚未定位具体承接。'],
 ]);
 takeaway(s,'下一步','从“谁常说什么”继续追踪到：一条留言之后，是否出现帖主的直接回应？');
 note(s,'评论以短句为主，清理后长度中位数只有六个字符。加油覆盖431位用户，谢谢却只覆盖53人，所以词频还要结合参与面理解。按所在帖子划分角色后，其他用户的赞许词命中率16.9%，帖主为4.5%；感谢词则相反，帖主7.9%，其他用户0.6%。这呈现出读者赞许、帖主感谢的分工。不过，总体分组还不能确认具体哪句赞许接到了感谢，下一步需要直接配对。',55);
}
{
 const s=begin('直接承接：感谢更常见，回复覆盖却较低',4,'源报告 §6.3、附录A.4 · PDF第14—15、25页；7天从根评论发出时起算');
 const flow=[['6,609条根评论','其他用户发给帖主的根评论'],['同帖＋明确指向＋7天内','每条仅取最早观测到的帖主直接回复'],['3,568条配对成功','定位到根评论本身的直接承接']];
 flow.forEach((a,i)=>{const x=.55+i*4.17;box(s,x,1.83,3.9,1.08,i===2?C.paleGreen:C.lilac);txt(s,a[0],x+.17,1.99,3.56,.36,i===1?18:21,i===2?C.green:C.purple,true);txt(s,a[1],x+.17,2.53,3.56,.22,12.5,C.ink);});
 table(s,['根评论组别','根评论数','7天内直接回复覆盖','已回复中，最早回复含感谢'],[
  ['命中鼓励或赞许词','1,180','43.5%（513条）','26.7%（137 / 513）'],
  ['未命中鼓励或赞许词','5,429','56.3%（3,055条）','6.4%（195 / 3,055）'],
 ],.55,3.3,12.23,[3.0,1.45,3.42,4.36],15,.63);
 txt(s,'直接回复覆盖：分母是各组全部根评论。感谢表达占比：分母只包括已观察到直接回复的记录。',.69,5.46,11.97,.55,17,C.ink);
 takeaway(s,'不同维度','已经回复时怎样表达，与整组留言中多少得到回复，可以呈现不同方向。');
 note(s,'直接配对从6,609条外来根评论出发，要求回复来自帖主、属于同一帖子，明确指向该根评论及作者，并发生在根评论后七天内；每条只取最早观测回复，最终配对3,568条。表中要分清两个分母。以全部根评论为分母，鼓励组观察到直接回复的比例为43.5%，另一组56.3%，鼓励组较低。只看已回复记录，最早回复含感谢词的比例却是26.7%对6.4%，鼓励组更高。这说明回话怎样表达，与哪些留言被接住，是两个维度。两组帖主和情境有差别，不能把覆盖差异解释成鼓励词带来的效果。',80);
}

startChapter(5);
{
 const s=begin('网络构建：把每次发言放回它所指向的账号',5,'源报告 §7.1、附录A.4 · PDF第16—17、25页；图沿用报告图11');
 s.addImage({path:path.join(ROOT,'figures','06_comment_network.png'),x:.55,y:1.85,w:7.3,h:4.05});
 narrative(s,[
  ['先确定方向与权重','根评论指向帖主，明确回复指向被回复用户；同一方向的多次事件合并，次数累加为边权。'],
  ['再区分事件、边与账号','11,595条评论排除84次自我互动后，11,511次事件形成4,069条有向边、2,932个有边账号。'],
  ['图形辅助理解结构','金色为样本作者，蓝色为其他账号；节点按接收量对数缩放，为便于阅读省略箭头。'],
 ],8.45,1.82,4.3,4.03);
 takeaway(s,'关系含义','10次同方向留言是一条权重为10的边；网络账号同时包含发送者与接收者。');
 note(s,'接下来把评论转成有向加权网络。根评论指向帖主，明确回复指向被回复用户；同一对账号同方向的多次互动合并成一条边，次数作为权重。文本统计的11,595条评论排除84次自我互动后，形成11,511次网络事件、4,069条有向边，涉及2,932个账号。图中金色为样本作者，蓝色为其他参与者，节点大小按接收量的对数缩放。图上省略箭头是为了阅读，统计仍然保留方向。这样就可以把评论总量拆回谁向谁发言。',60);
}
{
 const s=begin('网络结构：间接相连广，回话主要由帖主承担',5,'源报告 §7.2 · PDF第17页；角色占比以4,902次非自我明确回复为分母');
 chart(s,pptx.ChartType.bar,[{name:'明确回复的角色份额',labels:['帖主 → 其他用户','其他用户 → 帖主','其他用户 → 其他用户'],values:[89.0,9.1,2.0]}],.55,2.02,7.3,3.47,{barDir:'bar',showLegend:false,valAxisMaxVal:105,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:13});
 narrative(s,[
  ['大多数账号能间接串起','最大弱连通部分包含94.4%的有边账号；网络密度仅0.0473%，直接联系仍稀疏。'],
  ['明确回话高度依赖帖主','帖主回复其他用户4,361次，占89.0%；其他用户彼此回复97次，占2.0%。'],
  ['连通与横向对话要区分','用户经由共同评论对象间接相连，实际回话则主要围绕帖主展开。'],
 ]);
 takeaway(s,'结构发现','多人留言形成参与广度，帖主持续回应构成主要承接；横向接话只占很小份额。');
 note(s,'忽略方向后，94.4%的账号处于最大的连通部分，但直接关系密度很低。这意味着大家能通过共同评论对象间接串起来，并不代表彼此经常交谈。再看4,902次明确回复，89%由帖主发给其他用户，而其他用户彼此回复只有2%。因此，这批评论区最主要的组织方式，是读者向帖主留言，帖主承接回应，参与者之间的横向对话占比较小。',50);
}
{
 const s=begin('互动规模：相似评论量，可以来自很不同的人数',5,'源报告 §7.3 · PDF第17—18页；次数与人数均包括根评论和明确回复');
 const arr=[['U1528','1,378次','53位发送者','已有发送者反复留言的份量较大'],['U0948','1,275次','1,091位发送者','接收量相近，却覆盖更多不同账号']];
 arr.forEach((a,i)=>{const x=.55+i*6.29;box(s,x,1.87,5.94,3.18,i?C.paleGreen:C.lilac);txt(s,a[0],x+.25,2.09,5.44,.35,20,C.muted,true);txt(s,a[1],x+.25,2.75,5.44,.57,34,C.purple,true);txt(s,a[2],x+.25,3.51,5.44,.43,25,C.green,true);txt(s,a[3],x+.25,4.3,5.44,.43,18,C.ink);});
 txt(s,'前10位账号接收了54.0%的非自我互动事件。事件次数（加权入度）衡量声量，不同发送者人数（入度）衡量接收关系的范围。',.69,5.35,11.97,.59,18,C.ink);
 takeaway(s,'衡量方式','不能只按评论总量判断活跃程度，还要区分参与广度与已有关系中的重复往来。',6.35);
 note(s,'接收事件集中在部分账号，前十位占了54%。但相似接收量，可以对应完全不同的参与面。U1528收到1,378次互动，只有53位发送者；U0948收到1,275次，却来自1,091位发送者。前者更多包含已有账号的重复留言，后者覆盖面明显更广。因此接收事件数，也就是加权入度，反映声量；不同发送者人数，也就是入度，反映关系范围。评价评论活跃时，应同时报告这两项，不能把评论多直接当成参与面广。',60);
}
{
 const s=begin('互动时序：评论集中在早期，帖主在线程中承接',5,'源报告 §7.4、附录A.4 · PDF第18—19、25页；时序分母11,595条评论');
 stat(s,'64.5%','评论发生在发帖后24小时内',.55,1.85,3.88);
 stat(s,'82.2%','评论发生在发帖后7天内',4.72,1.85,3.88);
 stat(s,'2.05小时','已参与线程：首回距根评论中位数',8.89,1.85,3.89);
 box(s,.55,3.55,5.86,2.1,C.paleGreen);box(s,6.72,3.55,6.06,2.1,C.lilac);
 txt(s,'57.0%的根评论线程有帖主参与',.79,3.77,5.38,.4,20,C.green,true);
 txt(s,'线程参与包括留言串内的回复；第4章直接配对则要求明确指向根评论本身，且限根评论后7天。',.79,4.43,5.36,.94,18,C.ink);
 txt(s,'双向连接体现留言与回话',6.96,3.77,5.5,.4,20,C.purple,true);
 txt(s,'全量网络互惠率49.6%，仅明确回复为29.9%；根评论与帖主回复，能够组成账号间的双向关系。',6.96,4.43,5.5,.94,18,C.ink);
 takeaway(s,'口径区别','评论发生时间从发帖起算；直接配对与线程首回从根评论起算，三类指标分别衡量。');
 note(s,'评论主要发生在发帖后的早期：64.5%在二十四小时内，82.2%在七天内。在线程层面，57%观察到帖主参与；只在这些已参与线程里，帖主首回距根评论的中位间隔约两小时。线程参与包括留言串内的回复，比直接匹配根评论的条件宽，两个比例不能替代。关系层面，全量互惠率为49.6%，仅明确回复为29.9%，也体现根评论加帖主回话形成双向连接。概括来说，互动发生得较早，并且主要由帖主承接，但时间、关系和留言三个层次要分别衡量。',55);
}

startChapter(6);
{
 const s=begin('综合判断与建议：把证据落实到内容和承接',6,'源报告 §8.1—8.2、§9.2 · PDF第20—21页；建议效果仍需后续验证');
 const rows=[
  ['表达要结合作者','原始高赞与调整后关联不同，文本增量较少。','创作者不依赖固定关键词模板，关注完整内容与持续记录。'],
  ['活跃要看参与面','相近接收量对应不同人数，回话主要围绕帖主。','运营同时观察事件量、独立参与者和留言承接，关注低反馈者。'],
  ['早期回应值得关注','多数评论出现在发帖后的早期，帖主承担主要回复。','尝试及时承接留言，但回复是否促进后续互动仍需检验。'],
 ];
 rows.forEach((a,i)=>{const y=1.83+i*1.32;circle(s,.61,y+.12,.48,i===1?C.green:C.purple,String(i+1),C.white,17);txt(s,a[0],1.35,y+.02,3.1,.35,20,C.purple,true);txt(s,a[1],1.35,y+.6,4.5,.53,17,C.ink);txt(s,a[2],6.5,y+.19,6.0,.86,19,C.ink);});
 takeaway(s,'实践方向','内容投入与互动支持值得继续探索；当前观察性结果提供设计线索，效果需验证。');
 note(s,'将两条分析线合在一起，可以形成三点建议。第一，表达的原始优势会随着作者和情境调整而变化，创作者不必依赖固定关键词模板，可以关注完整内容和持续记录。第二，评论活跃不能只按总量衡量，平台还应看独立参与者和留言承接，关注长期缺少反馈的人。第三，既然评论集中在发帖早期，可以尝试及时回应。不过，这些都是与观察结果对应的参考方向，配图或者早回复能否提高后续互动，现有数据还没有识别，需要进一步验证。',70);
}
{
 const s=begin('研究边界与下一步：用统一窗口检验实际效果',6,'源报告 §9.3—9.4 · PDF第22页；所述随机实验尚未实施');
 box(s,.55,1.85,5.86,3.98,C.lilac);box(s,6.72,1.85,6.06,3.98,C.paleGreen);
 txt(s,'当前结论适用到哪里',.8,2.1,5.35,.43,24,C.purple,true);
 para(s,'样本与记录有限','只有100位课程样本作者，抽样机制不明；正文和评论覆盖不全，不能推广到全平台。',.8,2.9,5.35,1.25);
 para(s,'仍是平台内关联','缺少真实曝光、粉丝数、统一采集时点和完整内容；点赞不等于运动效果或用户留存。',.8,4.3,5.35,1.25);
 txt(s,'下一步怎样验证',6.97,2.1,5.5,.43,24,C.green,true);
 para(s,'按作者随机分组','比较运动过程记录提示、面向伙伴的问题提示和常规发布，减少同一作者跨组的干扰。',6.97,2.9,5.5,1.25);
 para(s,'统一发帖后7天观察','记录实际曝光、独立互动人数、后续发布行为与回复质量；试点后再估计所需样本量。',6.97,4.3,5.5,1.25);
 takeaway(s,'后续方向','用更完整的曝光与内容记录，加上随机实验，推进对表达和互动效果的判断。');
 note(s,'最后说明边界。样本只有100位作者，抽样机制不明；正文和评论都有缺口，也缺少真实曝光和统一采集时点，所以不能外推到全平台，更不能把点赞等同于运动坚持或留存。后续若获得实验权限，可以按作者随机分组，比较两类表达提示和常规发布，统一观察发帖后七天，同时记录曝光、独立互动人数与回复质量。这样才能从关联分析进一步判断实际效果，这个实验目前尚未实施。',50);
}
{
 const s=begin('结论',6,'依据排版优化版报告 §9.5；方法文献与完整结果见源报告第23—26页',{dark:true,clean:true});
 txt(s,'最后的判断',.65,.7,11.9,.6,36,C.white,true);
 const ends=[['01','原始表达优势，需要放回作者与情境','现有证据不足以支持特定词汇或主题稳定提高点赞。'],['02','训练交流与生活表达并存','部分小主题的高频出现，也反映少数作者的持续记录。'],['03','评论往来主要围绕帖主展开','理解活跃程度，需要结合次数、人数和回应覆盖。']];
 ends.forEach((a,i)=>{const y=1.94+i*1.47;circle(s,.72,y,.52,C.green,a[0],C.white,16);txt(s,a[1],1.58,y-.03,10.8,.5,25,C.white,true);txt(s,a[2],1.58,y+.67,10.8,.5,19,'D4CBE3');});
 note(s,'最后总结三点：表达的原始优势，需要结合作者和情境理解；训练交流与生活表达并存，但内容频次也受高产作者影响；评论主要围绕帖主展开，评价活跃应同时看次数、人数和回应覆盖。这就是本次内容分析与评论网络共同给出的认识。',30);
}

async function main(){
 if(manifest.length!==MAIN_COUNT)throw new Error('This version must contain exactly 18 presented slides.');
 await pptx.writeFile({fileName:OUT+'.pptx'});
 const zip=await JSZip.loadAsync(fs.readFileSync(OUT+'.pptx'));
 const axisRepairs=[];
 for(const name of Object.keys(zip.files).filter(n=>/^ppt\/charts\/chart\d+\.xml$/.test(n))){
  let xml=await zip.file(name).async('string');
  const declared=new Set([...xml.matchAll(/<c:(?:catAx|valAx|serAx)\b[^>]*>([\s\S]*?)<\/c:(?:catAx|valAx|serAx)>/g)].map(m=>m[1].match(/<c:axId\s+val="([^"]+)"\s*\/>/)[1]));
  let removed=0;
  xml=xml.replace(/<c:barChart\b[^>]*>[\s\S]*?<\/c:barChart>/g,bar=>bar.replace(/<c:axId\s+val="([^"]+)"\s*\/>/g,(all,id)=>{if(declared.has(id))return all;removed++;return '';}));
  zip.file(name,xml);axisRepairs.push({chart:name,orphanAxisReferencesRemoved:removed,declaredAxes:[...declared]});
 }
 for(const name of Object.keys(zip.files).filter(n=>/^ppt\/slides\/_rels\/slide\d+\.xml\.rels$/.test(n))){
  const xml=await zip.file(name).async('string');zip.file(name,xml.replace(/Target="\/ppt\/charts\//g,'Target="../charts/'));
 }
 fs.writeFileSync(OUT+'.pptx',await zip.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
 fs.writeFileSync(path.join(QA,'chart_axis_repairs.json'),JSON.stringify(axisRepairs,null,2));
 fs.writeFileSync(path.join(QA,'slides_manifest.json'),JSON.stringify(manifest,null,2));
 let cumulative=0;
 const clock=s=>`${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`;
 const script=manifest.map(s=>{const start=cumulative;cumulative+=s.seconds;return `第${String(s.page).padStart(2,'0')}页｜${s.title}\n建议${s.seconds}秒；累计${clock(start)}—${clock(cumulative)}\n${'─'.repeat(30)}\n${s.speech}\n\n来源：${s.source}\n`;}).join('\n\n');
 const chaptersTiming=chapters.map((c,i)=>({chapter:i+1,title:c[0],slides:manifest.filter(s=>s.chapter===i+1).map(s=>s.page),seconds:manifest.filter(s=>s.chapter===i+1).reduce((a,s)=>a+s.seconds,0)}));
 const time={presented_slides:MAIN_COUNT,hidden_slides:0,appendix_slides:0,speech_seconds:cumulative,transition_buffer_seconds:50,total_target_seconds:cumulative+50,chapters:chaptersTiming,narration_characters:manifest.reduce((a,s)=>a+s.speech.length,0),timing_note:'逐页建议时间是排练预算，包含讲解与指图；另留50秒给转场、换人及停顿，实际以排练为准。'};
 fs.writeFileSync(path.join(QA,'timing_plan.json'),JSON.stringify(time,null,2));
 fs.writeFileSync(OUT+'_逐页讲稿.txt',`Keep社区内容表达与互动反馈｜15—20分钟精简版\n18页全部为正式讲述内容，无备用页或隐藏页。\n逐页讲述预算${clock(cumulative)}，另留50秒转场，总目标${clock(cumulative+50)}。\n每页讲稿亦写入PPT演讲者备注；实际时长请以正常语速排练校准。\n\n${script}`);
 console.log(JSON.stringify({slides:manifest.length,nativeCharts:manifest.reduce((a,s)=>a+s.charts.length,0),timing:time,pptx:OUT+'.pptx'}));
}
main().catch(e=>{console.error(e);process.exit(1);});
