<p align="center">
<img src="./DocuTranslate.png" alt="プロジェクトロゴ" style="width: 150px">
</p>

<h1 align="center">DocuTranslate</h1>

<p align="center">
  <a href="https://github.com/xunbu/docutranslate/stargazers"><img src="https://img.shields.io/github/stars/xunbu/docutranslate?style=flat-square&logo=github&color=blue" alt="GitHub stars"></a>
  <a href="https://github.com/xunbu/docutranslate/releases"><img src="https://img.shields.io/github/downloads/xunbu/docutranslate/total?logo=github&style=flat-square" alt="GitHub Downloads"></a>
  <a href="https://pypi.org/project/docutranslate/"><img src="https://img.shields.io/pypi/v/docutranslate?style=flat-square" alt="PyPI version"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white&style=flat-square" alt="Python Version"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/xunbu/docutranslate?style=flat-square" alt="License"></a>
</p>

<p align="center">
  <a href="/README_ZH.md"><strong>简体中文</strong></a> / <a href="/README.md"><strong>English</strong></a> / <a href="/README_JP.md"><strong>日本語</strong></a>
</p>

<p align="center">
  大規模言語モデル（LLM）に基づいた軽量なローカルファイル翻訳ツール
</p>

- ✅ **多形式対応**：`pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt`、`ass`など、多様なファイルの翻訳に対応。
- ✅ **用語集自動生成**：用語のアライメント（統一）を実現するための用語集自動生成をサポート。
- ✅ **PDFの表・数式・コード認識**：`docling`、`mineru`といったPDF解析エンジンにより、学術論文によくある表、数式、コードの認識と翻訳を実現。
- ✅ **JSON翻訳**：JSONパス（`jsonpath-ng`構文）による翻訳対象値の指定をサポート。
- ✅ **Word/Excelの書式保持翻訳**：`docx`、`xlsx`ファイル（`doc`、`xls`は未対応）の書式を保持したまま翻訳可能。
- ✅ **マルチAIプラットフォーム対応**：ほぼ全てのAIプラットフォームに対応し、カスタムプロンプトによる高性能な並行AI翻訳を実現。
- ✅ **非同期サポート**：高性能なシナリオ向けに設計され、完全な非同期サポートを提供し、マルチタスク並列処理可能なサービスインターフェースを実装。
- ✅ **LAN・複数人利用対応**：LAN内での複数人同時利用をサポート。
- ✅ **インタラクティブなWeb画面**：すぐに使えるWeb UIとRESTful APIを提供し、統合と使用が容易。
- ✅ **軽量・マルチプラットフォーム対応のポータブルパッケージ**：40MB未満のWindows/Mac用ポータブルパッケージ（`docling`ローカル解析を含まないバージョン）を提供。

> `pdf`を翻訳する際、まずMarkdownに変換されるため、元のレイアウトが**失われます**。レイアウトを重視するユーザーはご注意ください。

> QQ交流グループ：1047781902

**UI画面**：
![UI画面](/images/UI界面.png)

**論文翻訳**：
![論文翻訳](/images/论文翻译.png)

**小説翻訳**：
![小説翻訳](/images/小说翻译.png)

## 統合パッケージ

