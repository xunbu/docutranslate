# 简介

## DocuTranslate [<svg height="32" aria-hidden="true" viewBox="0 0 24 24" version="1.1" width="20" data-view-component="true" class="octicon octicon-mark-github v-align-middle"><path d="M12 1C5.9225 1 1 5.9225 1 12C1 16.8675 4.14875 20.9787 8.52125 22.4362C9.07125 22.5325 9.2775 22.2025 9.2775 21.9137C9.2775 21.6525 9.26375 20.7862 9.26375 19.865C6.5 20.3737 5.785 19.1912 5.565 18.5725C5.44125 18.2562 4.905 17.28 4.4375 17.0187C4.0525 16.8125 3.5025 16.3037 4.42375 16.29C5.29 16.2762 5.90875 17.0875 6.115 17.4175C7.105 19.0812 8.68625 18.6137 9.31875 18.325C9.415 17.61 9.70375 17.1287 10.02 16.8537C7.5725 16.5787 5.015 15.63 5.015 11.4225C5.015 10.2262 5.44125 9.23625 6.1425 8.46625C6.0325 8.19125 5.6475 7.06375 6.2525 5.55125C6.2525 5.55125 7.17375 5.2625 9.2775 6.67875C10.1575 6.43125 11.0925 6.3075 12.0275 6.3075C12.9625 6.3075 13.8975 6.43125 14.7775 6.67875C16.8813 5.24875 17.8025 5.55125 17.8025 5.55125C18.4075 7.06375 18.0225 8.19125 17.9125 8.46625C18.6138 9.23625 19.04 10.2125 19.04 11.4225C19.04 15.6437 16.4688 16.5787 14.0213 16.8537C14.42 17.1975 14.7638 17.8575 14.7638 18.8887C14.7638 20.36 14.75 21.5425 14.75 21.9137C14.75 22.2025 14.9563 22.5462 15.5063 22.4362C19.8513 20.9787 23 16.8537 23 12C23 5.9225 18.0775 1 12 1Z"></path></svg>](https://github.com/xunbu/docutranslate)

文件翻译工具，借助[docling](https://github.com/docling-project/docling)与大语言模型实现多种格式文件的翻译

# 安装

使用pip  
`pip install docutranslate`

使用uv  
`uv init`  
`uv add docutranslate`

# 支持的文件格式

| 输入格式       | 输出格式         |
|------------|--------------|
| PDF（非扫描版）  | Markdown（推荐） |
| Markdown   | HTML         |
| HTML、XHTML |              |
| CSV        |              |

# 前置条件

## huggingface换源

无法访问的huggingface的电脑在以下操作时请换源[点击测试](https://huggingface.co)

- 第一次读取非markdown文本
- 第一次使用公式识别或代码识别功能

### 方法1

设置电脑的环境变量(记得设置后重启重启IDE)  
`HF_ENDPOINT=https://hf-mirror.com`

### 方法2

在代码开头设置环境变量

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

###其余代码写在下方
```

## 获取大模型平台的baseurl、key、model-id

由于需要使用大语言模型进行markdown调整与翻译，所以需要预先获取模型的baseurl、key、model-id  
常见的大模型平台baseurl与api获取方式可见[常用ai平台](#常用ai平台)
> 比较推荐的模型有阿里云的qwen-plus、智谱的glm-4-air、glm-z1-flash等。免费的智谱glm-4-flash能用但效果欠佳(2025.5)

# 使用方式

## 注意事项

以下操作会自动从[huggingface](https://huggingface.co)下载模型，windows需要使用**管理员模式**打开IDE运行脚本，并按需换源

- 第一次使用该库读取、翻译非markdown文本
- 第一次使用该库的公式识别或代码识别功能

## 翻译文件

```python
from docutranslate.translater import FileTranslater

translater = FileTranslater(base_url="<baseurl>",
                            key="<key>",
                            model_id="<model-id>")
# 不开启公式、代码识别（默认输出为markdown文件）(打开文本修复)
translater.translate_file("<文件路径>", to_lang="中文", refine=True)

# 开启公式、代码识别（需要下载更多模型）
translater.translate_file("<文件路径>", to_lang="中文", formula=True, code=True)

# 翻译markdown文件
translater.translate_file("<markdown路径>", to_lang="中文", refine=False)
```

> 下载模型时请用管理员模式打开终端运行文件（windows），并按需换源
> 输出文件默认放在`./output`中

## 使用不同的agent分别进行文本修正和翻译

```python
from docutranslate import FileTranslater
from docutranslate.Agents import MDRefineAgent, MDTranslateAgent

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

translater = FileTranslater(base_url="<baseurl>",# 默认的模型baseurl
                            key="<key>",#默认的模型api-key
                            model_id="<model-id>",  # 默认的模型id
                            chunksize=4000,  # markdown分块长度，分块越大效果越好，不建议超过4096
                            max_concurrent=6,  # 并发数，受到ai平台并发量限制，如果文章很长建议适当加大到20以上
                            docling_artifact=None, #使用提前下载好的docling模型
                            tips=True#开场提示
                            )

```

### 翻译文件

```python
translater.translate_file(r"<要翻译的文件路径>",
                          to_lang="中文",
                          formula=False,  # 是否启用公式识别
                          code=False,  # 是否启用代码识别
                          refine=True,  # 是否在翻译前先修正markdown文本（较耗时）
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

> 创建FileTranslater时携带模型文件夹即可

```python
from docutranslate import FileTranslater

translater = FileTranslater(base_url="<baseurl>",
                            key="<key>",
                            model_id="<model-id>",  # 使用的模型id
                            docling_artifact=r"C:\Users\<user>\.cache\docling\models"
                            )
```

> 对于llm功能，可以使用ollama或lm studio等方式本地部署。