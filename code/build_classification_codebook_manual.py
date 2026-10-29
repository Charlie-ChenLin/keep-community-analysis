#!/usr/bin/env python3
"""Build the frozen Chinese classification manual from four approved JSON sources.

The generator does not inspect post bodies, annotation packets, predictions, old
features, or outcomes. No external package or network access is required.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_PATHS = {
    "codebook": "code/classification_codebook_v1.json",
    "protocol": "results/classification_rebuild_protocol.json",
    "calibration": "results/classification_codebook_calibration.json",
    "literature": "code/classification_rebuild_literature.json",
}

# All teaching examples below are newly composed. They are not corpus excerpts,
# replacements for development observations, or evidence of class prevalence.
LEAF_EXAMPLES = {
    "exercise": ("今天慢跑了两公里。", "运动项目和动作明确；不据此判断完成质量或长期习惯。"),
    "weight": ("我想把腰围减少两厘米。", "身体形态目标明确；没有运动或饮食证据时不追加相应叶。"),
    "food": ("午餐准备了豆腐和青菜。", "餐食是实质对象；不能补称减脂餐。"),
    "body": ("今天脖子很僵，准备早点休息。", "身体感觉与休息明确；不推断病因或确诊。"),
    "life": ("一次失败不能决定一个人的价值。", "可复述的一般处世命题；无需推断作者的人格。"),
    "social": ("想找一位周末一起散步的伙伴。", "明确结伴诉求；也可标运动，与家庭身份无关。"),
    "family": ("下午陪女儿去上兴趣课。", "亲属和照料日程明确；不补出课程内容或作者职业。"),
    "work_study": ("今晚轮到我值夜班。", "工作班次明确；不由单独收工二字推职业。"),
    "culture": ("这周读完了一本小说。", "阅读成为主题；引语中的书名提及不一概增加本叶。"),
    "weather": ("今天降温八度，风也很大。", "天气描述明确；阳光作为人生隐喻不算天气。"),
    "outing": ("下周去苏州游园，车票已经订好。", "目的地与出行安排明确；地名单独出现不够。"),
    "appearance": ("新买的手套跑步时总往下滑。", "穿着适用性明确；身体外形另属weight。"),
    "platform": ("投屏以后，应用没有保存这次记录。", "工具记录机制明确；不能补出具体运动项目。"),
    "festival": ("祝大家端午安康。", "明确节日对象；周末愉快不足以判为节日。"),
    "religion": ("今天去寺里参加了祈福仪式。", "宗教场所与活动明确；不推断宗派、信仰或虔诚程度。"),
    "commerce": ("这套杯子售价四十元，可办理退换。", "商品交易条款明确；不推断已成交或作者职业。"),
    "home_housing": ("周末安排师傅来修补客厅墙面。", "居住装修成为讨论对象；居家训练中的场所词不自动算。"),
}
LEAF_NEIGHBORS = {
    "commerce": ["food：买菜可同时涉及采购与食物；单有菜名不等于交易。", "platform：应用机制不自动等于商业供给。", "f_sale_offer：内容轴的消费交易可只是自述购买，行为轴的交易告知须有供给或条款。"],
    "home_housing": ["exercise：在家训练的在家只是场所，不等于讨论住房。", "life：本叶指具体居住环境，life叶指可复述的人生处世命题。"],
}
FUNCTION_EXAMPLES = {
    "f_activity_update": ("第三次练习结束，今天做了两组。", "只呈报次数与阶段，不自动标方法建议，也不把完成当自律。"),
    "f_experience_report": ("现在小腿发酸，我有点紧张。", "逐字记录感觉和情感表达，不作医学或心理诊断。"),
    "f_future_intention": ("明晚准备去游泳半小时。", "明确后续安排；尚未发生，不标为已完成。"),
    "f_explanation": ("持续受力会使弹簧发生形变。", "给出可跨事件使用的关系主张；本编码不验证科学正确性。"),
    "f_practical_guidance": ("做这个动作时先扶稳椅背，再缓慢抬腿。", "明确对象、步骤和可执行办法；若另有机制解释可并标。"),
    "f_reflection": ("成长有时意味着接受自己的局限。", "一般价值主张；不推断作者已经接受自己或具有积极人格。"),
    "f_exhortation": ("给自己提个醒：继续坚持！", "明确动员；无内容对象时允许领域未指明。"),
    "f_greeting_wish": ("早上好，祝大家周末愉快。", "问候与祝愿明确；不证明互动已发生或支持有效。"),
    "f_relational_bid": ("有没有人愿意周六一起去公园散步？", "索取共同参与，标本类；若另外索取一个可独立回答的问题，再考虑回应征询。"),
    "f_reader_response_request": ("请大家告诉我，这个按钮该怎么设置？", "明确面向读者索取答案；不是仅凭问号判定。"),
    "f_appraisal": ("这份汤的味道很好。", "对明确对象作评价；不能自动追加自身开心或实际健康获益。"),
    "f_caption": ("雨后湖面。", "可理解的景象题注；不推断作者去过、拍摄过或完成运动。"),
    "f_gratitude": ("谢谢小林帮我找回钥匙。", "明确对象与感谢话语；不据此声称已经测得社会支持或真诚感激。"),
    "f_sale_offer": ("手工围巾一条六十元，支持七天退换。", "具体供给、报价和交易条款；不是机制解释。"),
    "f_other_expression": ("梦里我成了会说话的云，正和月亮下棋。", "明确幻想叙事；须在note描述，不能把其他当无把握的兜底。"),
}
STATUS_ZH = {
    "development_supported_candidate": "开发样本中有重复支持的候选类",
    "sparse_candidate": "稀疏候选",
    "sparse_candidate_added_from_calibration": "校准新增、支持稀疏",
    "candidate": "开发发现候选",
    "provisional_sparse": "暂定稀疏候选",
    "provisional_singleton": "暂定单例候选",
    "added_from_calibration_then_development_rechecked": "校准新增并回查开发",
}


def stringify(value):
    if isinstance(value, list):
        return "；".join(str(x).rstrip("；。") for x in value) + "。"
    return str(value)


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def table(headers, rows):
    lines = ["| " + " | ".join(map(cell, headers)) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(map(cell, row)) + " |" for row in rows)
    return "\n".join(lines)


def load_sources(root):
    data, hashes = {}, {}
    for name, relative in SOURCE_PATHS.items():
        raw = (root / relative).read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        data[name] = json.loads(raw)
    c, cal = data["codebook"], data["calibration"]
    if hashes["codebook"] != cal["codebook_sha256"]:
        raise ValueError("冻结码本SHA-256与校准记录不一致；请先核实版本，生成器不会修改码本。")
    if len(c["content_subdomains"]) != 17 or len(c["functions"]) != 15 or len(c["domains"]) != 6:
        raise ValueError("输入类别数与本版冻结结构不一致。")
    leaves = {x["code"] for x in c["content_subdomains"]}
    parents = {x["code"] for x in c["domains"]}
    if set(c["subdomain_to_parent"]) != leaves or not set(c["subdomain_to_parent"].values()) <= parents:
        raise ValueError("内容叶与展示父组映射不完整。")
    if set(LEAF_EXAMPLES) != leaves or set(FUNCTION_EXAMPLES) != {x["code"] for x in c["functions"]}:
        raise ValueError("合成教学例未覆盖冻结类别。")
    for axis in ("domains", "functions"):
        by_code = {x["code"]: x for x in cal["counts"][axis]}
        for item in c[axis]:
            for metric in ("development_posts", "calibration_posts"):
                if item[metric] != by_code[item["code"]][metric]:
                    raise ValueError(f"{item['code']}的{metric}与校准记录不一致。")
    if cal["changes"] != c["calibration_changes"]:
        raise ValueError("校准变更记录不一致。")
    return data, hashes


def build_manual(data, hashes):
    c = data["codebook"]
    p = data["protocol"]
    cal = data["calibration"]
    lit = data["literature"]
    parent_by_code = {x["code"]: x for x in c["domains"]}
    leaf_by_code = {x["code"]: x for x in c["content_subdomains"]}
    parts = []
    add = parts.append
    add("# Keep主帖分类编码手册 v1\n\n内容对象 × 可观察表达行为；课堂研究与人工复核用。")
    add(f"**冻结版本：** `{c['version']}`。\n\n**编制口径：** 手册按冻结时定义编制；AI检验当前结果见《分类测量重建_实证依据与验证报告》，人审尚未完成，不能写成人工验证通过。\n\n**冻结快照中的状态文字：** {c['status']} 这句话说明码本冻结时所处阶段，不代表当前执行进度；四份生成来源均为冻结快照。")
    add("## 1. 这份手册测量什么\n\n本手册帮助编码者回答两个问题：正文在谈什么内容？正文做出了什么可观察的表达行为？它不测量作者真实人格、真实心理情绪的正负程度、身体或医学事实、行动完成质量，也不据主帖推定实际支持交换或互动效果。\n\n旧四词典的词命中、词频比例，以及旧NMF主题权重，不能直接当作人格、动机、披露、社会支持或情绪构念。看见我不等于自我披露，看见加油不等于向别人提供支持，看见谢谢不等于已经获助，出现情绪词也不能直接升级为心理状态测量。新类别须由本帖可观察语义和逐字证据支持。\n\n两个轴分别判断、均可多标签，也可交叉共现。一帖谈运动和饮食，可以有两个内容叶；同帖呈报行动、表达酸痛并说明明日安排，可以有三类表达行为。没有证据的类不因邻类成立而自动成立。")
    add("## 2. 编码单位、可用信息与禁止补充的信息\n\n**编码单位是单条完整的清理后正文。** 先通读全文，再选标签；不可只依据触发词，也不可把一句话从上下文中截出后单独判断。\n\n只使用研究方交付的清理正文。不得用原始标签、图片想象、用户名或作者身份、其他帖子、点赞/浏览/评论数、旧词典预测、旧NMF权重来补语义。正文出现可识别的点名或关系称谓时，可用其文本语义，但不能另外查询身份。\n\n正文中的数字、项目、时间和主体都只按其所言处理。例如写跑了五公里可编码为运动与行动呈报，不能验证其是否真实完成；写很难过可记录体验表达，不能诊断心理问题；描述别人的运动也可属于运动内容。")
    add("## 3. 结构速查：17个内容叶、5个展示父组与其他槽\n\n内容叶保留具体对象，父组服务于本研究的汇总展示。可先用叶定义帮助理解对象，再按映射取父组并集；同一父组有多个叶，只给该帖的父组记一次。父组频数不是叶频数相加。\n\n**现有人审CSV只填写6个内容父组槽与15个表达行为槽，没有content_leaves列。** 17叶是理解边界和父组映射的辅助，不要求填写者在现有表中另找逐叶字段；如研究者另建逐叶扩展表，应标明其为扩展记录，不能冒充本轮已验证项目。\n\n5个观察父组是人为设定的研究任务展示聚合，并非唯一自然分类，也不声称内部同质。`d_other`是另外保留的开放槽，不是第六个已经发现的同质构念。`d_life`要求实质内容对象，不能充当非运动残余；运动与其中的家庭、出行或天气等可同时出现。")
    mapping_rows = []
    for parent in c["domains"]:
        mapped = [f"`{leaf['code']}` {leaf['label']}" for leaf in c["content_subdomains"] if c["subdomain_to_parent"][leaf["code"]] == parent["code"]]
        mapping_rows.append((f"`{parent['code']}` {parent['label']}", "；".join(mapped) if mapped else "无预设内容叶；须在note写明具体遗漏对象"))
    add(table(["展示父组或开放槽", "17个内容叶的固定映射"], mapping_rows))
    add("**检验范围要分层书写。** 本轮留出编码对照只评估6个内容父组槽与15个表达行为槽，不逐一验证17个内容叶。17叶是可追溯的发现记录；它们的边界、父组内部同质性以及这一分组方式，均不能宣称已经获得实证效度验证。")
    add("## 4. 先区分观察状态，再区分内容领域状态\n\n无正文、信息不足、领域未指明、不确定和其他明确内容不是同一种情况。一个轴可判断，不代表另一个轴也可判断。")
    add(table(["层次与状态", "如何判定", "如何记录"], [
        ("观察：`empty` 无正文", "清理正文为空或仅空白", "无可观察文字；内容领域记unavailable；标签缺失不能记为实质阴性"),
        ("观察：`insufficient` 信息不足", "有符号、数字或不可释义片段，但不足以解释语义", "例如单独的省略号或缺上下文数字；内容领域记unavailable，不硬塞题注或其他"),
        ("观察：`readable` 可读", "能解释至少一项表达或内容", "继续分轴；例如早安可读但未必有内容领域"),
        ("内容：`specified` 已指明", "有可复述且能指出证据的对象", "现有CSV记录全部有证据的父组；内容叶帮助匹配；明确未覆盖对象可用d_other并写note"),
        ("内容：`unspecified` 领域未指明", "正文可表达体验、寒暄或动员，但不足以识别内容对象", "例如只有加油；可有行为标签，不能归d_life，也不能把五父组记为已知都不存在"),
        ("内容：`uncertain` 不确定", "文本存在可疑对象，但指代、词义或边界无法确定", "记下待选类别、歧义片段及不能裁定的原因；不得用其他掩盖犹豫"),
        ("内容：`unavailable` 无可用判断", "观察状态为空或不足，无法进入领域判断", "与可读但未指明分开；也与已指明后某标签未检出分开"),
        ("内容：`d_other` 其他明确内容", "存在可清楚复述的具体对象，现有叶和父组不能覆盖", "仍为specified；note必须写具体对象和现有分类不适用之处"),
    ]))
    add("**未检出、未知和缺失分开。** 在足够可读且已完成判断的范围里，某类未检出才可按编码任务要求记录为0；空白、信息不足、未指明或尚未解决的判断不得批量填成0。若表格只能接受0/1，须另保留状态与缺失标记，交由研究者确定分析分母，编码者不能自行把未知替换为0。\n\n当前冻结码本正式列出了观察状态和内容领域状态，没有新增一套行为状态值。行为轴遇到缺失、信息不足或歧义时，应在对应判断和note中保留，不为了填满表格而强加行为，也不另造正式标签。")
    add("## 5. 内容父组边界与样本支持\n\n下列开发计数的分母是160条开发帖，校准计数的分母是80条校准帖。它们是发现与修订阶段的样本支持，不是全体9532帖、全部可读正文或Keep平台的比例。每帖可多标签，列间总和允许超过样本数；不同父组也可重叠。作者数仅为开发样本内出现该父组的作者数。")
    add(table(["父组/槽", "开发帖数", "开发作者数", "校准帖数", "支持状态"], [(f"`{x['code']}` {x['label']}", x["development_posts"], x["development_authors"], x["calibration_posts"], STATUS_ZH.get(x["status"], x["status"])) for x in c["domains"]]))
    for x in c["domains"]:
        include_text = stringify(x["include"])
        if x["code"] == "d_life":
            include_text = include_text.replace("保留11个开发细分", "按固定映射保留10个开发叶与2个校准新增叶")
        add(f"### {x['code']}｜{x['label']}\n\n**定义：** {x['definition']}\n\n**纳入：** {include_text}\n\n**排除：** {stringify(x['exclude'])}\n\n**归并理由：** {x['merge_reason']}")
        if x["code"] == "d_life":
            add("**计数措辞说明：** 冻结JSON的纳入字段原写11个开发细分，与其显式叶列表和映射不一致。本手册依17叶列表及固定映射展示：d_life下共12叶，其中10叶来自开发，commerce和home_housing两叶由校准新增；冻结JSON保持原样。本说明仅澄清条目数，不更改分类定义。")
    add("## 6. 17个内容叶：逐类操作说明\n\n本节按冻结码本逐类列定义、纳入、排除与近邻。例句全部是为教学自行编造的短句，**不是原帖、不是开发或校准证据**，也不改变样本计数。所给四份来源没有逐叶的帖子与作者计数，本手册不推算或虚造叶级频数。以下合成例只展示局部判定，实际编码仍须通读全文并检索其他可并列标签。")
    for i, x in enumerate(c["content_subdomains"], 1):
        parent = parent_by_code[c["subdomain_to_parent"][x["code"]]]
        example, explanation = LEAF_EXAMPLES[x["code"]]
        neighbors = x.get("nearest_confusion", LEAF_NEIGHBORS.get(x["code"], []))
        add(f"### 6.{i} `{x['code']}`｜{x['label']}\n\n**展示父组：** `{parent['code']}` {parent['label']}。**发现状态：** {STATUS_ZH.get(x['status'], x['status'])}。\n\n**定义：** {x['definition']}\n\n**纳入：** {stringify(x['include'])}\n\n**排除：** {stringify(x['exclude'])}\n\n**近邻辨别：** {stringify(neighbors)}\n\n**合成教学例（非原帖）：** “{example}” {explanation}")
    add("## 7. 15类表达行为：逐类操作说明\n\n表达行为回答这段文字在做什么，不能由内容域直接推定。行为共现须分别有证据；同一片段只有确实兼具两种行为时才能同时支持两类。开发0不代表该行为在总体中不存在；校准新增的稀有行为继续保留人工候选，不保证能自动识别或用于回归。")
    add(table(["行为", "开发帖数/160", "开发作者数", "校准帖数/80", "支持状态"], [(f"`{x['code']}` {x['label']}", x["development_posts"], x["development_authors"], x["calibration_posts"], STATUS_ZH.get(x["status"], x["status"])) for x in c["functions"]]))
    for i, x in enumerate(c["functions"], 1):
        example, explanation = FUNCTION_EXAMPLES[x["code"]]
        add(f"### 7.{i} `{x['code']}`｜{x['label']}\n\n**定义：** {x['definition']}\n\n**纳入：** {stringify(x['include'])}\n\n**排除：** {stringify(x['exclude'])}\n\n**近邻辨别：** {x['nearest_confusion']}\n\n**样本支持：** 开发{x['development_posts']}帖、{x['development_authors']}作者；校准{x['calibration_posts']}帖。{STATUS_ZH.get(x['status'], x['status'])}。\n\n**类别依据：** {x['basis']}\n\n**合成教学例（非原帖）：** “{example}” {explanation}")
    add("### 7.16 常见行为边界的快速比较")
    add(table(["容易混淆的类", "实际判据"], [
        ("行动呈报／未来安排", "现在或已发生的行动框架 vs 尚未发生的计划、目标、愿望；不替计划补出执行"),
        ("行动呈报／方法建议", "给自己的过程简表 vs 提供可供读者执行的办法；组数、次数本身不决定类别"),
        ("体验自述／对象评价", "我很舒服是自身体验；这双鞋很舒服是对象评价；两者明说可并存"),
        ("一般解释／方法建议／交易告知", "说明跨事件关系 vs 告诉读者如何做 vs 具体供给和交易条款；具体价格不自动成为解释"),
        ("概括议论／行动号召", "一般价值与意义命题 vs 启动或坚持的动员；格言不自动再标号召"),
        ("联络邀请／回应征询", "索取联系或共同参与 vs 索取答案或回应；一个邀请句有问号也不自动双标"),
        ("题注／行动呈报／信息不足", "能解释为主题、指称或景象 vs 具有个人行动、事件或进度框架 vs 根本无法解释"),
        ("感谢／评价／社会支持", "感谢话语、褒贬评价分开编码；两者都不能直接证明已发生支持交换"),
        ("其他行为／不确定", "能清楚说出未覆盖的具体话语行为才用其他；只是拿不准已有类则保留歧义"),
    ]))
    add("## 8. 逐字证据与特殊语境\n\n每个阳性父组和行为判断都要有可逐字定位的正文证据；若另建逐叶扩展记录，叶标签也须保存证据。选择足以支持判断的最短连续片段，保留否定、主体、时间和语气条件；过短的触发词或省去否定的引文不能作证。多个分散片段可分别保存，不拼成原文中不存在的句子。父组可使用其下叶的对象证据；多个标签共享片段时，要能分别解释各自满足的条件。\n\n**不得把证据意译为原文。** 证据栏逐字保存，解释另写note。正文若写没有去跑步，证据必须包含没有；可据明确运动对象标运动内容，却不能记录实际去跑步。记录很难过，只能支持难过这一表达，不证明临床状态或长期特征。\n\n**否定、梦境、假设和引用中的明确对象仍可属于内容轴。** 但内容出现不等于事实发生。梦里腿酸不能当实际身体体验；假设发生的运动不能当已完成行动；幻想或谐音愿望不能自动当未来承诺。先确定话语框架，再判断行为。若假设用于给读者具体办法，可标方法建议；若只是明确幻想叙事，可在现有类不能覆盖时标其他行为并说明。\n\n**引用与格言可按其表达内容编码。** 保留引用来源或话语归属提示，不认定作者赞同、相信或实践引文，也不据此推断作者人格。引用的书籍或歌曲只作来源时，不机械增加文化内容叶；只有其本身被实质讨论时再标。\n\n**主体与受众不能自行补全。** 句中别人发生的运动仍是运动话题；宝宝可能是亲属，也可能是昵称。单独@、大家、你、一起、支持等词，不足以证明共同参与邀请、求助或实际支持。反问、设问、自问和转述问句也不能凭问号记作回应征询。\n\n**准确性与真实性另属任务。** 机制解释标签说明文本提出了关系主张，不等于知识已经证实；商品条款不证明交易成交；感谢不证明真实获助；体重描述不证明测量准确。")
    add("## 9. 实际编码流程\n\n1. 打开单条清理正文，确认编号；不查看互动结果、旧预测或额外身份信息。\n2. 通读全文，判观察状态：空白为empty，不可解释片段为insufficient，有可解释语义为readable。\n3. 先辨话语框架：当下或已发生、未来、否定、假设、梦境、引用、设问或外向征询；确认文本说的主体和对象。\n4. 在内容轴识别可复述的实质对象，可用17叶定义帮助匹配。只有遗漏对象明确时用d_other并写note；没有足够对象为unspecified，存在无法裁定的歧义为uncertain。\n5. 按固定映射取父组并集，填入现有CSV的6个内容槽；不要求另填不存在的逐叶列。检查d_life是否有具体对象证据，避免将所有非运动文本装入其中。\n6. 单独判断并填写15类表达行为。不要从运动推行动完成、从难处推求助、从问号推征询、从鼓励词推社会支持。\n7. 为每个阳性标签抄录逐字证据，保留否定、时间、假设与引用框架；在note解释稀有类、其他槽和歧义。\n8. 核查多标签：每类是否有独立语义理由？是否漏掉可并列内容或行为？是否把一个轴的可判定性误带到另一个轴？\n9. 保存初始判断后再复核。存在分歧时先保留双方原判及证据，再依据冻结规则讨论；裁决记录不得抹掉原始分歧。\n10. 留出检验开始后不静默改类名、规则、阈值或训练方式。新问题记入下一版本候选，不用同一留出样本一边改规则一边报告最终表现。\n\n课堂练习可先用本手册合成例理解边界，再由教师另行准备不参与当前冻结检验的练习材料。若正式开展人工验证，应由至少两名未参与该批发现的编码者独立盲标，保留证据与分歧，再安排裁决；这是一项后续建议，并非已完成的工作。")
    add("## 10. 合成边界练习：全部非原帖\n\n以下短句均由手册作者为教学编造，不对应任何开发、校准或留出编号。表中是为突出边界的局部示范，不替代全文判断，也不加入样本支持计数。")
    add(table(["合成句", "建议判断", "关键边界"], [
        ("早安！", "readable；domain_state=unspecified；f_greeting_wish", "问候可判，内容对象未指明；不归d_life"),
        ("……", "insufficient；domain_state=unavailable", "不能硬归题注或其他；不是所有类的实质阴性"),
        ("加油，坚持住！", "readable；内容未指明；f_exhortation", "无法仅凭动员补出运动、他人受众或支持效果"),
        ("今天没去跑步。", "exercise→d_exercise；f_activity_update；证据保留没", "是关于未行动的日常情况呈报，不是跑步已经发生"),
        ("如果膝盖痛，先暂停跑步。", "body+exercise→d_body+d_exercise；f_practical_guidance", "假设对象明确，可编码内容；不认定作者膝痛或实际跑步"),
        ("梦里我的腿酸得抬不起来。", "body→d_body；f_other_expression，note写梦境叙事", "不以梦中反应标实际体验或行动；保留梦里证据"),
        ("书中格言说：人的价值不由一时输赢决定。", "life→d_life；f_reflection；note写引用", "不认定作者人格或信念；书作为出处不足以自动标culture"),
        ("我完成了三组深蹲。", "exercise→d_exercise；f_activity_update", "个人简表没有邀请仿用，不自动标方法建议"),
        ("深蹲时先收紧腹部，再缓慢下蹲。", "exercise→d_exercise；f_practical_guidance", "步骤可供读者执行，不是个人完成日志"),
        ("你们通常怎么设置提醒？请留言告诉我。", "platform→d_tools；f_reader_response_request", "明确索取回应；不等于已获帮助"),
        ("为什么要休息？因为恢复也需要时间。", "body→d_body；f_explanation", "设问并自行回答，不自动标回应征询；知识正确性另审"),
        ("谢谢阿宁提醒我带水。", "f_gratitude；内容对象不足时可保留未指明", "感谢本身不是关系内容叶，也不证明测得支持效果"),
        ("明天和我一起去慢跑吧。", "exercise+social→d_exercise+d_life；f_relational_bid", "明确共同参与；不凭邀请句自动增加已完成行动或回应征询"),
        ("这款台灯八十元，七日内可退。", "commerce→d_life；f_sale_offer", "具体报价不是一般机制解释；不推断作者身份或成交"),
    ]))
    add("## 11. 校准发现与冻结变更\n\n下表仅列问题、决定和追溯编号，不展示任何原帖。D/C编号是来源记录中的开发/校准索引，不是本手册合成例。校准后产生的v1不能被描述成未经修订的最初草案；新增类的支持须按回查后的实际计数报告。")
    add(table(["校准问题", "冻结决定", "追溯索引（不含正文）"], [(x["issue"], x["decision"], "、".join(x["evidence_ids"])) for x in cal["changes"]]))
    add("开发最初保留15个内容叶，校准补入消费交易与居住装修两叶，合计17叶；表达行为从12类补至15类，新增感谢、商品服务供给与交易告知、其他可辨识表达行为。新增三行为在160条开发正文回查中仍为0，校准分别为2、1、4帖；不得把合成例、校准例或后续样本混写成开发阳性。\n\n这些变更说明草案曾有遗漏，修订记录使其可追溯；它们不证明遗漏已经穷尽，也不证明稀有类别适合自动化或回归。")
    add("## 12. 样本、留出检验和结论边界\n\n按作者分开开发、校准和留出，种子为`" + str(p["seed"]) + "`，角色分配不使用互动结果。来源总计" + str(p["population_posts"]) + "帖，其中清理正文非空" + str(p["nonempty_body_posts"]) + "帖；非空也不自动等于语义足够。")
    add(table(["角色池", "作者数", "帖数", "非空正文帖数", "本轮实际材料"], [
        (x["role"], x["authors"], x["posts"], x["nonempty"], {"development": "开发包160帖／55作者", "calibration": "校准包80帖／14作者", "holdout": "冻结快照记计划160帖、当时未释放；当前状态见验证报告"}[x["role"]]) for x in p["split_counts"]
    ]))
    add("另有12条观察状态控制材料、涉及10名作者，用于检查无可读正文等处理；它们不能混作开发或校准类别阳性。开发发现有意增加作者与文本长度的多样性，校准和留出也有作者及模板隔离条件，因此这些包不代表全体帖子分布。不能将开发61/160之类数字解释成总体运动帖占比。\n\n**原型范围。** 本轮原型只使用160条开发与80条校准材料，6个内容父组槽加15个行为槽合计21槽，其中14槽进入模型支持范围，7槽因阳性不足保留为人工候选。原型训练支持、人工候选保留与效度验证是三件不同的事；不能把存在标签等同于已训练成功，也不能把训练完成等同于留出有效。此原型范围来自项目交付说明，不用于修改四份冻结来源。\n\n**验证状态与进度口径。** 开发阶段每轴由一个AI任务编码，不是人工双人编码。本手册按开发和校准后的冻结定义编制，未使用留出正文、留出标注或预测生成手册；四源中未释放的表述只指冻结时快照。同基座AI、不同上下文盲标属于暂时筛查，AI检验当前结果见《分类测量重建_实证依据与验证报告》，人审尚未完成。一致率、κ或F1只说明给定样本、规则和模型条件下的一致性或可重复性，不能替代独立人工效标。共享模型可能共同误判。\n\n**后续应报告什么。** 保留规则版本与输入哈希，报告各标签支持数、每类混淆和分歧、缺失及不确定的处理；稀疏类单独说明。另行完成独立人工盲标、裁决与外部效度工作后，才据实际证据讨论人类可解释性与构念效度。在此之前，不宣称当前分类已经证明真实心理、人格或社会支持，也不提出AI验证过的真实主题互动效果结论。\n\n点赞或回归显著性不能用于反选类别数、名称、词项、阈值或规则；父组用于展示与筛查，不预设组内叶对点赞的关系相同。")
    add("## 13. 文献方法依据与不可迁移内容\n\n本节依据项目指定文献记录整理。双轴是本项目为区分内容与行为所作的工作设计，不声称是任何一篇论文中已经验证的标准分类。下面五项原研究或方法原文提供的是方法与概念边界，不共同构成当前Keep标签的外部验证。")
    for i, s in enumerate(lit["sources"], 1):
        authors = "、".join(s["authors"][:3]) + ("等" if len(s["authors"]) > 3 else "")
        add(f"### 13.{i} {s['id']}\n\n{s['year']}，{authors}。[{s['title']}]({s['url']})。{s['journal']}，{s['volume_pages']}。DOI：`{s['doi']}`。\n\n**原情境与单位：** {s['population']} {s['unit']}\n\n**记录核对的方法：** {s['verified_method']}\n\n**本研究可借鉴：** {s['transferable']}\n\n**不可直接迁移：** {s['not_transferable']}\n\n**定位与版本：** {s['locator']} {s.get('full_text_version', '项目记录已核对原文。')}")
    add("### 13.6 这些依据在本手册中的具体用途\n\n归纳阅读、试编码、修订和双人验证的流程借鉴Kalinowski等；把自述、征询、支持提供分开并保存语义证据借鉴Wang等；Stragier等提醒，支持行为应结合发送者、接收者与回复语境，单条主帖的称呼、感谢或高互动量不能证明互助；Ying等区分主题连贯性、概念标签适配与测量验证；Tausczik与Pennebaker说明词表需要独立评审和外部验证，词计数存在语境局限。\n\n这些研究的类别名称、比例、平台分布、心理关联和回归效果都不迁移为本项目结论。原研究也没有直接评估本轮AI多任务编码；对同基座AI局限的判断是结合测量原则作出的项目推论。")
    add("## 附录A. 人工编码表填写提示与可选扩展\n\n现有人审CSV的标签部分只有6个内容父组槽和15个表达行为槽，没有逐叶列。下表用概念性字段名说明填写要求；实际按交付CSV的现有列名填写，不要求填写者另造字段。保留证据时需遵守数据管理要求；公开报告可只用合成示例和汇总统计。")
    add(table(["建议字段", "填写要求"], [
        ("post_id", "沿用盲包编号；不补查身份"),
        ("observation_state", "readable／insufficient／empty三选一"),
        ("domain_state", "specified／unspecified／uncertain／unavailable；按本手册区分"),
        ("domain_parents", "按固定映射取并集；遗漏对象明确时可加d_other"),
        ("functions", "从15行为选择有证据的全部行为；不由内容轴代填"),
        ("evidence", "逐标签保存逐字片段；注明父组或行为代码"),
        ("note", "歧义、话语归属、梦境/假设/否定、其他的具体缺口、未决理由"),
        ("coder / round / codebook_version", "匿名编码者、轮次、冻结版本；独立初判与复核裁决分开保留"),
    ]))
    add("**可选逐叶扩展表：** 只有研究者另行建立并明确说明扩展目的时，才增设content_leaves列并记录17叶及逐叶证据。扩展表不属于现有人审CSV，不扩大本轮留出验证范围。")
    add("**保存前自查：** 我能为每个阳性标签指出逐字证据吗？我是否保留了否定、假设、梦境与引用框架？我是否从品牌、数字、打卡、加油、问号或称呼补出了原文没有的意义？我是否把无正文或不确定填成了0？d_life、题注和其他是否被当成了剩余槽？我是否把表达误写成了真实身体、心理、人格或支持事实？")
    add("## 附录B. 冻结来源与可重复生成\n\n生成器仅读取以下四个项目文件，不读帖子正文包、标注或预测。源文件SHA-256用于确认手册对应的输入版本；生成器会先核对码本与校准记录的哈希及计数一致性。")
    add(table(["来源文件", "SHA-256"], [(f"`{SOURCE_PATHS[key]}`", f"`{hashes[key]}`") for key in SOURCE_PATHS]))
    add("生成命令（从`projects/group`目录运行）：\n\n```bash\npython3 code/build_classification_codebook_manual.py\npython3 code/build_classification_codebook_manual.py --check\npython3 code/build_classification_codebook_manual.py --html-output /tmp/classification_codebook_v1.html\n```\n\n默认输出为`分类编码手册_v1.md`。可选HTML为自包含中文打印版，含A4打印样式，可用浏览器打印为PDF；PDF导出应检查分页、表格、中文字体和长代码，不改变任何分类规则。合成教学例固定保存在生成器中，不会从任何帖子自动抽例。")
    return "\n\n".join(parts).rstrip() + "\n"


def inline_html(text):
    # Protect code before applying other inline markup.
    tokens = []
    def protect(match):
        tokens.append("<code>" + html.escape(match.group(1)) + "</code>")
        return f"@@CODE{len(tokens)-1}@@"
    text = re.sub(r"`([^`]+)`", protect, text)
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    for i, token in enumerate(tokens):
        text = text.replace(f"@@CODE{i}@@", token)
    return text


def markdown_to_html(markdown):
    """Render only the small, explicit Markdown subset emitted above."""
    lines = markdown.splitlines()
    body, i = [], 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            body.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            i += 1
            continue
        heading = re.match(r"^(#{1,3}) (.+)$", line)
        if heading:
            level = len(heading.group(1))
            body.append(f"<h{level}>" + inline_html(heading.group(2)) + f"</h{level}>")
            i += 1
            continue
        if line.startswith("| "):
            rows = []
            while i < len(lines) and lines[i].startswith("| "):
                # Emitted cells do not contain literal pipes.
                rows.append([x.strip() for x in lines[i].strip().strip("|").split("|")])
                i += 1
            header, data_rows = rows[0], rows[2:]
            body.append('<div class="table-wrap"><table><thead><tr>' + "".join("<th>" + inline_html(x) + "</th>" for x in header) + "</tr></thead><tbody>" + "".join("<tr>" + "".join("<td>" + inline_html(x) + "</td>" for x in row) + "</tr>" for row in data_rows) + "</tbody></table></div>")
            continue
        if re.match(r"^\d+\. ", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\. ", lines[i]):
                items.append(re.sub(r"^\d+\. ", "", lines[i]))
                i += 1
            body.append("<ol>" + "".join("<li>" + inline_html(x) + "</li>" for x in items) + "</ol>")
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3} |\| |```|\d+\. )", lines[i]):
            paragraph.append(lines[i])
            i += 1
        body.append("<p>" + inline_html(" ".join(paragraph)) + "</p>")
    style = """
