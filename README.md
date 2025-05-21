# 简介

## DocuTranslate

[![image](https://img.shields.io/badge/github-DocuTranslate-blue)](https://github.com/xunbu/docutranslate)

文件翻译工具，借助[docling](https://github.com/docling-project/docling)、[minerU](https://mineru.net/)与大语言模型实现多种格式文件的翻译

> QQ交流群：1047781902

# 整合包

对于只使用基本翻译功能的用户，可以在[github releases](https://github.com/xunbu/docutranslate/releases)
上下载最新的整合包，该整合包点击即用，您所需的只是获取某个ai平台的api-key。
以及可以在mineru申请token进行pdf识别【可选】

对于轻量版，只支持minerU转换引擎，因此需要申请minerU的API-Token

# 安装

使用pip  
1. `pip install docutranslate`  
2. `pip install docling`#如果使用docling进行文档解析

使用uv  
1. `uv init`  
2. `uv add docutranslate`  
3. `uv add docling`#如果使用docling进行文档解析

使用git
1. `git clone https://github.com/xunbu/docutranslate.git`
2. `uv sync`
3. `uv pip install -U -e .`
# 支持的文件格式

| 输入格式           | 输出格式         |
|----------------|--------------|
| PDF（非扫描版）      | Markdown（推荐） |
| Markdown       | HTML         |
| HTML、XHTML     | PDF(仅交互界面支持) |
| CSV            |              |
| DOC、DOCX（部分支持） |              |

> 如果想不使用交互界面获取pdf，可以先下载HTML文件，用浏览器打开并打印

# 前置条件

本翻译工具的翻译流程总体如下：

1. 使用文本转换引擎将文档转换成markdown（有docling（本地）、minerU（联网）两种引擎）
2. 使用大语言模型翻译markdown文本（需要申请api-key或本地部署）

## 使用docling引擎注意事项

使用docling将文档转换为markdown时，需要下载模型到本地（也可以提前下载，见FAQ），因此可能会遇到一些网络问题

### huggingface换源

> 不能科学上网的友友注意了

无法访问的huggingface的电脑在以下操作时请换源[点击测试](https://huggingface.co)

- 第一次读取非markdown文本
- 第一次使用公式识别或代码识别功能

#### 方法1

设置电脑的环境变量(记得设置后重启IDE)  
`HF_ENDPOINT=https://hf-mirror.com`

#### 方法2

在代码开头设置环境变量

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

###其余代码写在下方
```

## 使用minerU引擎注意事项

使用minerU将文档转换为markdown时，需要在minerU平台申请token

1. 打开[minerU官网](https://mineru.net/apiManage/docs)申请token
2. 申请成功后，在[API Token管理界面](https://mineru.net/apiManage/token)创建API Token

## 获取大模型平台的baseurl、key、model-id

由于需要使用大语言模型进行markdown调整与翻译，所以需要预先获取模型的baseurl、key、model-id  
常见的大模型平台baseurl与api获取方式可见[常用ai平台](#常用ai平台)
> 比较推荐的模型有智谱的glm-4-air、glm-4-flash（免费），阿里云的qwen-plus等。  
> 推理模型需要支持api请求响应中区分`reasoning_content`和`content`（详见平台开发手册，ollama、lmstudio需开启对应选项）

# 使用方式

## 注意事项（使用docling转换引擎必看，使用minerU或使用整合包时可跳过）

使用docling转换引擎时以下操作会自动从[huggingface](https://huggingface.co)下载模型，windows需要使用**管理员模式**
打开IDE运行脚本，并按需换源[换源指南](#huggingface换源)

- 第一次使用该库读取、翻译非markdown文本
- 第一次使用该库的公式识别或代码识别功能

## 使用图形化界面

```commandline
docutranslate -i
```

## 翻译文件

```python
from docutranslate.translater import FileTranslater

translater = FileTranslater(base_url="<baseurl>",
                            key="<key>",
                            model_id="<model-id>",
                            convert_engin="mineru",# 使用mineru解析文档
                            mineru_token="<申请的mineru_token>"#使用mineru时必填
                            # convert_engin="docling"  # 使用docling解析文档
                            )

# 不开启公式、代码识别（默认输出为markdown文件）
translater.translate_file("<文件路径>", to_lang="中文")

# 开启公式、代码识别（需要下载更多模型）
translater.translate_file("<文件路径>", to_lang="中文", formula=True, code=True)

# 在先修复文本再翻译（适用于翻译pdf，但更耗时耗费）
translater.translate_file("<文件路径>", to_lang="中文", refine=True)
```

> 下载模型时请用管理员模式打开终端运行文件（windows），并按需换源
> 输出文件默认放在`./output`中

## 使用不同的agent分别进行文本修正和翻译

```python
from docutranslate import FileTranslater
from docutranslate.agents import MDRefineAgent, MDTranslateAgent

translater = FileTranslater()

refine_agent = MDRefineAgent(baseurl="<baseurl-1>", key="<key-1>", model_id="<model-id-1>")
translate_agent = MDTranslateAgent(baseurl="<baseurl-2>", key="<key-2>", model_id="<model-id-2>")

translater.translate_file("<文件路径>", to_lang="中文", refine_agent=refine_agent,
                          translate_agent=translate_agent)
```

## 文件转换(pdf/markdown/HTML/Doc等->markdown/html)

```python
from docutranslate import FileTranslater

translater = FileTranslater(base_url="<baseurl>",
                            key="<key>",
                            model_id="<model-id>")
# 文件转html
translater.read_file("<文件路径>").save_as_html()
# 文件转markdown
translater.read_file("<文件路径>").save_as_markdown()
```

## 参数说明

### 创建FileTranslater

```python
from docutranslate import FileTranslater

translater = FileTranslater(base_url="<baseurl>",  # 默认的模型baseurl
                            key="<api-key>",  # 默认的大语言模型平台api-key
                            model_id="<model-id>",  # 默认的模型id
                            chunksize=2000,  # markdown分块长度（单位byte），分块越大效果越好（也越慢），不建议超过8000
                            max_concurrent=20,  # 并发数，受到ai平台并发量限制，如果文章很长建议适当加大到20以上
                            timeout=2000,  # 调用api的超时时间
                            docling_artifact=None,  # 使用提前下载好的docling模型
                            convert_engin="mineru",  # 可选minerU或docling
                            mineru_token="<mineru-token>",  # minerU的token，使用minerU时必填
                            tips=True  # 开场提示
                            )

```
> 使用docling需要先`pip install docling`或`uv add docling`
### 翻译文件

```python
translater.translate_file(r"<要翻译的文件路径>",
                          to_lang="中文",
                          formula=True,  # 是否启用公式识别
                          code=True,  # 是否启用代码识别
                          refine=False,  # 是否在翻译前先修正一遍markdown文本（较耗时）
                          output_format="markdown",  # "markdown"与"html"两种输出格式
                          output_dir="./output",  # 默认输出文件夹
                          refine_agent=None,  # 修正Agent
                          translate_agent=None  # 翻译Agent
                          )
```

# 常用ai平台

| 平台名称       | 获取APIkey                                                                              | baseurl                                           |
|------------|---------------------------------------------------------------------------------------|---------------------------------------------------|
| ollama     |                                                                                       | http://127.0.0.1:11434/v1                         |
| lm studio  |                                                                                       | http://127.0.0.1:1234/v1                          |
| openrouter | [点击获取](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                      |
| openai     | [点击获取](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                        |
| deepseek   | [点击获取](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                       |
| 智谱ai       | [点击获取](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4              |
| 腾讯混元       | [点击获取](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1          |
| 阿里云百炼      | [点击获取](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| 火山引擎       | [点击获取](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3          |
| 硅基流动       | [点击获取](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                     |
| DMXAPI     | [点击获取](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                          |

# FAQ

1. 是否支持扫描件

> 暂不支持

2. 第一次使用很慢是怎么回事

> 第一次是使用时docling需要从huggingface下载转换输入文件为markdown的模型  
> 通过设置环境变量换源或科学上网可能有助于提高下载速度

> huggingface换源，请设置环境变量：`HF_ENDPOINT=https://hf-mirror.com`

3. 如何内网使用（不联网）

> 可以，对于docling提供的解析pdf、html等功能，可以使用以下方式提前下载所需的模型

```python
from docutranslate.utils.docling_utils import get_docling_artifacts

print(get_docling_artifacts())  # 会显示模型下载文件夹，通常在`C:\Users\<user>\.cache\docling\models`
```

> 将模型文件夹命名为docling_artifact放置在项目下
> 或创建FileTranslater时docling_artifact参数设置为文件夹位置

```python
from docutranslate import FileTranslater

translater = FileTranslater(base_url="<baseurl>",
                            key="<key>",
                            model_id="<model-id>",  # 使用的模型id
                            docling_artifact=r"C:\Users\<user>\.cache\docling\models"
                            )
```

> 对于llm功能，可以使用ollama或lm studio等方式本地部署。