すぐに使い始めたいユーザー向けに、[GitHub Releases](https://github.com/xunbu/docutranslate/releases) で統合パッケージを提供しています。ダウンロードして解凍し、AIプラットフォームのAPIキーを入力するだけで使用を開始できます。

- **DocuTranslate**: 標準版。オンラインの `minerU` エンジンを使用してPDFドキュメントを解析します。ローカルでのPDF解析が不要な場合はこちらを選択してください（推奨）。
- **DocuTranslate_full**: 完全版。`docling` ローカルPDF解析エンジンを内蔵しています。ローカルでPDFを解析する必要がある場合はこちらを選択してください。
> バージョン1.5.1以降、ローカルにデプロイされたmineruサービスの呼び出しをサポートしています。

## インストール

### pipを使用する場合

```bash
# 基本インストール
pip install docutranslate

# doclingでローカルPDF解析を行う場合
pip install docutranslate[docling]
```

### uvを使用する場合

```bash
# 環境の初期化
uv init

# 基本インストール
uv add docutranslate

# docling拡張のインストール
uv add docutranslate[docling]
```

### gitを使用する場合

```bash
# 環境の初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

### docker を使用する場合

```bash
docker run -d -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:latest
# docker run -it -p 8010:8010 xunbu/docutranslate:v1.5.4
```

## コアコンセプト：ワークフロー (Workflow)

新しい DocuTranslate の核となるのは **ワークフロー (Workflow)** です。各ワークフローは、特定の種類のファイル用に設計された、完全なエンドツーエンドの翻訳パイプラインです。巨大なクラスとやり取りするのではなく、ファイルの種類に基づいて適切なワークフローを選択し、設定します。

**基本的な使用手順は以下の通りです：**

1. **ワークフローの選択**：入力ファイルの種類（例：PDF/Word または TXT）に基づいて、`MarkdownBasedWorkflow` や `TXTWorkflow` などのワークフローを選択します。
2. **設定の構築**：選択したワークフローに対応する設定オブジェクト（例：`MarkdownBasedWorkflowConfig`）を作成します。この設定オブジェクトには、必要なすべてのサブ設定が含まれます：
    * **コンバータ設定 (Converter Config)**: 元のファイル（例：PDF）をMarkdownに変換する方法を定義します。
    * **翻訳機設定 (Translator Config)**: 使用するLLM、APIキー、ターゲット言語などを定義します。
    * **エクスポータ設定 (Exporter Config)**: 出力形式（例：HTML）の特定のオプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳の実行**：ワークフローの `.read_*()` および `.translate()` / `.translate_async()` メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()` または `.save_as_*()` メソッドを呼び出して翻訳結果を取得または保存します。

## 利用可能なワークフロー

| ワークフロー | 適用シナリオ | 入力形式 | 出力形式 | コア設定クラス |
|:---|:---|:---|:---|:---|
| **`MarkdownBasedWorkflow`** | PDF、Word、画像などのリッチテキストドキュメントを処理。フロー：`ファイル -> Markdown -> 翻訳 -> エクスポート`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` 等 | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`** | プレーンテキストドキュメントを処理。フロー：`txt -> 翻訳 -> エクスポート`。 | `.txt` およびその他のテキスト形式 | `.txt`, `.html` | `TXTWorkflowConfig` |
| **`JsonWorkflow`** | JSONファイルを処理。フロー：`json -> 翻訳 -> エクスポート`。 | `.json` | `.json`, `.html` | `JsonWorkflowConfig` |
| **`DocxWorkflow`** | docxファイルを処理。フロー：`docx -> 翻訳 -> エクスポート`。 | `.docx` | `.docx`, `.html` | `docxWorkflowConfig` |
| **`XlsxWorkflow`** | xlsxファイルを処理。フロー：`xlsx -> 翻訳 -> エクスポート`。 | `.xlsx`, `.csv` | `.xlsx`, `.html` | `XlsxWorkflowConfig` |
| **`SrtWorkflow`** | srtファイルを処理。フロー：`srt -> 翻訳 -> エクスポート`。 | `.srt` | `.srt`, `.html` | `SrtWorkflowConfig` |
| **`EpubWorkflow`** | epubファイルを処理。フロー：`epub -> 翻訳 -> エクスポート`。 | `.epub` | `.epub`, `.html` | `EpubWorkflowConfig` |
| **`HtmlWorkflow`** | htmlファイルを処理。フロー：`html -> 翻訳 -> エクスポート`。 | `.html`, `.htm` | `.html` | `HtmlWorkflowConfig` |

> インタラクティブ画面ではPDF形式でのエクスポートも可能です。

## Web UI と API サービスの起動

使いやすくするために、DocuTranslate は機能豊富な Web インターフェースと RESTful API を提供しています。

**サービスの起動:**

```bash
# サービスの起動（デフォルトでポート8010をリッスン）
docutranslate -i

# ポートを指定して起動
docutranslate -i -p 8011

# CORSリクエストを許可
docutranslate -i --cors


# 環境変数でポートを指定することも可能
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **インタラクティブ画面**: サービス起動後、ブラウザで `http://127.0.0.1:8010` (または指定したポート) にアクセスしてください。
- **API ドキュメント**: 完全な API ドキュメント (Swagger UI) は `http://127.0.0.1:8010/docs` にあります。

## 使用方法

### 例 1: PDFファイルの翻訳 (`MarkdownBasedWorkflow` を使用)

これが最も一般的なユースケースです。`minerU` エンジンを使用して PDF を Markdown に変換し、その後 LLM を使用して翻訳します。ここでは非同期方式を例にします。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳機設定の構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AIプラットフォーム Base URL
        api_key="YOUR_ZHIPU_API_KEY",  # AIプラットフォーム API Key
        model_id="glm-4-air",  # モデル ID
        to_lang="English",  # ターゲット言語
        chunk_size=3000,  # テキスト分割サイズ
        concurrent=10,  # 同時並行数
        # glossary_generate_enable=True, # 用語集自動生成を有効化
        # glossary_dict={"Jobs":"ジョブズ"}, # 用語集を渡す
        # system_proxy_enable=True,# システムプロキシを有効化
    )

    # 2. コンバータ設定の構築 (minerUを使用)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # あなたの minerU Token
        formula_ocr=True  # 数式認識を有効化
    )

    # 3. メインワークフロー設定の構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンを指定
        converter_config=converter_config,  # コンバータ設定を渡す
        translator_config=translator_config,  # 翻訳機設定を渡す
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTMLエクスポート設定
    )
    
    # ローカルデプロイされたmineruサービスを使用する場合
    # from docutranslate.converter.x2md.converter_mineru_deploy import ConverterMineruDeployConfig
    # converter_config = ConverterMineruDeployConfig(
    #     base_url = "http://127.0.0.1:8000",
    #     output_dir= "./output",# mineruの制限により、解析後のファイルはoutput_dir下に保存されるため、定期的なクリーニングが必要です
    #     backend= "pipeline",
    #     start_page_id = 0,
    #     end_page_id = 99999,
    # )
    # workflow_config = MarkdownBasedWorkflowConfig(
    #     convert_engine="mineru_deploy",  # 解析エンジンを指定
    #     converter_config=converter_config,  # コンバータ設定を渡す
    #     translator_config=translator_config,  # 翻訳機設定を渡す
    #     html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTMLエクスポート設定
    # )

    # 4. ワークフローのインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルの読み込みと翻訳実行
    print("ファイルの読み込みと翻訳を開始します...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()
    print("翻訳完了！")

    # 6. 結果の保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像埋め込みMarkdown
    print("ファイルは ./output フォルダに保存されました。")

    # またはコンテンツ文字列を直接取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 2: TXTファイルの翻訳 (`TXTWorkflow` を使用)

プレーンテキストファイルの場合、ドキュメント解析（変換）ステップが不要なため、プロセスはより簡単です。ここでは非同期方式を例にします。

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. 翻訳機設定の構築
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
    )

    # 2. メインワークフロー設定の構築
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローのインスタンス化
    workflow = TXTWorkflow(config=workflow_config)

    # 4. ファイルの読み込みと翻訳実行
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果の保存
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXTファイルが保存されました。")

    # 翻訳後のテキストをエクスポートすることも可能
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 3: JSONファイルの翻訳 (`JsonWorkflow` を使用)

