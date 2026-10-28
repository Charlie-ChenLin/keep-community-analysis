/* Editable scatter panels with horizontal 95% intervals. No bitmap plots.
 * Use worksheet-linked native line series for the intervals so that both
 * PowerPoint and LibreOffice show the same endpoints and caps.
 * Postprocess after writeFile() and before zipping the deck.
 */
'use strict';

const TERMS = [
  ['self_discipline', '自律 / 目标'],
  ['social_address', '社交 / 互助'],
  ['positive_expression', '积极表达'],
];
const MODELS = [
  ['M3_', '主模型'], ['R1_', '仅可见正文'], ['R2_', '去最高1%'],
  ['R3_', '作者等权'], ['R4_', 'PPML计数'],
];
const pending = [];

function addSensitivityPanels(pres, slide, coefRows, palette = {}) {
  const font = palette.font || 'Arial Unicode MS';
  const ink = palette.ink || '20332F';
  const green = palette.green || '245C4F';
  const muted = palette.muted || '65756F';
  const orange = palette.orange || 'B97339';
  const metadata = [];
  const frame = { y: 2.2, w: 3.45, h: 2.35 };
  const layout = { x: .025, y: .06, w: .95, h: .80 };
  const xmin = -.4, xmax = .2;
  const yvalues = [5, 4, 3, 2, 1];

  TERMS.forEach(([term, title], index) => {
    const rows = MODELS.map(([prefix]) => {
      const row = coefRows.find(r => r.model.startsWith(prefix) && r.term === term);
      if (!row) throw new Error('Missing sensitivity coefficient: ' + prefix + term);
      const point = { model: row.model, coef: +row.coef, low: +row.ci_low, high: +row.ci_high, p: +row.p };
      if (![point.coef, point.low, point.high, point.p].every(Number.isFinite) || point.low > point.coef || point.coef > point.high) {
        throw new Error('Invalid sensitivity interval: ' + prefix + term);
      }
      return point;
    });
    const x = 1.85 + index * 3.70;
    const name = title + '（敏感性）';
    slide.addText(title, {
      x, y: 1.79, w: frame.w, h: .32, margin: 0,
      fontFace: font, fontSize: 16, color: index === 2 ? orange : green,
      bold: true, align: 'center', lang: 'zh-CN',
    });
    slide.addChart(pres.ChartType.scatter, [
      { name: '系数', values: rows.map(r => r.coef) },
      { name, values: yvalues.slice() },
      // This reference series is replaced with a two-point vertical line.
      { name: '零点参照', values: [.5, 5.5, .5, 5.5, .5] },
    ], {
      x, y: frame.y, w: frame.w, h: frame.h, layout: { ...layout },
      fontFace: font, lang: 'zh-CN', barDir: 'col',
      showTitle: false, showLegend: false, showLabel: false,
      showValue: false, showBorder: false,
      chartColors: [index === 2 ? orange : green, 'AAB8B0'],
      lineSize: 0, lineDataSymbol: 'circle', lineDataSymbolSize: 5,
      lineDataSymbolLineSize: 0,
      catAxisMinVal: xmin, catAxisMaxVal: xmax, catAxisMajorUnit: .2,
      catAxisLabelFontFace: font, catAxisLabelFontSize: 10.5,
      catAxisLabelColor: muted, catAxisLineShow: false,
      catGridLine: { color: 'E7ECE9', width: .5 },
      valAxisMinVal: .5, valAxisMaxVal: 5.5, valAxisMajorUnit: 1,
      valAxisHidden: true, valAxisLineShow: false,
      valAxisLabelFormatCode: '0.0', valAxisCrossesAt: .5,
      catAxisCrossesAt: xmin,
      valGridLine: { style: 'none' },
    });
    if (index === 0) {
      MODELS.forEach(([, label], i) => {
        const pointY = frame.y + frame.h * (layout.y + layout.h * ((5.5 - yvalues[i]) / 5));
        slide.addText(label, {
          x: .70, y: pointY - .12, w: 1.08, h: .25, margin: 0,
          fontFace: font, fontSize: 11, color: ink, align: 'right',
          lang: 'zh-CN',
        });
      });
    }
    const meta = { term, title, seriesName: name, rows, x, ...frame, range: [xmin, xmax], color: index === 2 ? orange : green };
    pending.push(meta);
    metadata.push(meta);
  });
  return { chartCount: TERMS.length, panels: metadata, note: '点为系数，横线为原始95%区间；PPML与OLS尺度不同，不比较系数绝对大小。' };
}

