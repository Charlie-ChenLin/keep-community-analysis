/* Integrate study framing, methods and reply definitions into the presentation body.
 * Source results are read only. Charts, tables and text remain editable.
 * Run: NODE_PATH=/tmp/keep-slides-tools/node_modules node code/build_merged_presentation.js
 */
const pptxgen = require('pptxgenjs');
const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..');
const QA = path.join(ROOT, 'validation/slides_integrated_10_15');
const OUT = path.join(ROOT, 'Keep社区内容表达与互动反馈_10-15分钟正文整合版');
fs.mkdirSync(QA, {recursive:true});
const pres = new pptxgen();
pres.layout='LAYOUT_WIDE';
pres.author='陈霖、董依心'; pres.company='社交媒体网络分析课程小组';
pres.title='Keep社区内容表达与互动反馈分析';
pres.subject='10—15分钟课堂汇报；16页均为正文';
pres.lang='zh-CN';
const F='Arial Unicode MS';
pres.theme={headFontFace:F,bodyFontFace:F,lang:'zh-CN'};
const C={ink:'20332F',green:'245C4F',deep:'173F36',muted:'65756F',light:'EDF4F0',
  pale:'F6F8F7',line:'DFE6E2',orange:'B97339',paleOrange:'F8F0E8',gray:'AAB8B0',white:'FFFFFF',purple:'6F5B8C'};