ここでは非同期方式を例にします。`JsonTranslatorConfig` の `json_paths` 項目で、翻訳対象のJSONパス（jsonpath-ng構文に準拠）を指定する必要があります。パスに一致する値のみが翻訳されます。

```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. 翻訳機設定の構築
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        json_paths=["$.*", "$.name"]  # jsonpath-ngパス構文に準拠、一致するパスの値が翻訳されます
    )

    # 2. メインワークフロー設定の構築
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローのインスタンス化
    workflow = JsonWorkflow(config=workflow_config)

    # 4. ファイルの読み込みと翻訳実行
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果の保存
    workflow.save_as_json(name="translated_notes.json")
    print("jsonファイルが保存されました。")

    # 翻訳後のjsonテキストをエクスポートすることも可能
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 4: docxファイルの翻訳 (`DocxWorkflow` を使用)

ここでは非同期方式を例にします。

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. 翻訳機設定の構築
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 選択肢 "replace" (置換), "append" (追記), "prepend" (前置)
        separator="\n",  # "append", "prepend" モード時の区切り文字
    )

    # 2. メインワークフロー設定の構築
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローのインスタンス化
    workflow = DocxWorkflow(config=workflow_config)

    # 4. ファイルの読み込みと翻訳実行
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果の保存
    workflow.save_as_docx(name="translated_notes.docx")
    print("docxファイルが保存されました。")

    # 翻訳後のdocxバイナリをエクスポートすることも可能
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 5: xlsxファイルの翻訳 (`XlsxWorkflow` を使用)

ここでは非同期方式を例にします。

```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. 翻訳機設定の構築
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 選択肢 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend" モード時の区切り文字
    )

    # 2. メインワークフロー設定の構築
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローのインスタンス化
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. ファイルの読み込みと翻訳実行
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果の保存
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("xlsxファイルが保存されました。")

    # 翻訳後のxlsxバイナリをエクスポートすることも可能
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 6: その他のワークフロー設定 (`HtmlWorkflow`、`EpubWorkflow` を使用)

