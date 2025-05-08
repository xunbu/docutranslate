# 简介 
## DocuTranslate
一个使用大语言模型(llm)翻译pdf和markdown的包
  
[github主页](https://github.com/xunbu/docutranslate)

# 安装
使用pip  
`pip install doctranslate`  

使用uv  
`uv add doctranslate`

# 前置条件（获取大模型平台的baseurl、key、model-id）
由于需要使用大语言模型进行markdown调整与翻译，所以需要预先获取模型的baseurl、key、model-id  
常见的大模型平台baseurl可见[常用baseurl](#常用baseurl)

# 使用方式
## 使用默认参数翻译pdf

```python
from docutranslate.translater import FileTranslater

# 不开启公式、代码识别
FileTranslater(base_url="<baseurl>", key="<key>", model_id="<model-id>").translate_pdf_file("<pdf路径>", to_lang="中文")

# 开启公式、代码识别（需要下载更多模型）
FileTranslater(base_url="<baseurl>", key="<key>", model_id="<model-id>").translate_pdf_file("<pdf路径>", to_lang="中文",
                                                                                            formula=True, code=True)
```
> 第一次使用时需要下载模型（约1G、使用公式、代码识别需要多约0.5G），请稍作等待  
> 输出文件默认放在`./output`中

## 使用不同的agent分别进行文本修正和翻译

```python
from docutranslate.translater import FileTranslater

translater = FileTranslater()

refine_agent = translater.create_refine_agent(baseurl="<baseurl-1>", key="<key-1>", model_id="<model-id-1>")
translate_agent = translater.create_translate_agent(baseurl="<baseurl-2>", key="<key-2>", model_id="<model-id-2>")

translater.translate_pdf_file(pdf_path="<pdf路径>", to_lang="中文", refine_agent=refine_agent,
                              translate_agent=translate_agent)
```

## 参数说明
### 创建FileTranslate

```python
from docutranslate.translater import FileTranslater

translater = FileTranslater(base_url="<baseurl>",
                            key="<key>",
                            model_id="<model-id>",  # 使用的模型id
                            chunksize=4000,  # 【可选】markdown分块长度，分块越大效果越好，不建议超过4096
                            max_concurrent=6  # 【可选】并发数，受到ai平台并发量限制
                            )
```
### 翻译pdf文件
```python
translater.translate_pdf_file(r"<要翻译的pdf路径>",
                              to_lang="中文",
                              formula=False,#是否启用公式识别
                              code=False,#是否启用代码识别
                              refine=True,#是否在翻译前先修正markdown文本
                              output_format="markdown",#"markdown"与"html"两种输出格式
                              output_dir="./output"#默认输出文件夹
                              )
```

### 翻译markdown文件
```python
translater.translate_markdown_file(r"<要翻译的markdown路径>",
                                    to_lang="中文",
                                    refine=False,#【可选】是否在翻译前先修正markdown文本
                                    output_format="markdown",#"markdown"与"html"两种输出格式
                                    output_dir="./output"#默认输出文件夹
                                    )
```



# 常用baseurl
| 平台名称      | baseurl                              |
|-----------|--------------------------------------|
| ollama    | http://127.0.0.1:11434/v1            |
| lm studio | http://127.0.0.1:1234/v1             |
| openai    | https://api.openai.com/v1/           |
| deepseek  | https://api.deepseek.com/v1          |
| 智谱ai      | https://open.bigmodel.cn/api/paas/v4 |