const M=[]; const MAIN=16;
const FOOTERS=[
 '社交媒体网络分析 · 课程小组汇报',
 '研究设计 · 预期是待检验的可能解释，是否成立由后文分析回答。',
 '数据：课程提供的Keep样本；帖子发表于2020年11—12月（UTC）。',
 '原报告第3章 · 描述性均值比较，尚未调整作者与发布情境。',
 '原报告第4章 · 四类表达可重叠；词典仅识别字面用词。',
 '原报告第2章、附录A.1 · 文字编码、比较方式与统计检验。',
 '原报告第4章 · 主模型；五项文字线索采用BH多重检验校正。',
 '原报告第5章 · 2,470帖、86位作者；两组使用相同的主题分类。',
 '原报告第6章 · 角色按所在帖子确定；词类可重叠。',
 '原报告第6—7章 · 同为6,609条外来根评论，回复规则和时间范围不同。',
 '原报告第6章 · 仅看根评论发出后7天内、明确指向该根评论的最早帖主回复。',
 '原报告第7章，图11 · 金色为样本作者，蓝色为其他账号；图中省略箭头。',
 '原报告第7章 · 分母：4,902次非自我明确回复，排除根评论。',
 '原报告第7章 · 次数为收到的互动事件，人数为不同发送者；账号已匿名化。',
 '原报告第7章 · 分母：11,595条评论；时间从发帖起算，区别于根评论起算。',
 '完整方法与结果见原报告。'
];
const STANDARD_SECONDS=[20,60,45,40,50,60,70,60,50,60,60,45,45,55,35,55];
const SHORT_SECONDS=[15,45,30,25,35,45,50,40,35,45,45,30,35,45,25,45];

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
function slide(title,section,source,{dark=false,clean=false}={}){
 const s=pres.addSlide();s.background={color:dark?C.deep:C.white};
 s._m={page:M.length+1,title,section,source,appendix:false,text:[],charts:[],seconds:0,speech:''};M.push(s._m);
 if(!clean){
  text(s,section,.62,.34,11.6,.25,11,dark?'C5D9D0':C.muted);
  text(s,title,.62,.88,12,.7,29,dark?C.white:C.ink,true);
 }
 text(s,FOOTERS[M.length-1]||source,.62,7.08,11.3,.23,9,dark?'B3CFC1':C.muted);
 text(s,`${String(M.length).padStart(2,'0')} / ${MAIN}`,11.92,7.06,.78,.26,10.5,dark?'BDD3C8':C.muted,false,{align:'right'});
 return s;
}
function note(s,speech,seconds=0,short=''){
 s._m.speech=speech;s._m.seconds=STANDARD_SECONDS[s._m.page-1];s._m.short=short;
 s._m.shortSeconds=SHORT_SECONDS[s._m.page-1];
 s.addNotes(`标准版建议${s._m.seconds}秒；压缩版${s._m.shortSeconds}秒\n\n${speech}${short?'\n\n压缩讲法：'+short:''}\n\n数据来源：${s._m.source}`);
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
// 2 — One general question, then three specific questions and possible answers.
{
 const s=slide('研究背景、问题与预期','研究设计','来源：原报告§1研究背景与研究问题；预期为解释框架，不是已验证结论。');
 text(s,'健身社区里，什么内容受到关注，人们又怎样交流？',.7,1.78,11.9,.53,25,C.green,true);
 text(s,'Keep用户既记录运动，也分享经验和生活感受。点赞是可见的反馈，\n评论进一步记录了谁在留言、谁在回应。',.72,2.48,11.8,.68,17.5,C.ink);
 text(s,'由总问题细化的三个问题',.88,3.36,5.5,.35,16,C.green,true);
 text(s,'预期：可能的回答与解释',7.06,3.36,5.3,.35,16,C.green,true);
 const rows=[
  ['01  哪些内容更常见，点赞集中在哪里？','运动记录之外，可能也有生活分享；\n媒体反馈可能不同，高赞帖也可能拉高均值。'],
  ['02  怎样写、谈什么，与点赞有关吗？','自律、积极表达或提问可能对应更多点赞；\n调整作者与发布情境后，差异也可能减弱。'],
  ['03  谁在留言、谁在接话，参与面有多广？','读者可能更多鼓励，帖主更多回应；\n评论多既可能来自多人，也可能来自重复往来。']
 ];
 rows.forEach((r,i)=>{const y=3.9+i*.96;rect(s,.7,y,11.95,.88,i===1?C.pale:C.light);text(s,r[0],.89,y+.18,5.7,.55,18,C.ink,true);text(s,r[1],7.06,y+.13,5.34,.64,16.5,C.ink);});
 note(s,'我们先从一个总问题出发：健身社区里，什么内容受到关注，人们又怎样交流？背景是，Keep里的发帖不只有运动打卡，也包含经验和生活分享，点赞与评论提供了两类能观察的反馈。我们把总问题拆成三个方面：第一，内容和点赞怎样分布，是否有少量高赞帖拉高均值；第二，用词和主题是否与点赞相关，调整作者与发布情境后差异还在不在；第三，评论由谁发起、谁来回应，热闹是来自更多人还是重复往来。右栏是用来组织分析的可能解释，下面会分别用数据检验，并不先把它们当结论。',60,'先讲总问题和背景，再逐行串起三个问题与对应预期，不逐字读右栏。');
}
// 3 — Data coverage, now separate from the study framing.
{
 const s=slide('这些结论，来自100位作者的帖子与评论','样本与记录范围','来源：summary.json；报告§2—3。帖子发表于2020年11—12月（UTC）。');
 text(s,'先分清样本规模，以及哪些内容被实际记录下来。',.65,1.78,11.8,.5,23,C.green,true);
 value(s,'9,532','帖子 · 100位作者',.7,2.65,3.7);
 value(s,'11,595','去重后评论',4.8,2.65,3.6);
 value(s,'1,323','有采集到评论的帖子',8.8,2.65,3.7);
 rect(s,.67,4.55,5.75,1.66,C.light);rect(s,6.75,4.55,5.9,1.66,C.paleOrange);
 text(s,'正文覆盖',.9,4.77,5.2,.4,22,C.green,true);
 text(s,'3,984帖缺可用正文，保留并标记\n主题分析另用2,470帖、86位作者',.9,5.34,5.1,.66,18);
 text(s,'评论覆盖',6.98,4.77,5.25,.4,22,C.orange,true);
 text(s,'仅覆盖1,323帖，其他帖记为未知\n未采到评论，不等于实际没有评论',6.98,5.34,5.2,.66,18);
 text(s,'100位作者的抽样机制、实际曝光及统一采集时点未提供。',.7,6.52,11.8,.35,13.5,C.muted);
 note(s,'分析使用课程提供的100位作者、9,532条帖子，以及去重后的11,595条评论。帖子实际发表于2020年11到12月。正文和评论各有缺口：3,984帖没有可用正文，我们保留帖子并单独标记；主题分析则筛出2,470条有效正文，涉及86位作者。评论只覆盖1,323帖，其他帖子没有采到评论，不能按零评论处理。后面不同分析使用的范围也因此不同，结论都只针对这批课程记录。',45,'读出样本规模，重点说明主题子样本与评论覆盖不同。');
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
// 6 — Explain coding and comparison before showing the adjusted result.
{
 const s=slide('尽量比较同一作者在不同帖子中的表达','文字与点赞：比较方法','来源：报告§2.2—2.3、附录A.1；code/text_dictionary.json。');
 label(s,'先记录文字中的5项字面线索，再调整已记录的作者与发布情境差异',.7,1.86,11.9);
 table(s,['文字线索','怎样记录'],[
  ['正文长度','ln(1+清理后字数)'],['自律 / 目标','坚持、自律、目标等'],['社交 / 互助','大家、小伙伴、谢谢、一起等'],
  ['积极表达','开心、快乐、喜欢、哈哈等'],['问号','全角或半角，出现记1']
 ],.7,2.36,6.1,[2,4.1],{fontSize:16,rowH:.55});
 text(s,'除长度外，命中记1；同一帖可同时命中多类。',.74,5.94,6,.5,14,C.muted);
 text(s,'比较结果：ln(1+点赞数)',7.25,2.39,5.15,.45,21,C.green,true);
 rect(s,7.2,3.15,5.43,1.12,C.light);
 text(s,'先扣除作者差异',7.42,3.32,4.98,.35,20,C.green,true);
 text(s,'利用同一作者不同帖子之间的变化',7.42,3.86,4.98,.31,16.5);
 rect(s,7.2,4.64,5.43,1.12,C.paleOrange);
 text(s,'再调整日期与发布情境',7.42,4.8,4.98,.35,20,C.orange,true);
 text(s,'日期、媒体形式、业务类型和时段等',7.42,5.34,4.98,.31,16.5);
 text(s,'标准误按100位作者聚类；五项文字线索统一作BH多重检验校正。',.74,6.57,11.9,.35,15,C.muted);
 note(s,'看到原始均值差异后，我们再说明怎样比较。左边把文字拆成五项字面线索：长度，以及自律、社交、积极表达和问号。除长度外，命中固定词表就记为一，同一帖可以命中多类。右边说明模型要做什么：结果使用一加点赞数的对数，先扣除作者差异，更多利用同一作者不同帖子之间的变化，再调整日期、媒体形式、业务类型和时段。技术上采用作者与日期固定效应，标准误按100位作者聚类。五项文字线索一起看时，还做BH多重检验校正。这些处理改善可比性，但没有实际曝光等完整信息，仍然只能解释关联。',60,'只解释五项线索、同一作者内比较、控制发布情境和多重检验；不逐项念词表。');
}
// 7 — Compact actual results. Statistical table remains editable.
{
 const s=slide('调整之后，还不足以支持一套“高赞用词”','文字与点赞','来源：regression_coefficients.csv（M3）；summary.json。因变量：ln(1+点赞数)。');
 label(s,'系数正负表示关联方向；原始95%区间跨0时，仍同时容纳正、负方向',.7,1.86,11.8);
 const names=['正文长度','自律 / 目标','社交 / 互助','积极表达','问号'];
 table(s,['文字线索','系数','原始95%区间','校正后q值'],coefs.map((r,i)=>[names[i],(+r.coef).toFixed(3),`[${(+r.ci_low).toFixed(3)}, ${(+r.ci_high).toFixed(3)}]`,(+r.q_bh_focal).toFixed(3)]),.67,2.42,8,[2.05,1.2,3.25,1.5],{fontSize:16,rowH:.57,highlight:3});
 text(s,'积极表达的系数转负',9.16,2.49,3.45,.78,23,C.orange,true);
 text(s,'原始 p = 0.016\n校正后 q = 0.079',9.16,3.55,3.45,.8,20);
 text(s,'多重检验后，\n未达到5%标准。',9.16,4.7,3.45,.8,20);
 text(s,'五项文字线索新增的解释度仅0.065个百分点；联合检验 p = 0.130。',.7,6.22,11.8,.44,19,C.green,true);
 note(s,'按刚才的方式调整后，积极表达的系数转为负数，原始均值优势没有延续下来。读这张表时，先看系数方向，再看区间和校正后的q值。其他四项的原始区间都包含零；积极表达原始p值是0.016，但五项一起做多重检验校正后，q值是0.079，没有达到5%的标准。因此，也不能反过来说积极用词会让点赞减少。五项文字线索新增的解释度只有0.065个百分点，联合检验p值为0.130。现有证据还不足以支持一套可照搬的高赞用词。',70,'只指积极表达一行与0.065个百分点，不逐行读表。');
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
 text(s,'主题加入点赞模型后，联合检验 p = 0.166，尚未出现明确的新增解释。',.73,6.66,11.9,.27,12,C.muted);
 note(s,'我们还对有效正文做了主题分析：分词后用TF-IDF和NMF提取预先固定的五类主题，再依据关键词命名。训练和生活占了大多数。不过，按帖子统计会让高产作者被多次计入。让86位作者各占相同权重后，静蹲从3.4%降到0.6%。原因很具体：85条静蹲主题帖子中，78条来自同一个人。因此，一种内容出现得多，不一定意味着很多人都在写。训练和生活并存的格局则保留下来。主题加入点赞模型后的联合检验p值为0.166，也没有给出明确的新增解释，这回应了第二个研究问题。',60,'只讲静蹲85帖中78帖来自一人，再用一句话交代主题模型没有明确的新增点赞关联。');
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
// 10 — Two parallel definitions, no nested-set or funnel implication.
{
 const s=slide('直接回这条留言，和在留言串里接话，怎样区分','评论与回复：先把对象说清楚','来源：supplemental_direct_reply_language.csv；extension_summary.json。');
 text(s,'从6,609条其他用户根评论出发：直接发在帖子下、未指定回复对象的留言。',.72,1.82,11.9,.57,18,C.ink);
 const cols=[
  {x:.72,color:C.green,fill:C.light,title:'直接回复这条根评论',target:'这条根评论',time:'从根评论发出起，限定7天内',pct:'54.0%',count:'3,568 / 6,609条',small:'每条根评论最多记一次'},
  {x:6.97,color:C.orange,fill:C.paleOrange,title:'帖主参与这条留言串',target:'根评论或同串其他留言',time:'不限7天，查看已采集的整条留言串',pct:'57.0%',count:'3,770 / 6,609条',small:'只要帖主在串里回过话，就算参与'}
 ];
 cols.forEach(a=>{
  text(s,a.title,a.x,2.68,5.65,.4,22,a.color,true);
  rect(s,a.x,3.35,5.65,.83,a.fill);
  text(s,'帖主',a.x+.2,3.57,.85,.4,18,C.ink,true);
  line(s,a.x+1.16,3.76,.72,0,a.color,1.6,true);
  text(s,a.target,a.x+2.05,3.58,3.37,.42,17,C.ink);
  text(s,a.time,a.x+.03,4.53,5.58,.43,17,a.color,true);
  text(s,a.pct,a.x+.03,5.22,2.9,.72,36,a.color,true);
  text(s,a.count,a.x+2.9,5.45,2.75,.43,16,C.ink);
  text(s,a.small,a.x+.03,6.14,5.58,.36,15,C.muted);
 });
 text(s,'两种统计的时间范围不同，要分别理解；未观察到回复，也不等于实际没有回复。',.75,6.68,11.9,.3,13.5,C.muted);
 note(s,'先把回复对象说清楚。根评论是其他用户直接发在帖子下、没有指定回复对象的留言，一共有6,609条。我们分别做两种统计：左边要求帖主的回复记录明确指向这条根评论，而且发生在根评论发出后七天内，共观察到3,568条，占54%。右边只问帖主是否在整条留言串里回过话，可以直接回根评论，也可以回复同串的其他人，不限七天，共3,770条，占57%。两边时间范围不同，不能把这三个百分点直接解释成“回复别人的比例”。接下来分析鼓励留言时，采用左边较严格的直接回复规则。',60,'用一句话定义根评论，再并列讲54%与57%的对象和时间范围；下一页沿用左边规则。');
}
// 11 — Different denominators explicitly visible.
{
 const s=slide('鼓励留言得到回复时，回复更常带有感谢','评论与直接回复','来源：supplemental_direct_reply_language.csv。配对要求同帖、明确回复根评论、根评论后7天内。');
 text(s,'6,609条外来根评论 → 3,568条观察到帖主直接回复',.7,1.85,11.8,.5,22,C.green,true);
 text(s,'沿用前页的直接回复规则：根评论发出后7天内，取最早一条明确回复。',.73,2.4,11.8,.26,12.5,C.muted);
 text(s,'整组留言中，多少观察到直接回复？',.73,2.68,5.7,.4,19,C.ink,true);
 text(s,'已有回复中，多少带有感谢？',7.03,2.68,5.65,.4,19,C.ink,true);
 const labs=['鼓励 / 赞许留言','未命中该词类'];
 chart(s,pres.ChartType.bar,[{name:'直接回复覆盖',labels:labs,values:[43.4745763,56.2718733]}],.69,3.26,5.76,2.6,
  {barDir:'bar',showLegend:false,valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',chartColors:[C.green],catAxisLabelFontSize:11.5});
 chart(s,pres.ChartType.bar,[{name:'回复含感谢',labels:labs,values:[26.705653,6.3829787]}],6.98,3.26,5.72,2.6,
  {barDir:'bar',showLegend:false,valAxisMaxVal:70,dataLabelFormatCode:'0.0"%"',chartColors:[C.orange],catAxisLabelFontSize:11.5});
 text(s,'分母：各组全部根评论\n513 / 1,180；3,055 / 5,429',.83,6.02,5.65,.68,14,C.muted);
 text(s,'分母：各组已观察到直接回复的评论\n137 / 513；195 / 3,055',7.12,6.02,5.5,.68,14,C.muted);
 note(s,'按前页的直接回复规则，把根评论分为命中鼓励赞许词和未命中两组。左图问，一组全部留言里有多少观察到了七天内直接回复，鼓励组是43.5%，未命中组是56.3%。右图的分母则缩小到已经得到回复的留言，鼓励组的最早回复有26.7%带感谢，另一组为6.4%。这说明回复中感谢更多，和整组留言更容易得到回复，是不同的问题。两幅图的分母就写在下方，不能把它们当成同一种回复率。',60,'先说左图分母是全部根评论，右图只看已回复记录，再读两个方向。');
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
 label(s,'4,902次非自我明确回复：排除根评论，再看回复的角色方向（%）',.7,1.88,11.8);
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
 text(s,'从发帖时间起算的累计评论占比（不同于前面的根评论后7天）',.7,1.88,11.8,.32,13,C.muted);
 chart(s,pres.ChartType.bar,[{name:'累计占比',labels:['发帖后24小时内','发帖后7天内'],values:[64.5,82.2]}],.66,2.45,8.2,3.65,
  {barDir:'bar',showLegend:false,valAxisMaxVal:100,dataLabelFormatCode:'0.0"%"',catAxisLabelFontSize:15,gapSizePct:100});
 text(s,'早期留言值得关注',9.2,2.55,3.4,.85,24,C.green,true);
 text(s,'可以优先观察\n前24小时的留言，\n以及哪些还没有回复。',9.2,3.95,3.4,1.34,21);
 text(s,'及时回复是否带来后续互动，\n仍需要另行检验。',9.2,5.81,3.4,.8,16,C.muted);
 note(s,'时间上，64.5%的评论出现在发帖后24小时内，82.2%在发帖后七天内。两个比例都是从发帖时间开始算，且七天内包含前24小时。这给实际观察评论区提供了一个具体起点：先看早期留言和未得到回应的留言。当然，这里描述的是评论何时出现，还没有检验及时回复是否会带来更多后续互动。我们把它作为后续观察的方向，不当成已经验证的运营效果。',40,'若时间有限，本页一句带过：近三分之二评论在发帖后24小时内出现。');
}
// 13 — Single closing page, with concrete consequences and precise limits.
{
 const s=slide('判断高赞与活跃，还要看哪些信息','结论','完整方法与结果见分析报告。',{dark:true});
 const rows=[['用词','高赞帖常用的词，还不能直接变成高赞模板。'],
  ['内容','看一种主题有多常见，也要看有多少人在写。'],
  ['互动','除了留言次数，还要看参与人数、谁在回复。']];
 rows.forEach((r,i)=>{const y=1.99+i*1.19;dot(s,.75,y+.08,.18,i===2?C.orange:'89AC97');text(s,r[0],1.2,y,1.1,.47,22,'B9D3C4',true);text(s,r[1],2.62,y,9.8,.75,24,C.white);});
 rect(s,.7,5.76,11.95,.96,'295347');
 text(s,'解释范围：100位课程样本作者；正文与评论覆盖不全；缺少真实曝光和统一采集时点。',.9,5.94,11.54,.34,14.5,'DDE9E1');
 text(s,'这些结果描述样本内关联，后续需要补齐记录并统一观察窗口。',.9,6.36,11.54,.28,14.5,'DDE9E1');
 note(s,'最后回到最初的问题。关于内容，我们没有找到一套可以直接套用的高赞用词；判断一种主题常不常见，还要留意是不是少数作者写得多。关于互动，评论往来主要围绕帖主展开，留言次数、参与人数和回复情况需要一起看。这也意味着，如果以后观察一个社区是否活跃，我们会少问一句“有多少评论”，多问一句“有多少不同的人参与，谁在接话”。这些判断限于课程的100位作者样本，正文、评论和曝光信息仍有缺口，后续需要统一观察窗口，再检验具体做法的效果。谢谢大家。',65,'只讲三条判断，最后用一句话交代样本与观察性边界。');
}
async function main(){
 if(M.length!==MAIN)throw Error('Expected sixteen body slides');
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
 const scripts=M.map(s=>{const start=elapsed;elapsed+=s.seconds;return `第${s.page}页｜${s.title}\n${clock(start)}—${clock(elapsed)}，建议${s.seconds}秒；压缩版${s.shortSeconds}秒\n\n${s.speech}\n\n压缩提示：${s.short||'保留本页主要判断。'}\n来源：${s.source}\n`;}).join('\n\n');
 const timing={main_slides:MAIN,appendix_slides:0,hidden_slides:0,total_slides:M.length,speech_and_pointing_seconds:elapsed,transition_seconds:30,target_seconds:elapsed+30,
  standard_seconds_by_page:STANDARD_SECONDS,short_seconds_by_page:SHORT_SECONDS,
  normal_mode:'16页全部为正文，标准预算14分钟；包含读图和停顿，另计30秒转场。',
  short_mode:'按逐页压缩提示讲，约10分20秒；保留研究设计、比较方法和回复定义，不逐项念表。',
  short_mode_seconds:SHORT_SECONDS.reduce((a,b)=>a+b,0)+30,
  note:'时间是排练预算，请按实际语速校准。',narration_characters:M.reduce((a,s)=>a+s.speech.length,0)};
 fs.writeFileSync(path.join(QA,'timing_plan.json'),JSON.stringify(timing,null,2));
 fs.writeFileSync(OUT+'_逐页讲稿与修改说明.txt',`Keep社区内容表达与互动反馈｜正文整合版\n\n16页均为正文，无答疑页或隐藏页。标准预算${clock(elapsed)}，另留30秒转场，总目标${clock(elapsed+30)}。\n压缩版约${clock(timing.short_mode_seconds)}：${timing.short_mode}\n每页讲稿亦写入PPT备注。\n\n这轮怎样改\n1. 封面后第一张正文专门讲研究设计：总问题与背景、三个具体研究问题、各自的可能解释。预期不冒充已经证实的结论或预注册假设。\n2. 将文字编码和比较方法放在原始均值与调整后结果之间，先解释为什么这样比，再看系数。\n3. 用并列的关系示意区分“直接回复根评论”和“在留言串里接话”，讲清54.0%与57.0%的规则、共同分母和不同时间范围。\n4. 89%的明确回复比例留在角色页，82.2%的评论时间占比留在时序页；相关定义和分母在图旁当场说明。\n5. 删除末尾答疑页，更新页码、讲稿和时间安排；保留原版文件。\n\n${scripts}`);
 const peer='/Users/lchen/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_pweb8scv3czt22_1e94/msg/file/2026-10/Keep社区内容表达与互动反馈分析汇报';
 const inputs=[path.join(ROOT,'Keep社区内容表达与互动反馈_10-15分钟合并版.pptx'),path.join(ROOT,'Keep社区内容表达与互动反馈_10-15分钟合并版.pdf'),...['演示文稿_Phase2_章节清晰_讲述增强版','演示文稿_Phase2_15-20分钟精简版'].flatMap(n=>[path.join(ROOT,n+'.pptx'),path.join(ROOT,n+'.pdf')]),peer+'.pptx',peer+'.pdf'];
 fs.writeFileSync(path.join(QA,'protected_inputs.json'),JSON.stringify(inputs.map(f=>({file:f,sha256:crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex')})),null,2));
 console.log(JSON.stringify({pptx:OUT+'.pptx',native_charts:M.reduce((n,s)=>n+s.charts.length,0),timing},null,2));
}
main().catch(e=>{console.error(e);process.exit(1);});
