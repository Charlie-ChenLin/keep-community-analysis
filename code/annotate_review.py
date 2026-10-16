"""Record assistant semantic spot-checks; no human annotation is claimed.

Sample selection is stratified by rule hit and is not a representative test set.
Labels assess a broader semantic interpretation, not whether the literal rule ran.
"""
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
labels=[1,0,0,1,1,0,0,0,0,1, 1,1,1,0,1,0,0,0,0,0,
        1,1,1,1,1,0,0,0,1,0, 0,1,0,1,0,0,0,0,0,0]
notes={
0:"努力跑的自我调节叙述。",1:"完成的对象是身体部门配合，不是自律或目标行为。",
2:"完成率指绘画进度，非健身目标。",3:"坚持与结果的自我激励。",4:"夜跑打卡。",
9:"停止囤货和限制零食体现饮食自控，但词典漏掉此表达。",
10:"感谢、你们和共同参与。",11:"向大家提供减脂建议。",12:"我们要在一起飞，含共同参与指向但语境有限。",
13:"一起描述线下朋友活动，不能据此推断向线上受众寻求互动。",14:"大家早上好为受众称呼。",
20:"快乐的正面生活感悟。",21:"哈哈表示愉悦，同时请举手为词典未覆盖的互动邀请。",
22:"美好的正面体验。",23:"快乐的正面感悟。",24:"小幸福表达正面体验。",
26:"加油是激励，不自动等于愉悦情绪；与自律维度重叠的可能性需区分。",
27:"劝慰文本，未明确表达愉悦或赞许。",28:"OK啦表达完成后的满意，积极词典未覆盖。",
30:"反问式抱怨，问号不能等同真实求助。",31:"面向受众的询问，仍不等于求助。",
32:"反问式自我表达。",33:"含面向读者的询问，同时夹杂课程推广式表达，不认可其中健康建议。",
34:"反问或感叹，非信息请求。"
}
def main():
    p=ROOT/"results/text_coding_review.csv";d=pd.read_csv(p)
    assert len(d)==40
    d["reviewed_semantic"]=labels
    d["review_note"]=[notes.get(i,"未见该维度明确语义。") for i in range(len(d))]
    d["reviewer"]="Codex辅助语义抽查；非人工双人编码"
    d.to_csv(p,index=False,encoding="utf-8-sig")
if __name__=="__main__":main()