ここでは非同期方式を例にします。

```python
# HtmlWorkflow
from docutranslate.translator.ai_translator.html_translator import HtmlTranslatorConfig
from docutranslate.workflow.html_workflow import HtmlWorkflowConfig, HtmlWorkflow


async def html():
    # 1. 翻訳機設定の構築
    translator_config = HtmlTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 選択肢 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend" モード時の区切り文字
    )

    # 2. メインワークフロー設定の構築
    workflow_config = HtmlWorkflowConfig(
        translator_config=translator_config,
    )
    workflow_html = HtmlWorkflow(config=workflow_config)


# EpubWorkflow
from docutranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
from docutranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
from docutranslate.workflow.epub_workflow import EpubWorkflowConfig, EpubWorkflow


async def epub():
    # 1. 翻訳機設定の構築
    translator_config = EpubTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        insert_mode="replace",  # 選択肢 "replace", "append", "prepend"
        separator="\n",  # "append", "prepend" モード時の区切り文字
    )

    # 2. メインワークフロー設定の構築
    workflow_config = EpubWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Epub2HTMLExporterConfig(cdn=True),
    )
    workflow_epub = EpubWorkflow(config=workflow_config)
```

## 前提条件と設定詳細

### 1. 大規模モデル API Key の取得

翻訳機能は大規模言語モデル（LLM）に依存しており、対応するAIプラットフォームから `base_url`、`api_key`、`model_id` を取得する必要があります。

> 推奨モデル：Volcengineの `doubao-seed-1-6-flash`、`doubao-seed-1-6` シリーズ、Zhipuの `glm-4-flash`、Alibaba Cloudの `qwen-plus`、`qwen-flash`、DeepSeekの `deepseek-chat` など。

