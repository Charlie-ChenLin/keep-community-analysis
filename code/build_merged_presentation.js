/* Combine the latest local decks with the teammate's revision.
 * Source results are read only. Charts, tables and text remain editable.
 * Run: NODE_PATH=/tmp/keep-slides-tools/node_modules node code/build_merged_presentation.js
 */
const pptxgen = require('pptxgenjs');
const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..');
const QA = path.join(ROOT, 'validation/slides_merged_10_15');
const OUT = path.join(ROOT, 'Keep社区内容表达与互动反馈_10-15分钟合并版');
fs.mkdirSync(QA, {recursive:true});
const pres = new pptxgen();
pres.layout='LAYOUT_WIDE';
pres.author='陈霖、董依心'; pres.company='社交媒体网络分析课程小组';
pres.title='Keep社区内容表达与互动反馈分析';
pres.subject='10—15分钟课堂汇报；13页正文及2页答疑';
pres.lang='zh-CN';
const F='Arial Unicode MS';
pres.theme={headFontFace:F,bodyFontFace:F,lang:'zh-CN'};
const C={ink:'20332F',green:'245C4F',deep:'173F36',muted:'65756F',light:'EDF4F0',
  pale:'F6F8F7',line:'DFE6E2',orange:'B97339',paleOrange:'F8F0E8',gray:'AAB8B0',white:'FFFFFF',purple:'6F5B8C'};
const M=[]; const MAIN=13;
const FOOTERS=[
 '社交媒体网络分析 · 课程小组汇报',
 '数据：课程提供的Keep样本；帖子发表于2020年11—12月（UTC）。',
 '原报告第3章 · 描述性均值比较，尚未调整作者与发布情境。',
 '原报告第4章 · 四类表达可重叠；词典仅识别字面用词。',
 '原报告第4章 · 主模型；标准误按作者聚类，五项文字线索采用BH多重检验校正。',
 '原报告第5章 · 2,470帖、86位作者；两组使用相同的主题分类。',
 '原报告第6章 · 角色按所在帖子确定；词类可重叠。',
 '原报告第6章 · 同帖、明确回复根评论，且在根评论发出后7天内。',
 '原报告第7章，图11 · 金色为样本作者，蓝色为其他账号；图中省略箭头。',
 '原报告第7章 · 分母：4,902次非自我明确回复，排除根评论。',
 '原报告第7章 · 次数为收到的互动事件，人数为不同发送者；账号已匿名化。',
 '原报告第7章 · 分母：11,595条评论；两个窗口均从发帖时间起算。',
 '完整方法与结果见原报告；后附2页答疑，不计入主讲。',
 '原报告第2章、附录A.1 · 词典识别字面表达，维度可重叠。',
 '原报告第6—7章、附录A.4 · 未观察到回复，不等于实际没有回复。'
];
function csv(name){
 const text=fs.readFileSync(path.join(ROOT,'results',name),'utf8').replace(/^\uFEFF/,'').trim();
 const rows=[];let row=[],cell='',quoted=false;
 for(let i=0;i<text.length;i++){
  const ch=text[i];
  if(ch==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
  else if(ch===','&&!quoted){row.push(cell);cell='';}
  else if(ch==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}
  else cell+=ch;
 }
 row.push(cell);rows.push(row);const keys=rows.shift();return rows.map(r=>Object.fromEntries(keys.map((k,i)=>[k,r[i]])));
}
const summary=JSON.parse(fs.readFileSync(path.join(ROOT,'results/summary.json'),'utf8'));
const features=csv('text_features_summary.csv');
const coefs=csv('regression_coefficients.csv').filter(r=>r.model.startsWith('M3_')).slice(0,5);
const themes=csv('supplemental_topic_author_weighting.csv');
const words=csv('comment_text_features.csv');
const direct=csv('supplemental_direct_reply_language.csv');
const nodes=csv('network_nodes.csv');
function text(s,t,x,y,w,h,size=20,color=C.ink,bold=false,extra={}){
 s.addText(t,{x,y,w,h,fontFace:F,fontSize:size,color,bold,margin:0,paraSpaceAfterPt:0,
  valign:'top',breakLine:false,wrap:true,lang:'zh-CN',...extra});
 s._m.text.push({text:t,x,y,w,h,size});
}
function rect(s,x,y,w,h,fill,line=fill){s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:fill},line:{color:line,width:0}});}
function line(s,x,y,w,h,color=C.line,width=1,arrow=false){
 s.addShape(pres.ShapeType.line,{x,y,w,h,line:{color,width,...(arrow?{endArrowType:'triangle'}:{})}});
}
function dot(s,x,y,d,fill){s.addShape(pres.ShapeType.ellipse,{x,y,w:d,h:d,fill:{color:fill},line:{color:fill,width:0}});}
function slide(title,section,source,{dark=false,clean=false,appendix=false}={}){
 const s=pres.addSlide();s.background={color:dark?C.deep:C.white};
 s._m={page:M.length+1,title,section,source,appendix,text:[],charts:[],seconds:0,speech:''};M.push(s._m);
 if(!clean){
  text(s,section,.62,.34,11.6,.25,11,dark?'C5D9D0':C.muted);
  text(s,title,.62,.88,12,.7,29,dark?C.white:C.ink,true);
 }
 text(s,FOOTERS[M.length-1]||source,.62,7.08,11.3,.23,9,dark?'B3CFC1':C.muted);
 text(s,appendix?`答疑 ${M.length-MAIN}`:`${String(M.length).padStart(2,'0')} / ${MAIN}`,11.92,7.06,.78,.26,10.5,dark?'BDD3C8':C.muted,false,{align:'right'});
 return s;
}
function note(s,speech,seconds=0,short=''){
 s._m.speech=speech;s._m.seconds=seconds;s._m.short=short;
 s.addNotes(`${s._m.appendix?'答疑备用，不计入主讲':`标准版建议${seconds}秒`}\n\n${speech}${short?'\n\n10分钟版：'+short:''}\n\n数据来源：${s._m.source}`);
}
function chart(s,type,data,x,y,w,h,opts={}){
 const options={x,y,w,h,fontFace:F,showTitle:false,showLegend:data.length>1,
  legendPos:'b',legendFontFace:F,legendFontSize:12,
  catAxisLabelFontFace:F,catAxisLabelFontSize:13,valAxisLabelFontFace:F,valAxisLabelFontSize:11,
  catAxisLabelColor:C.ink,valAxisLabelColor:C.muted,catAxisLineShow:false,valAxisLineShow:false,
  catGridLine:{style:'none'},valGridLine:{color:'E7ECE9',width:.6},
  showValue:true,dataLabelPosition:'outEnd',dataLabelFormatCode:'0.0',dataLabelFontFace:F,
  dataLabelFontSize:13,dataLabelColor:C.ink,showCatName:false,showSerName:false,
  chartColors:data.length>1?[C.green,C.orange]:[C.green],showBorder:false,showShadow:false,showMarker:false,
  valAxisMinVal:0,gapSizePct:85,showLegendKey:false,showCatName:false,
  ...(opts.barDir==='bar'?{catAxisOrientation:'maxMin',catAxisLabelPos:'low',valAxisLabelPos:'low'}:{}),...opts};
 s.addChart(type,data,options);s._m.charts.push({type,data,options});
}
function table(s,headers,rows,x,y,w,colW,{fontSize=16,rowH=.66,highlight=-1}={}){
 const data=[headers.map(t=>({text:t,options:{bold:true,color:C.green,fill:C.light}})),
  ...rows.map((r,i)=>r.map(t=>({text:String(t),options:{fill:i===highlight?C.paleOrange:(i%2?C.pale:C.white),color:C.ink}})))];
 s.addTable(data,{x,y,w,colW,rowH,fontFace:F,fontSize,border:{color:C.white,pt:1},
  margin:[.12,.15,.12,.15],vertAnchor:'mid',autoPage:false,paraSpaceAfterPt:0});
 s._m.text.push({text:headers.join(' ')+' '+rows.flat().join(' '),x,y,w,h:rowH*(rows.length+1),size:fontSize});
}
function label(s,t,x,y,w=4,color=C.muted){text(s,t,x,y,w,.31,13,color);}
function value(s,n,t,x,y,w=3.6,color=C.green){text(s,n,x,y,w,.73,40,color,true);text(s,t,x,y+.9,w,.66,16,C.ink);}
function person(s,x,y,scale,color){dot(s,x+.075*scale,y,.15*scale,color);rect(s,x,y+.2*scale,.3*scale,.27*scale,color);}

