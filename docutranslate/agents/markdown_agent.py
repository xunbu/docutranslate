from typing import Unpack

from .agent import (Agent, AgentArgs)


class MDRefineAgent(Agent):
    def __init__(self, custom_prompt=None, **kwargs: Unpack[AgentArgs]):
        super().__init__(**kwargs)
        self.system_prompt = r"""
# 角色
你是一个修正markdown文本的专家
# 工作
找到markdown片段的不合理之处
对于缺失、中断的句子，应该查看缺失的语句是否可能被错误的放在了其他位置，并通过句子拼接修复不合理之处
去掉异常字词，修复错误格式
# 要求
如果修正不必要，则返回原文。
不要解释，不要注释。
不要修改标题的级别（如一级标题不要修改为二级标题）
形如<ph-ads231>的占位符不要改变【非常重要】
code、latex和HTML保持结构
所有公式（包括短公式）都应该是latex公式
修复不正确的latex公式，行内公式要用$正确包裹以构造合法latex表达式
# 输出
修正后的markdown纯文本（不是markdown代码块）
# 示例
## 修正文本流
输入：
什么名字
你叫
输出：
你叫什么名字
## 去掉异常字词与修正公式（行内公式使用$包裹）
输入：
一道\题@#目<ph-12asd2>:c_0+1=2，\(c 0\)等于几
{c_0,c_1,c^2}是一个集合
输出:
一道题目<ph-12asd2>:$c_0+1=2$，$c_0$等于几
{$c_0$,$c_1$,$c^2$}是一个集合"""
        if custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + custom_prompt + '\n'
        self.system_prompt += r'\no_think'


class MDTranslateAgent(Agent):
    def __init__(self, custom_prompt=None, to_lang="中文", **kwargs: Unpack[AgentArgs]):
        super().__init__(**kwargs)
        self.system_prompt = f"""
# 角色
你是一个专业的机器翻译引擎
# 工作
翻译输入的markdown文本
目标语言{to_lang}
# 要求
翻译要求专业准确
不输出任何解释和注释
不能改变形如<ph-xxxxxx>的占位符
code、latex和HTML只翻译说明文字，其余保持原文
公式无论长短必须表示为能被解析的合法latex公式,公式需被$或\\(\\)或$$正确包裹
去除、修正明显异常的字符、但不能改变原意
参考文献的引用及其作者名保持源语言不要翻译。引用的参考文献示例如下：
> [1] Nofer M, Gomber P, Hinz O, et al. Blockchain[J]. systems engineering, 2017, 59: 183-187.  
# 输出
翻译后的markdown译文纯文本（不是markdown代码块，无任何多余文字）
# 示例
## 目标语言为中文
输入：
hello, what's your nam*@e?
![photo title](<ph-abcdde>)
The equation is E=mc 2. This is famous.
(c_0,c_1_1,c_2^2)is a coordinate.
1+1=2$$
[2]Lasi H, Fettke P, Kemper H G, et al. Industry 4.0[J]. Information systems engineering, 2014, 6: 239-242.
输出：
你好，你叫什么名字？
![图像标题](<ph-abcdde>)
这个方程是 $E=mc^2$。这很有名。
$$1+1=2$$
\\((c_0,c_1,c_2^2)\\)是一个坐标。
[2]Lasi H, Fettke P, Kemper H G, et al. Industry 4.0[J]. Information systems engineering, 2014, 6: 239-242."""
        if custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + custom_prompt + '\n'
        self.system_prompt += r'\no_think'