> [302.AI](https://share.302.ai/BgRLAe)👈このリンクから登録すると、1ドルの無料クレジットがもらえます。

| プラットフォーム名 | API Keyの取得 | baseurl |
|:---|:---|:---|
| ollama | | http://127.0.0.1:11434/v1 |
| lm studio | | http://127.0.0.1:1234/v1 |
| 302.AI | [取得はこちら](https://share.302.ai/BgRLAe) | https://api.302.ai/v1 |
| openrouter | [取得はこちら](https://openrouter.ai/settings/keys) | https://openrouter.ai/api/v1 |
| openai | [取得はこちら](https://platform.openai.com/api-keys) | https://api.openai.com/v1/ |
| gemini | [取得はこちら](https://aistudio.google.com/u/0/apikey) | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek | [取得はこちら](https://platform.deepseek.com/api_keys) | https://api.deepseek.com/v1 |
| 智譜ai (Zhipu) | [取得はこちら](https://open.bigmodel.cn/usercenter/apikeys) | https://open.bigmodel.cn/api/paas/v4 |
| テンセント混元 | [取得はこちら](https://console.cloud.tencent.com/hunyuan/api-key) | https://api.hunyuan.cloud.tencent.com/v1 |
| アリババ百錬 | [取得はこちら](https://bailian.console.aliyun.com/?tab=model#/api-key) | https://dashscope.aliyuncs.com/compatible-mode/v1 |
| 火山引擎 (Volcengine) | [取得はこちら](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3 |
| SiliconFlow | [取得はこちら](https://cloud.siliconflow.cn/account/ak) | https://api.siliconflow.cn/v1 |
| DMXAPI | [取得はこちら](https://www.dmxapi.cn/token) | https://www.dmxapi.cn/v1 |
| 聚光AI | [取得はこちら](https://ai.juguang.chat/console/token) | https://ai.juguang.chat/v1 |

### 2. PDF解析エンジン（PDF翻訳が不要な場合は無視して構いません）

### 2.1 minerU Token の取得 (オンラインPDF解析、無料、推奨)

ドキュメント解析エンジンとして `mineru` を選択する場合（`convert_engine="mineru"`）、無料の Token を申請する必要があります。

1. [minerU 公式サイト](https://mineru.net/apiManage/docs) にアクセスし、登録して API を申請します。
2. [API Token 管理画面](https://mineru.net/apiManage/token) で新しい API Token を作成します。

> **注意**: minerU Token の有効期限は14日間です。期限切れ後は再作成してください。

### 2.2. docling エンジン設定 (ローカルPDF解析)

ドキュメント解析エンジンとして `docling` を選択する場合（`convert_engine="docling"`）、初回使用時に Hugging Face から必要なモデルをダウンロードします。

> [Github Releases](https://github.com/xunbu/docutranslate/releases) から `docling_artifact.zip` をダウンロードし、作業ディレクトリに解凍することをお勧めします。

**`docling` モデルダウンロード時のネットワーク問題解決策:**

1. **Hugging Face ミラーの設定 (推奨)**:

* **方法 A (環境変数)**: システム環境変数 `HF_ENDPOINT` を設定し、IDEまたはターミナルを再起動します。
   ```
   HF_ENDPOINT=https://hf-mirror.com
   ```
* **方法 B (コード内で設定)**: Pythonスクリプトの冒頭に以下のコードを追加します。

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **オフライン使用 (事前にモデルパッケージをダウンロード)**:

* [GitHub Releases](https://github.com/xunbu/docutranslate/releases) から `docling_artifact.zip` をダウンロードします。
* プロジェクトディレクトリに解凍します。
* 設定でモデルパスを指定します（モデルがスクリプトと同階層にない場合）：

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 解凍後のフォルダを指定
    code_ocr=True,
    formula_ocr=True
)
```

## FAQ

**Q: なぜ翻訳結果が原文のままなのですか？**
A: ログを確認し、エラー内容をチェックしてください。通常、AIプラットフォームの残高不足か、ネットワークの問題（システムプロキシを有効にする必要があるか確認）です。

**Q: 8010ポートが使用されていますが、どうすればいいですか？**
A: `-p` パラメータを使用して新しいポートを指定するか、`DOCUTRANSLATE_PORT` 環境変数を設定してください。

**Q: スキャンされたPDFの翻訳はサポートされていますか？**
A: はい、サポートされています。強力なOCR機能を備えた `mineru` 解析エンジンを使用してください。

**Q: 最初のPDF翻訳が非常に遅いのはなぜですか？**
A: `docling` エンジンを使用している場合、初回実行時に Hugging Face からモデルをダウンロードする必要があるためです。上記の「ネットワーク問題解決策」を参照して、このプロセスを高速化してください。

**Q: イントラネット（オフライン）環境で使用する方法は？**
A: 可能です。以下の条件を満たす必要があります：

1. **ローカルLLM**: [Ollama](https://ollama.com/) や [LM Studio](https://lmstudio.ai/) などのツールを使用してローカルに言語モデルをデプロイし、`TranslatorConfig` にローカルモデルの `base_url` を入力します。
2. **ローカルPDF解析エンジン**（PDF解析が必要な場合のみ）: `docling` エンジンを使用し、上記の「オフライン使用」の指示に従って事前にモデルパッケージをダウンロードしてください。

**Q: PDF解析のキャッシュメカニズムはどのように機能しますか？**
A: `MarkdownBasedWorkflow` は、ドキュメント解析（ファイルからMarkdownへの変換）の結果を自動的にキャッシュし、時間とリソースを消費する重複解析を回避します。キャッシュはデフォルトでメモリに保存され、最近の10件の解析を記録します。`DOCUTRANSLATE_CACHE_NUM` 環境変数でキャッシュ数を変更できます。

**Q: ソフトウェアでプロキシを使用するにはどうすればいいですか？**
A: ソフトウェアはデフォルトではシステムプロキシを使用しません。`TranslatorConfig` で `system_proxy_enable=True` を設定することで、システムプロキシを有効にできます。

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>

## 寄付・サポート

著者をサポートしてくださる方は、備考欄に理由を書いていただけると嬉しいです。

<p align="center">
  <img src="./images/赞赏码.jpg" alt="寄付コード" style="width: 250px;">
</p>