:root { color-scheme: light; }
body { max-width: 980px; margin: 40px auto; padding: 0 24px; color: #172033; background: white; font: 16px/1.75 -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Noto Sans CJK SC', 'Microsoft YaHei', sans-serif; }
h1 { font-size: 30px; line-height: 1.3; margin-top: 0; }
h2 { font-size: 23px; margin-top: 2.1em; padding-bottom: .3em; border-bottom: 1px solid #cad2df; }
h3 { font-size: 18px; margin-top: 1.8em; }
p { margin: .8em 0; } strong { color: #101a2d; }
code { font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace; font-size: .83em; overflow-wrap: anywhere; }
pre { padding: 12px; background: #f3f5f8; white-space: pre-wrap; }
a { color: #23568a; text-decoration: none; overflow-wrap: anywhere; }
.table-wrap { overflow-x: auto; } table { border-collapse: collapse; width: 100%; font-size: 13px; line-height: 1.6; margin: 14px 0; }
th, td { border: 1px solid #b8c2d2; padding: 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: #eaf0f7; font-weight: 650; }
li { padding-left: .2em; margin: .4em 0; }
@page { size: A4; margin: 18mm 16mm; }
@media print {
 body { max-width: none; margin: 0; padding: 0; font-size: 10pt; line-height: 1.65; }
 h1 { font-size: 22pt; } h2 { font-size: 15pt; } h3 { font-size: 12pt; }
 h1, h2, h3 { break-after: avoid; } p { orphans: 3; widows: 3; }
 .table-wrap { overflow: visible; } table { font-size: 8pt; table-layout: fixed; }
 thead { display: table-header-group; } tr { break-inside: avoid; }
 pre { break-inside: avoid; } a { color: inherit; }
}
"""
    return '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Keep主帖分类编码手册 v1</title><style>' + style + '</style></head><body>\n' + "\n".join(body) + "\n</body></html>\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "分类编码手册_v1.md", help="Markdown destination")
    parser.add_argument("--html-output", type=Path, help="Optional standalone, print-ready HTML destination")
    parser.add_argument("--check", action="store_true", help="Check that requested outputs match, without modifying them")
    args = parser.parse_args()
    data, hashes = load_sources(ROOT)
    markdown = build_manual(data, hashes)
    outputs = [(args.output, markdown)]
    if args.html_output:
        outputs.append((args.html_output, markdown_to_html(markdown)))
    for path, content in outputs:
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"not up to date: {path}")
            print(f"checked: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            print(f"wrote: {path}")


if __name__ == "__main__":
    main()