// 1 — Opening. Preserve the teammate's real names.
{
 const s=slide('Keep社区内容表达与互动反馈分析','开场','社交媒体网络分析 · 课程小组汇报',{dark:true,clean:true});
 text(s,'Keep 社区',.75,.72,8,.55,25,'C3D9CE');
 text(s,'内容表达与\n互动反馈分析',.75,1.75,9.6,1.67,40,C.white,true);
 text(s,'哪些帖子获得更多点赞？\n评论区里，又是谁在接话？',.8,4.05,8.5,1.05,24,'E0EBE5');
 text(s,'陈霖  ·  董依心',.8,6.08,8,.45,20,C.white);
 dot(s,10.25,2.15,1.25,'3B7160');dot(s,10.5,4.25,.7,C.orange);
 line(s,10.86,3.4,0,.7,'8FAF9F',2,true);
 text(s,'点赞',10.25,2.56,1.25,.4,20,C.white,true,{align:'center'});
 text(s,'回复',10.38,5.16,1.2,.4,19,'D7E6DD',false,{align:'center'});
 note(s,'大家好，我们研究的是Keep社区的内容表达与互动反馈。我们想知道两件事：什么样的文字和更高点赞同时出现；评论区又是怎样形成往来的。分析中最有意思的地方，是有些看起来直观的判断，在换一种比较方式后会发生变化。',25,'直接提出“怎样获得点赞、谁在评论里接话”两个问题。');
}
// 2 — Context, sample and a short analytical route.
{
 const s=slide('先看帖子怎样写，再看评论怎样往来','研究问题与样本','来源：summary.json；报告§1—3。帖子发表于2020年11—12月（UTC）。');
 text(s,'健身社区里，运动记录和日常交流发生在一起。',.65,1.78,11.8,.5,23,C.green,true);
 value(s,'9,532','帖子 · 100位作者',.7,2.65,3.7);
 value(s,'11,595','去重后评论',4.8,2.65,3.6);
 value(s,'1,323','有采集到评论的帖子',8.8,2.65,3.7);
 rect(s,.67,4.55,5.75,1.66,C.light);rect(s,6.75,4.55,5.9,1.66,C.paleOrange);
 text(s,'文字与点赞',.9,4.77,5.2,.4,22,C.green,true);
 text(s,'比较用词、内容主题与累计点赞\n把作者、媒体形式和日期纳入比较',.9,5.34,5.1,.66,18);
 text(s,'留言与回复',6.98,4.77,5.25,.4,22,C.orange,true);
 text(s,'先看谁说什么，再按回复对象连线\n区分留言次数、参与人数和回复',6.98,5.34,5.2,.66,18);
 text(s,'评论未覆盖的帖子，记为未知；3,984帖缺可用正文，保留并作标记。',.7,6.52,11.8,.35,13.5,C.muted);
 note(s,'Keep里既有运动打卡，也有问候、感受分享和同伴鼓励。我们使用课程提供的100位作者、9,532条帖子，以及去重后的11,595条评论。帖子实际来自2020年11到12月。左边这条线研究文字和点赞的关联，会同时考虑作者、媒体形式和日期；右边研究评论里谁说什么、谁回复谁。评论只覆盖1,323帖，其他帖子没有采到评论，不能按零评论处理。正文缺失的帖子也保留，并单独标记。',60,'只讲样本规模、两条主线，以及未采到评论不等于零评论。');
}
// 3 — Baseline differences matter before talking about words.
{
 const s=slide('图片和视频帖，原始点赞水平更高','文字与点赞','来源：media_summary.csv；summary.json。均为样本内描述性均值。');
 label(s,'平均每帖点赞数',.7,1.88,6);
 chart(s,pres.ChartType.bar,[{name:'平均点赞',labels:['图片','视频','纯文字','无媒体'],values:[51.03,48.05,7.94,3.91]}],.68,2.3,8,3.97,{barDir:'col',showLegend:false,valAxisMaxVal:60,dataLabelFormatCode:'0.00',catAxisLabelFontSize:15});
 value(s,'25','点赞中位数',9.2,2.35,3.2);
 text(s,'平均数为37.05，\n最高一帖为5,126。',9.2,4.15,3.2,.86,20);
 text(s,'比较文字之前，\n先把媒体形式和\n作者差异考虑进去。',9.2,5.44,3.2,1.1,20,C.green,true);
 text(s,'8,286帖点赞数高于记录浏览数，口径不明，因此使用累计点赞数，不计算点赞率。',.7,6.6,11.9,.34,13,C.muted);
 note(s,'先看最直观的背景：图片和视频帖，平均点赞约51和48；纯文字与无媒体帖约8和4。这样的差距提醒我们，不能把高赞全部归到文字表达上。点赞本身也有长尾，平均数是37，但中位数只有25，最高一帖超过五千。后面的比较会把媒体形式与作者等因素纳入模型。另一个数据问题是，多数帖子点赞高于记录浏览数，两个字段口径不清，所以我们没有计算点赞率。',45,'读出图片、视频约50赞，文字约8赞，并说明比较用词需要控制媒体形式。');
}
// 4 — The descriptive observation which motivates adjustment.
{
 const s=slide('只看分组均值，四类表达都显得“更受欢迎”','文字与点赞','来源：text_features_summary.csv。固定词表命中；四类表达可以重叠。');
 label(s,'平均每帖点赞数',.7,1.88,6);
 chart(s,pres.ChartType.bar,[
  {name:'命中该表达',labels:['自律 / 目标','社交 / 互助','积极表达','问号'],values:features.map(r=>+r.raw_mean_likes_hit)},
  {name:'未命中',labels:['自律 / 目标','社交 / 互助','积极表达','问号'],values:features.map(r=>+r.raw_mean_likes_nohit)}
 ],.65,2.3,8.15,4.1,{barDir:'col',chartColors:[C.green,'AFBCB5'],valAxisMaxVal:130});
 text(s,'以积极表达为例',9.13,2.32,3.5,.35,18,C.muted);
 text(s,'57.29 vs 35.76',9.13,2.91,3.55,.65,29,C.green,true);
 text(s,'命中“开心、喜欢、\n哈哈”等词的帖子，\n原始平均点赞更高。',9.13,3.96,3.45,1.1,20);
 text(s,'是措辞的差别，\n还是发帖人的差别？',9.13,5.51,3.48,.88,22,C.orange,true);
 note(s,'如果按词表简单分组，四类表达的命中组都比未命中组平均点赞高。问号组甚至超过一百个赞。比如积极表达，命中“开心、喜欢、哈哈”等词的帖子，平均57.29个赞；没命中的约35.76。直觉上我们容易说，这样写更讨喜。但两组可能恰好由不同作者构成，也有不同的媒体形式和发帖日期。因此，我们接着问：把这些条件放到一起比较，优势是否仍然存在？',60,'只用积极表达57.29对35.76这个例子，引出作者与情境调整。');
}
// 5 — Compact actual results. Statistical table remains editable.
{
 const s=slide('调整之后，还不足以支持一套“高赞用词”','文字与点赞','来源：regression_coefficients.csv（M3）；summary.json。因变量：ln(1+点赞数)。');
 label(s,'扣除作者差异、日期差异，并控制媒体形式等已记录条件',.7,1.86,11.8);
 const names=['正文长度','自律 / 目标','社交 / 互助','积极表达','问号'];
 table(s,['文字线索','系数','原始95%区间','BH q值'],coefs.map((r,i)=>[names[i],(+r.coef).toFixed(3),`[${(+r.ci_low).toFixed(3)}, ${(+r.ci_high).toFixed(3)}]`,(+r.q_bh_focal).toFixed(3)]),.67,2.42,8,[2.05,1.2,3.25,1.5],{fontSize:16,rowH:.57,highlight:3});
 text(s,'积极表达的系数转负',9.16,2.49,3.45,.78,23,C.orange,true);
 text(s,'原始 p = 0.016\n校正后 q = 0.079',9.16,3.55,3.45,.8,20);
 text(s,'多重检验后，\n未达到5%标准。',9.16,4.7,3.45,.8,20);
 text(s,'五项文字线索新增的解释度仅0.065个百分点；联合检验 p = 0.130。',.7,6.22,11.8,.44,19,C.green,true);
 note(s,'主模型进一步扣除作者和日期的差异，也控制了媒体形式等条件。这里可以理解为，更多利用同一作者在不同帖子间的变化来比较。积极表达的系数转为负数，说明原始均值优势没有延续到调整后的比较中。但这个负向结果在多重检验校正后，q值是0.079，没有达到5%的标准；因此也不能反过来说，积极用词会让点赞减少。五项文字线索新增的解释度只有0.065个百分点。我们的判断是，现有证据不足以支持一套可照搬的高赞用词。',75,'只指积极表达一行与0.065个百分点，不逐行读表。');
}
// 6 — Theme coverage and a concrete author-composition example.
{
 const s=slide('一种主题出现得多，可能只是少数作者写得多','帖子主题','来源：supplemental_topic_author_weighting.csv；extension_topics.csv。2,470帖、86位作者。');
 label(s,'沿用同一主题分类，换一种统计权重（%）',.7,1.87,8.6);
 const order=[2,4,3,0,1];const labs=['运动与训练交流','生活感悟与问候','跑步与训练打卡','靠墙静蹲记录','骑行里程记录'];
 chart(s,pres.ChartType.bar,[{name:'按帖子统计',labels:labs,values:order.map(i=>+themes[i].post_equal_share*100)},
  {name:'每位作者等权',labels:labs,values:order.map(i=>+themes[i].author_equal_share*100)}],.64,2.27,8.2,4.32,
  {barDir:'bar',chartColors:[C.green,C.orange],valAxisMaxVal:60,dataLabelFormatCode:'0.0"%"',gapSizePct:55,catAxisLabelFontSize:12.5});
 text(s,'靠墙静蹲',9.18,2.42,3.4,.45,23,C.green,true);
 text(s,'3.4% → 0.6%',9.18,3.15,3.55,.65,29,C.orange,true);
 text(s,'85帖中有78帖\n来自同一位作者。',9.18,4.23,3.35,.9,22);
 text(s,'训练与生活两类内容，\n换权重后仍占主要份额。',9.18,5.63,3.4,.8,19,C.green,true);
 note(s,'我们还对有效正文做了主题分析：分词后用TF-IDF和NMF提取预先固定的五类主题，再依据关键词命名。训练交流和生活问候占了大多数。不过，按帖子统计会让高产作者被多次计入。把每位作者的主题比例先算出来，再让86位作者各占相同权重，静蹲从3.4%降到0.6%。原因很具体：85条静蹲主题帖子中，78条来自同一个人。因此，一种内容出现得多，不一定意味着很多人都在写。训练和生活并存的主要格局则保留下来。',65,'只讲静蹲85帖中78帖来自一人，不读其余主题数值。');
}
// 7 — Real observed terms; no invented user quotations.
{
 const s=slide('读者更常说“加油”，帖主更常说“谢谢”','评论内容','来源：comment_text_features.csv、comment_text_terms.csv。角色按所在帖子确定；词类可重叠。');
 label(s,'发言中命中相应词类的比例（%）',.7,1.88,8.5);
 chart(s,pres.ChartType.bar,[
  {name:'其他用户（7,192条）',labels:['鼓励 / 赞许词','感谢词'],values:[16.8798665,.5839822]},
  {name:'帖主（4,403条）',labels:['鼓励 / 赞许词','感谢词'],values:[4.5196457,7.8809902]}
 ],.68,2.3,8.2,3.85,{barDir:'col',valAxisMaxVal:20,dataLabelFormatCode:'0.0"%"',gapSizePct:120});
 text(s,'评论往往很短',9.2,2.44,3.4,.42,22,C.green,true);
 text(s,'6个字符',9.2,3.12,3.4,.65,32,C.green,true);
 text(s,'清理后长度中位数',9.2,3.92,3.4,.4,17,C.muted);
 text(s,'“加油” 612条 / 431人\n“谢谢” 359条 / 53人',9.2,5.12,3.45,.92,18);
 text(s,'高频可以来自很多人，也可以来自少数人的重复使用。',.7,6.52,11.8,.38,17,C.muted);
 note(s,'接下来转到评论。评论长度的中位数只有六个字符，很多交流靠很短的话完成。按角色分组，其他用户的发言更常命中鼓励和赞许词，帖主更常命中感谢词，这和“读者留言鼓励、帖主回复致谢”的场景相符。词频还要结合人数看：“加油”出现612条，来自431个人；“谢谢”出现359条，却只来自53个人。所以，同样是高频词，背后的参与面并不一样。下一步要把这些发言放回具体的回复关系中。',55,'用“加油”与“谢谢”说明角色差异，不逐项读命中率。');
}
// 8 — Different denominators explicitly visible.
{
 const s=slide('鼓励留言得到回复时，回复更常带有感谢','评论与直接回复','来源：supplemental_direct_reply_language.csv。配对要求同帖、明确回复根评论、根评论后7天内。');
 text(s,'6,609条外来根评论 → 3,568条观察到帖主直接回复',.7,1.85,11.8,.5,22,C.green,true);
 text(s,'根评论：其他用户直接发在帖子下、没有指定回复对象的留言。',.73,2.4,11.8,.26,12.5,C.muted);
 text(s,'整组留言中，多少观察到直接回复？',.73,2.68,5.7,.4,19,C.ink,true);
 text(s,'已有回复中，多少带有感谢？',7.03,2.68,5.65,.4,19,C.ink,true);
 const labs=['鼓励 / 赞许留言','未命中该词类'];
 chart(s,pres.ChartType.bar,[{name:'直接回复覆盖',labels:labs,values:[43.4745763,56.2718733]}],.69,3.26,5.76,2.6,
  {barDir:'bar',showLegend:false,valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',chartColors:[C.green],catAxisLabelFontSize:11.5});
 chart(s,pres.ChartType.bar,[{name:'回复含感谢',labels:labs,values:[26.705653,6.3829787]}],6.98,3.26,5.72,2.6,
  {barDir:'bar',showLegend:false,valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',chartColors:[C.orange],catAxisLabelFontSize:11.5});
 text(s,'分母：各组全部根评论\n513 / 1,180；3,055 / 5,429',.83,6.02,5.65,.68,14,C.muted);
 text(s,'分母：各组已观察到直接回复的评论\n137 / 513；195 / 3,055',7.12,6.02,5.5,.68,14,C.muted);
 note(s,'这里把其他用户直接发在帖子下、没有指定回复对象的留言称为根评论。我们按明确的回复对象配对，只取根评论发出后七天内观察到的最早一条帖主直接回复。注意，这页两张图回答的是两个问题。左边看一组留言里多少观察到了回复，鼓励组是43.5%，另一组是56.3%。右边只看已经得到回复的留言，鼓励组的回复有26.7%带感谢，另一组为6.4%。所以，回复中感谢更多，和整组留言更容易得到回复，并不是同一件事。记录有缺口，也不能把未观察到的回复全部当成实际没有回复。',65,'本页用35秒：只说明两张图分母不同，鼓励组的回复更常致谢，但观测回复覆盖较低。');
}
// 9 — Keep the existing actual network figure, introduce its semantics first.
{
 const s=slide('把每次留言，连到它实际指向的账号','评论关系网络','来源：报告图11（figures/06_comment_network.png）；summary.json。绘图省略箭头以便阅读。');
 s.addImage({path:path.join(ROOT,'figures/06_comment_network.png'),x:.62,y:1.96,w:8.25,h:8.25*870/1569});
 text(s,'节点是账号，线表示评论关系',9.16,1.94,3.45,.86,22,C.green,true);
 text(s,'根评论：留言者 → 帖主\n明确回复：回复者 → 被回复者\n同向多次互动，累加为线的权重',9.16,3.07,3.48,1.58,17.5);
 text(s,'2,932 个有边账号\n4,069 条有向边',9.16,5.06,3.45,.95,23,C.green,true);
 text(s,'忽略方向时，94.4%的账号间接相连',9.16,6.27,3.45,.5,13.5,C.muted);
 note(s,'这张网络图把发言放回了它指向的账号。一个点是一个账号：金色是课程样本中的帖子作者，蓝色是其他参与账号。根评论从留言者指向帖主；明确回复则指向被回复的人。同一方向出现多次，就累加次数。排除84次自我互动后，11,511次事件合成4,069条有向边，涉及2,932个账号。忽略方向时，94.4%的账号可以沿路径间接串起来。但图上连在一起，并不意味着每个人都在彼此聊天。接下来直接看明确回复的方向。',55,'解释节点、两种连线及重复互动加权，跳过其他指标。');
}
// 10 — Native role chart with the correct denominator.
{
 const s=slide('明确回复中，近九成是帖主在回话','评论关系网络','来源：extension_comment_roles.csv。分母为4,902次非自我明确回复，排除根评论。');
 label(s,'明确回复的角色方向（%）',.7,1.88,7);
 chart(s,pres.ChartType.bar,[{name:'明确回复占比',labels:['帖主 → 其他用户','其他用户 → 帖主','其他用户 → 其他用户'],values:[4361/4902*100,444/4902*100,97/4902*100]}],.64,2.4,8.2,3.8,
  {barDir:'bar',showLegend:false,valAxisMaxVal:100,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:14,gapSizePct:100});
 text(s,'89.0%',9.18,2.55,3.4,.88,45,C.green,true);
 text(s,'4,361次\n帖主回复其他用户',9.18,3.7,3.4,.93,20);
 text(s,'其他参与者彼此接话，\n只占2.0%。',9.18,5.36,3.4,.94,20,C.orange,true);
 note(s,'只看明确的回复，帖主回复其他用户有4,361次，占89%；其他用户回复帖主占9.1%；其他用户彼此回复只有97次，占2%。这里的分母是4,902次明确回复，根评论没有算进来。因此，这批记录里最常见的是读者面向帖主留言，再由帖主回复。上一页网络里大多数账号能间接连起来，更多横向对话却没有随之出现。评价评论区时，只看是否连通是不够的，还要看究竟是谁在接话。',50,'保留89%与2%两个数字，强调分母是明确回复。');
}
// 11 — Two actual anonymized accounts; a diagram instead of a dense metric table.
{
 const s=slide('收到的留言差不多，参与人数却很不一样','评论关系网络','来源：network_nodes.csv。次数为收到的非自我互动事件；人数为不同发送者。账号均已匿名化。');
 const data=[['U1528','1,378','53','少数发送者反复留言',C.green],['U0948','1,275','1,091','更多不同账号参与',C.orange]];
 data.forEach((a,i)=>{
  const x=.7+i*6.25;
  rect(s,x,1.94,5.9,4.72,i===0?C.light:C.paleOrange);
  text(s,a[0],x+.27,2.2,5.3,.38,19,a[4],true);
  text(s,a[1]+' 次',x+.27,2.91,5.3,.72,36,C.ink,true);
  text(s,'收到的互动事件',x+.27,3.76,5.3,.4,16,C.muted);
  text(s,a[2]+' 人',x+.27,4.42,5.3,.75,37,a[4],true);
  text(s,'不同发送者',x+.27,5.29,5.3,.38,16,C.muted);
  text(s,a[3],x+.27,6.05,5.3,.36,19,C.ink,true);
 });
 note(s,'这两个真实的匿名账号，很能说明只看评论总量会漏掉什么。U1528收到1,378次互动，来自53个人；U0948收到1,275次，却来自1,091个人。两者的次数接近，参与面却很不一样。前者已有发送者反复留言的份量较大，后者收到更多不同账号的留言。对社区活跃程度的判断，应同时看次数、不同参与人数，以及这些留言有没有得到回应。',60,'讲两个账号的次数和人数，不展开技术指标。');
}
// 12 — Time context without introducing another full set of network measures.
{
 const s=slide('多数评论，出现在发帖后的前七天','评论发生时间','来源：extension_summary.json；extension_comment_timing.csv。分母为11,595条评论，均从发帖起算。');
 text(s,'累计评论占比',.7,1.88,8,.32,13,C.muted);
 chart(s,pres.ChartType.bar,[{name:'累计占比',labels:['发帖后24小时内','发帖后7天内'],values:[64.5,82.2]}],.66,2.45,8.2,3.65,
  {barDir:'bar',showLegend:false,valAxisMaxVal:100,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:15,gapSizePct:100});
 text(s,'早期留言值得关注',9.2,2.55,3.4,.85,24,C.green,true);
 text(s,'可以优先观察\n前24小时的留言，\n以及哪些还没有回复。',9.2,3.95,3.4,1.34,21);
 text(s,'及时回复是否带来后续互动，\n仍需要另行检验。',9.2,5.81,3.4,.8,16,C.muted);
 note(s,'时间上，64.5%的评论出现在发帖后24小时内，82.2%在发帖后七天内。两个比例都是从发帖时间开始算，且七天内包含前24小时。这给实际观察评论区提供了一个具体起点：先看早期留言和未得到回应的留言。当然，这里描述的是评论何时出现，还没有检验及时回复是否会带来更多后续互动。我们把它作为后续观察的方向，不当成已经验证的运营效果。',40,'若时间有限，本页一句带过：近三分之二评论在发帖后24小时内出现。');
}
// 13 — Single closing page, with concrete consequences and precise limits.
{
 const s=slide('判断高赞与活跃，还要看哪些信息','结论','完整方法与结果见分析报告；后附2页答疑，不计入主讲。',{dark:true});
 const rows=[['用词','高赞帖常用的词，还不能直接变成高赞模板。'],
  ['内容','看一种主题有多常见，也要看有多少人在写。'],
  ['互动','除了留言次数，还要看参与人数、谁在回复。']];
 rows.forEach((r,i)=>{const y=1.99+i*1.19;dot(s,.75,y+.08,.18,i===2?C.orange:'89AC97');text(s,r[0],1.2,y,1.1,.47,22,'B9D3C4',true);text(s,r[1],2.62,y,9.8,.75,24,C.white);});
 rect(s,.7,5.76,11.95,.96,'295347');
 text(s,'解释范围：100位课程样本作者；正文与评论覆盖不全；缺少真实曝光和统一采集时点。',.9,5.94,11.54,.34,14.5,'DDE9E1');
 text(s,'这些结果描述样本内关联，后续需要补齐记录并统一观察窗口。',.9,6.36,11.54,.28,14.5,'DDE9E1');
 note(s,'最后回到最初的问题。关于内容，我们没有找到一套可以直接套用的高赞用词；判断一种主题常不常见，还要留意是不是少数作者写得多。关于互动，评论往来主要围绕帖主展开，留言次数、参与人数和回复情况需要一起看。这也意味着，如果以后观察一个社区是否活跃，我们会少问一句“有多少评论”，多问一句“有多少不同的人参与，谁在接话”。这些判断限于课程的100位作者样本，正文、评论和曝光信息仍有缺口，后续需要统一观察窗口，再检验具体做法的效果。谢谢大家。',65,'只讲三条判断，最后用一句话交代样本与观察性边界。');
}
// Appendix A1 — retained for questions, after the conclusion.
{
 const s=slide('方法答疑：怎样比较文字与点赞？','答疑备用 · A1','来源：报告§2.2—2.3、附录A.1；code/text_dictionary.json。',{appendix:true});
 table(s,['文字线索','如何记录'],[
  ['正文长度','ln(1+清理后字符数)'],['自律 / 目标','坚持、自律、目标等词表命中'],['社交 / 互助','大家、小伙伴、谢谢、一起等词表命中'],
  ['积极表达','开心、快乐、喜欢、哈哈等词表命中'],['问号','全角或半角问号，出现记1']
 ],.67,1.98,6.15,[2.05,4.1],{fontSize:15,rowH:.61});
 text(s,'主模型 M3',7.3,2.09,5.15,.45,24,C.green,true);
 text(s,'因变量：ln(1+点赞数)\n作者固定效应 + 北京时间日期固定效应\n控制媒体形式、业务类型、时段等条件\n标准误按100位作者聚类\n五项核心系数作BH多重检验校正',7.3,2.91,5.2,2.85,18);
 text(s,'没有统一的真实曝光，固定效应也不能把关联解释成因果。',.7,6.37,11.9,.42,18,C.orange,true);
 note(s,'这些词典只识别字面表达，不是对用户心理或情绪的测量。正文缺失帖保留，文本计数设零，并加入正文是否可用的标记。主模型利用作者内变化，也控制日期及已记录情境；标准误按作者聚类，五项核心特征做BH校正。完整模型对照和敏感性分析见报告附录。',0);
}
// Appendix A2 — references for scope, timing and interpretation questions.
{
 const s=slide('口径答疑：几个容易混淆的比例与时间窗','答疑备用 · A2','来源：summary.json；supplemental_summary.json；extension_summary.json。',{appendix:true});
 table(s,['指标','分母与含义','结果'],[
  ['明确回复中由帖主发出','4,902次非自我明确回复；排除根评论','89.0%'],
  ['根评论后7天内直接回复覆盖','6,609条外来根评论；要求直接回复根评论本身','54.0%'],
  ['根评论线程中有帖主参与','6,609条外来根评论；帖主在串中回复即计入，不限7天','57.0%'],
  ['评论在发帖后7天内出现','11,595条评论；从发帖时间起算','82.2%']
 ],.67,2.01,12,[3.4,6.6,2],{fontSize:15.3,rowH:.77});
 text(s,'“根评论后7天”和“发帖后7天”起点不同；未观察到回复，不等于实际没有回复。',.7,6.23,11.9,.6,17.5,C.orange,true);
 note(s,'直接回复要求回复ID和被回复用户都明确指向根评论，七天从根评论时间开始。线程参与只要求帖主在这条留言串内出现，并不一定直接回复根评论本人。时序中的七天则从发帖开始。互惠率还属于另一种以账号间去重边为分母的结构指标，不能拿来当评论回复率。',0);
}

async function main(){
 if(M.filter(s=>!s.appendix).length!==MAIN)throw Error('Expected thirteen main slides');
 await pres.writeFile({fileName:OUT+'.pptx'});
 const zip=await JSZip.loadAsync(fs.readFileSync(OUT+'.pptx'));
 const repairs=[];
 for(const n of Object.keys(zip.files).filter(n=>/^ppt\/charts\/chart\d+\.xml$/.test(n))){
  let x=await zip.file(n).async('string');
  const declared=new Set([...x.matchAll(/<c:(?:catAx|valAx|serAx)\b[^>]*>([\s\S]*?)<\/c:(?:catAx|valAx|serAx)>/g)].map(m=>m[1].match(/<c:axId\s+val="([^"]+)"\s*\/>/)[1]));
  let count=0;x=x.replace(/<c:barChart\b[^>]*>[\s\S]*?<\/c:barChart>/g,b=>b.replace(/<c:axId\s+val="([^"]+)"\s*\/>/g,(all,id)=>{if(declared.has(id))return all;count++;return '';}));
  zip.file(n,x);repairs.push({part:n,orphanAxisReferencesRemoved:count});
 }
 for(const n of Object.keys(zip.files).filter(n=>/^ppt\/slides\/_rels\/slide\d+\.xml\.rels$/.test(n))){
  zip.file(n,(await zip.file(n).async('string')).replace(/Target="\/ppt\/charts\//g,'Target="../charts/'));
 }
 fs.writeFileSync(OUT+'.pptx',await zip.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
 fs.writeFileSync(path.join(QA,'chart_axis_repairs.json'),JSON.stringify(repairs,null,2));
 fs.writeFileSync(path.join(QA,'slides_manifest.json'),JSON.stringify(M,null,2));
 let elapsed=0;const clock=n=>`${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;
 const scripts=M.map(s=>{const start=elapsed;if(!s.appendix)elapsed+=s.seconds;return `${s.appendix?'答疑':'第'+s.page+'页'}｜${s.title}\n${s.appendix?'不计入主讲':clock(start)+'—'+clock(elapsed)+'，建议'+s.seconds+'秒'}\n\n${s.speech}\n\n10分钟版提示：${s.short||'答疑时按需使用'}\n来源：${s.source}\n`;}).join('\n\n');
 const timing={main_slides:MAIN,appendix_slides:2,total_slides:M.length,speech_and_pointing_seconds:elapsed,transition_seconds:30,target_seconds:elapsed+30,
  normal_mode:'13页全部讲，约12分30秒；逐页预算含读图和停顿，另留30秒转场。',
  short_mode:'约10分钟：第3页35秒，第4页45秒，第5页60秒，第6页45秒，第7页45秒，第8页35秒，第9页40秒，第11页55秒，第12页25秒，第13页55秒；其余按标准预算。',
  short_mode_seconds:[25,60,35,45,60,45,45,35,40,50,55,25,55].reduce((a,b)=>a+b,0)+30,
  longer_mode:'接近15分钟：按标准版讲完，增加第5页模型解释、第8页分母对比和第11页账号案例；答疑页仍按提问使用。',
  note:'时间为排练预算，实际需按语速与现场指图校准。',narration_characters:M.filter(s=>!s.appendix).reduce((a,s)=>a+s.speech.length,0)};
 fs.writeFileSync(path.join(QA,'timing_plan.json'),JSON.stringify(timing,null,2));
 fs.writeFileSync(OUT+'_逐页讲稿与修改说明.txt',`Keep社区内容表达与互动反馈｜10—15分钟合并版\n\n13页主讲 + 2页答疑。正常版讲述预算${clock(elapsed)}，另留30秒转场，总目标${clock(elapsed+30)}。\n10分钟版本目标${clock(timing.short_mode_seconds)}：${timing.short_mode}\n每页讲稿亦写入PPT备注。答疑页放在结论之后，无需主讲。\n\n修改说明\n1. 对照了37页《章节清晰_讲述增强版》、18页精简版及同伴30页版；保留同伴的真实署名、深绿基调和清楚顺序，保留本组的数字口径与具体案例。\n2. 删除独立章节隔页、六章目录、多次重复的结论和大段方法铺陈；方法明细移到答疑，讲述按问题展开。\n3. 原稿的机器感主要来自固定栏目、长标题、每页满三点、整段报告文字和泛化建议。本版减少这些模板，用可核对的数字与账号例子承担解释，版式随内容变化。\n4. 将“积极表达由优势转为劣势”改成具体的前后比较，同时保留q=0.079，避免暗示用词导致点赞下降。\n5. 把89%的分母写清，把直接回复与线程参与分开；没有新增统计模型、重新跑分析，也没有编造评论或用户动机。\n\n排练提示\n正常讲不逐项念回归表；第5页只讲积极表达一行和0.065个百分点。第8页先指分母，再指百分比。第11页留时间让听众对照人数。\n\n${scripts}`);
 const peer='/Users/lchen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_pweb8scv3czt22_1e94/msg/file/2026-10/Keep社区内容表达与互动反馈分析汇报';
 const inputs=[...['演示文稿_Phase2_章节清晰_讲述增强版','演示文稿_Phase2_15-20分钟精简版'].flatMap(n=>[path.join(ROOT,n+'.pptx'),path.join(ROOT,n+'.pdf')]),peer+'.pptx',peer+'.pdf'];
 fs.writeFileSync(path.join(QA,'protected_inputs.json'),JSON.stringify(inputs.map(f=>({file:f,sha256:crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')})),null,2));
 console.log(JSON.stringify({pptx:OUT+'.pptx',native_charts:M.reduce((n,s)=>n+s.charts.length,0),timing},null,2));
}
main().catch(e=>{console.error(e);process.exit(1);});