function literal(values) {
  return '<c:numLit><c:formatCode>General</c:formatCode><c:ptCount val="' + values.length + '"/>' +
    values.map((v, i) => '<c:pt idx="' + i + '"><c:v>' + v + '</c:v></c:pt>').join('') + '</c:numLit>';
}

function cachedReference(column, values) {
  return '<c:numRef><c:f>Sheet1!$' + column + '$2:$' + column + '$' + (values.length+1) + '</c:f><c:numCache>' +
    '<c:formatCode>General</c:formatCode><c:ptCount val="' + values.length + '"/>' +
    values.map((v,i)=>'<c:pt idx="'+i+'"><c:v>'+v+'</c:v></c:pt>').join('') + '</c:numCache></c:numRef>';
}

async function writeIntervalWorkbook(zip, chartPart, intervals) {
  const path = require('path');
  const JSZip = require('jszip');
  const relPart = chartPart.replace('/charts/', '/charts/_rels/') + '.rels';
  const rel = await zip.file(relPart).async('string');
  const target = rel.match(/Target="([^"]+\.xlsx)"/)[1];
  const workbookPart = path.posix.normalize(path.posix.join(path.posix.dirname(chartPart), target));
  const book = await JSZip.loadAsync(await zip.file(workbookPart).async('nodebuffer'));
  let sheet = await book.file('xl/worksheets/sheet1.xml').async('string');
  const rows = new Map();
  for(const m of sheet.matchAll(/<row\b[^>]*r="(\d+)"[^>]*>[\s\S]*?<\/row>/g)) rows.set(+m[1],m[0]);
  for(let n=1;n<=7;n++) {
    let row=rows.get(n)||'<row r="'+n+'"></row>';
    const extra=intervals.map((line,i)=> {
      const xc=String.fromCharCode(68+i*2), yc=String.fromCharCode(69+i*2);
      return n===1 ? '<c r="'+xc+'1" t="inlineStr"><is><t>'+line.label+' CI x</t></is></c><c r="'+yc+'1" t="inlineStr"><is><t>'+line.label+' CI y</t></is></c>' :
        '<c r="'+xc+n+'"><v>'+line.x[n-2]+'</v></c><c r="'+yc+n+'"><v>'+line.y[n-2]+'</v></c>';
    }).join('');
    rows.set(n,row.replace('</row>',extra+'</row>').replace(/spans="[^"]+"/,'spans="1:13"'));
  }
  sheet=sheet.replace(/<sheetData>[\s\S]*?<\/sheetData>/,'<sheetData>'+[...rows.values()].join('')+'</sheetData>')
    .replace(/<dimension ref="[^"]+"\s*\/>/,'<dimension ref="A1:M7"/>');
  book.file('xl/worksheets/sheet1.xml',sheet);
  zip.file(workbookPart,await book.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
}

async function postprocessSensitivityCharts(zip, explicitMetadata) {
  const specs = explicitMetadata || pending;
  const fixed = [];
  for (const part of Object.keys(zip.files).filter(n => /^ppt\/charts\/chart\d+\.xml$/.test(n))) {
    let xml = await zip.file(part).async('string');
    const spec = specs.find(p => xml.includes(p.seriesName));
    if (!spec) continue;
    if (!xml.includes('<c:scatterChart>')) throw new Error('Sensitivity chart is not scatter: ' + part);
    const color=spec.color || (spec.term==='positive_expression'?'B97339':'245C4F');
    const intervals=spec.rows.map((row,i)=>({label:MODELS[i][1],x:[row.low,row.low,row.low,row.high,row.high,row.high],y:[5-i-.08,5-i+.08,5-i,5-i,5-i-.08,5-i+.08]}));
    await writeIntervalWorkbook(zip,part,intervals);
    let count=0;
    xml=xml.replace(/<c:ser>[\s\S]*?<\/c:ser>/g,series=> {
      if(series.includes(spec.seriesName)) {
        count++;
        return series.replace(/<c:errBars>[\s\S]*?<\/c:errBars>/g,'');
      }
      if(series.includes('零点参照')) {
        series=series.replace(/<c:spPr>[\s\S]*?<\/c:spPr>/,'<c:spPr><a:ln w="15875"><a:solidFill><a:srgbClr val="65756F"/></a:solidFill><a:prstDash val="dash"/></a:ln></c:spPr>')
          .replace(/<c:marker>[\s\S]*?<\/c:marker>/,'<c:marker><c:symbol val="none"/></c:marker>')
          .replace(/<c:xVal>[\s\S]*?<\/c:xVal>/,'<c:xVal>'+literal([0,0])+'</c:xVal>')
          .replace(/<c:yVal>[\s\S]*?<\/c:yVal>/,'<c:yVal>'+literal([.5,5.5])+'</c:yVal>');
      }
      return series;
    });
    if(count!==1) throw new Error('Sensitivity point series count: '+count);
    const lines=intervals.map((line,i)=> {
      const xc=String.fromCharCode(68+i*2), yc=String.fromCharCode(69+i*2);
      return '<c:ser><c:idx val="'+(i+2)+'"/><c:order val="'+(i+2)+'"/><c:tx><c:v>'+line.label+'95%区间</c:v></c:tx>' +
        '<c:spPr><a:ln w="12700"><a:solidFill><a:srgbClr val="'+color+'"/></a:solidFill></a:ln></c:spPr><c:marker><c:symbol val="none"/></c:marker>' +
        '<c:xVal>'+cachedReference(xc,line.x)+'</c:xVal><c:yVal>'+cachedReference(yc,line.y)+'</c:yVal><c:smooth val="0"/></c:ser>';
    }).join('');
    xml=xml.replace(/(<c:scatterChart>[\s\S]*?)(<c:axId)/, (_all,before,axis)=>before+lines+axis);
    // Draw the estimate markers last so interval lines cannot cover them.
    const allSeries=[...xml.matchAll(/<c:ser>[\s\S]*?<\/c:ser>/g)].map(m=>m[0]);
    const ordered=[...allSeries.filter(v=>v.includes('95%区间')), ...allSeries.filter(v=>v.includes('零点参照')), ...allSeries.filter(v=>v.includes(spec.seriesName))];
    if(ordered.length!==7) throw new Error('Sensitivity rendering series count: '+ordered.length);
    const reordered=ordered.map((series,i)=>series.replace(/<c:idx val="\d+"\/>/,'<c:idx val="'+i+'"/>').replace(/<c:order val="\d+"\/>/,'<c:order val="'+i+'"/>')).join('');
    let emitted=false;
    xml=xml.replace(/<c:ser>[\s\S]*?<\/c:ser>/g,()=> {if(emitted)return '';emitted=true;return reordered;});
    zip.file(part,xml);
    fixed.push({part,term:spec.term,horizontalErrors:5,zeroReference:true,intervalRepresentation:'native scatter line series with worksheet-linked endpoints'});
  }
  if(fixed.length!==specs.length) throw new Error('Expected '+specs.length+' sensitivity charts, patched '+fixed.length);
  return fixed;
}

module.exports = { addSensitivityPanels, postprocessSensitivityCharts, TERMS, MODELS };
