# FileTranslate
## 一个使用llm翻译pdf和markdown的包

# 安装
## 使用pip
`pip install filetranslate`
## 使用uv
`uv add filetranslate`

# 使用方式
## 翻译pdf文件
```python
import  
translater = FileTranslater(base_url="https://open.bigmodel.cn/api/paas/v4",
                            key="969ba51b61914cc2b710d1393dca1a3c.hSuATex5IoNVZNGu",
                            model_id="glm-4-flashx",
                            chunksize=4000,
                            max_concurrent=40)
translater.read_markdown(
    markdown_path=r"/filetranslate\output\互联网认证授权机制.md")
translater.save_as_html()
```