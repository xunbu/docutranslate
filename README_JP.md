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
  <a href="/README_ZH.md"><strong>简体中文</strong></a> / <a href="/README.md"><strong>English</strong></a> / <a href="/README_JP.md"><strong>日本語</strong></a> / <a href="/README_VI.md"><strong>Tiếng Việt</strong></a>
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

- **DocuTranslate**: 標準版。`minerU`（オンラインまたはローカルデプロイ）を使用してPDFを解析します。ローカルの minerU API 呼び出しをサポートしています。（推奨）
- **DocuTranslate_full**: 完全版。`docling` ローカルPDF解析エンジンを内蔵しています。minerU なしでオフラインPDF解析が必要な場合はこちらを選択してください。

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

DocuTranslate は **ワークフロー (Workflow)** システムを使用しています。各ワークフローは、特定のファイルタイプ向けの完全な翻訳パイプラインです。

**基本フロー：**
1. ファイルタイプに基づいてワークフローを選択
2. ワークフローを設定（LLM、解析エンジン、出力形式）
3. 翻訳を実行
4. 結果を保存

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

### シンプルな Client SDK の使用 (推奨)

翻訳を始める最も簡単な方法は `Client` クラスを使用することです。これはシンプルで直感的な API を提供します：

```python
from docutranslate.sdk import Client

# AI プラットフォームの設定でクライアントを初期化
client = Client(
    api_key="YOUR_OPENAI_API_KEY",  # またはその他の AI プラットフォーム API キー
    base_url="https://api.openai.com/v1/",
    model_id="gpt-4o",
    to_lang="中文",
    concurrent=10,  # 同時リクエスト数
)

# 例 1: テキストファイルを翻訳 (PDF 解析エンジンが不要)
result = client.translate("path/to/your/document.txt")
print(f"翻訳完了！保存先: {result.save()}")

# 例 2: PDF ファイルを翻訳 (mineru_token またはローカルデプロイが必要)
# 方式 A: オンライン MinerU を使用 (token が必要: https://mineru.net/apiManage/token)
result = client.translate(
    "path/to/your/document.pdf",
    convert_engine="mineru",
    mineru_token="YOUR_MINERU_TOKEN",  # MinerU Token に置き換える
    formula_ocr=True,  # 数式認識を有効化
)
result.save(fmt="html")

# 方式 B: ローカルデプロイの MinerU を使用 (イントラネット/オフライン環境推奨)
# ローカル MinerU サービスを先に起動してください, 参考: https://github.com/opendatalab/MinerU
result = client.translate(
    "path/to/your/document.pdf",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # ローカル MinerU アドレス
    mineru_deploy_backend="hybrid-auto-engine",  # バックエンドタイプ
)
result.save(fmt="markdown")

# 例 3: Docx ファイルを翻訳 (書式保持)
result = client.translate(
    "path/to/your/document.docx",
    insert_mode="replace",  # replace/append/prepend
)
result.save(fmt="docx")  # docx フォーマットで保存

# 例 4: Base64 エンコード文字列としてエクスポート (API 転送用)
base64_content = result.export(fmt="html")
print(f"エクスポートコンテンツ長さ: {len(base64_content)}")

# 基盤のワークフローにアクセスして高度な操作を行うことも可能
# workflow = result.workflow
```

**Client の機能:**
- **自動検出**: ファイル类型を自動検出し、適切なワークフローを選択
- **柔軟な設定**: 翻訳呼び出しごとにデフォルト設定を上書き可能
- **複数の出力オプション**: ディスクに保存または Base64 文字列としてエクスポート
- **非同期サポート**: 同時翻訳タスクには `translate_async()` を使用

#### Client SDK パラメータ一覧

| パラメータ | タイプ | デフォルト | 説明 |
|:---|:---|:---|:---|
| **api_key** | `str` | - | AI プラットフォーム API キー |
| **base_url** | `str` | - | AI プラットフォームベース URL（例: `https://api.openai.com/v1/`） |
| **model_id** | `str` | - | 翻訳に使用するモデル ID |
| **to_lang** | `str` | - | ターゲット言語（例: `"中文"`、`"English"`、`"日本語"`） |
| **concurrent** | `int` | 10 | 同時 LLM リクエスト数 |
| **convert_engine** | `str` | `"mineru"` | PDF 解析エンジン: `"mineru"`、`"docling"`、`"mineru_deploy"` |
| **md2docx_engine** | `str` | `"auto"` | Markdown から Docx への変換エンジン: `"python"`（純Python）、`"pandoc"`（Pandoc を使用）、`"auto"`（インストールされていればPandocを使用，否则はPython）、`null`（docxを生成しない） |
| **mineru_deploy_base_url** | `str` | - | ローカル minerU API アドレス（`convert_engine="mineru_deploy"` の場合） |
| **mineru_deploy_parse_method** | `str` | `"auto"` | ローカル minerU 解析方法: `"auto"`, `"txt"`, `"ocr"` |
| **mineru_deploy_table_enable** | `bool` | `True` | ローカル minerU テーブル認識を有効化するか |
| **mineru_token** | `str` | - | minerU API Token（オンライン minerU 使用時） |
| **skip_translate** | `bool` | `False` | 翻訳をスキップしてドキュメントのみを解析 |
| **output_dir** | `str` | `"./output"` | `save()` メソッドのデフォルト出力ディレクトリ |
| **chunk_size** | `int` | 3000 | LLM 処理のテキストチャンクサイズ |
| **temperature** | `float` | 0.3 | LLM 温度パラメータ |
| **timeout** | `int` | 60 | リクエストタイムアウト（秒） |
| **retry** | `int` | 3 | 失敗時の再試行回数 |
| **provider** | `str` | `"auto"` | AI プロバイダータイプ（auto、openai、azure など） |
| **force_json** | `bool` | `False` | 強制 JSON 出力モード |
| **rpm** | `int` | - | 1分あたりのリクエスト数制限 |
| **tpm** | `int` | - | 1分あたりのトークン数制限 |

#### Result メソッド一覧

| メソッド | パラメータ | 説明 |
|:---|:---|:---|
| **save()** | `output_dir`, `name`, `fmt` | 翻訳結果をディスクに保存 |
| **export()** | `fmt` | Base64 エンコード文字列としてエクスポート |
| **supported_formats** | - | サポートされている出力フォーマット一覧を取得 |
| **workflow** | - | 基盤のワークフローオブジェクトにアクセス |

```python
import asyncio
from docutranslate.sdk import Client

async def translate_multiple():
    client = Client(
        api_key="YOUR_API_KEY",
        base_url="https://api.openai.com/v1/",
        model_id="gpt-4o",
        to_lang="中文",
    )

    # 複数のファイルを同時に翻訳
    files = ["doc1.pdf", "doc2.docx", "notes.txt"]
    results = await asyncio.gather(
        *[client.translate_async(f) for f in files]
    )

    for r in results:
        print(f"保存先: {r.save()}")

asyncio.run(translate_multiple())
```

### Workflow API の使用（高度な制御）

より精细な制御が必要な場合は、Workflow API を直接使用してください。すべてのワークフローは同じパターンに従います：

```python
# パターン:
# 1. TranslatorConfig を作成（LLM設定）
# 2. WorkflowConfig を作成（ワークフロー設定）
# 3. Workflow インスタンスを作成
# 4. workflow.read_path(ファイル)
# 5. await workflow.translate_async()
# 6. workflow.save_as_*(name=...) または export_to_*(...)
```

#### 利用可能なワークフローと出力メソッド

| ワークフロー | 入力形式 | save_as_* | export_to_* | 主要設定オプション |
|:---|:---|:---|:---|:---|
| **MarkdownBasedWorkflow** | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` | `html`, `markdown`, `markdown_zip`, `docx` | `html`, `markdown`, `markdown_zip`, `docx` | `convert_engine`, `md2docx_engine`, `translator_config` |
| **TXTWorkflow** | `.txt` | `txt`, `html` | `txt`, `html` | `translator_config` |
| **JsonWorkflow** | `.json` | `json`, `html` | `json`, `html` | `translator_config`, `json_paths` |
| **DocxWorkflow** | `.docx` | `docx`, `html` | `docx`, `html` | `translator_config`, `insert_mode` |
| **XlsxWorkflow** | `.xlsx`, `.csv` | `xlsx`, `html` | `xlsx`, `html` | `translator_config`, `insert_mode` |
| **SrtWorkflow** | `.srt` | `srt`, `html` | `srt`, `html` | `translator_config` |
| **EpubWorkflow** | `.epub` | `epub`, `html` | `epub`, `html` | `translator_config`, `insert_mode` |
| **HtmlWorkflow** | `.html`, `.htm` | `html` | `html` | `translator_config`, `insert_mode` |
| **AssWorkflow** | `.ass` | `ass`, `html` | `ass`, `html` | `translator_config` |

#### 主要設定オプション

**共通 TranslatorConfig オプション:**

| オプション | タイプ | デフォルト | 説明 |
|:---|:---|:---|:---|
| `base_url` | `str` | - | AI プラットフォームベース URL |
| `api_key` | `str` | - | AI プラットフォーム API キー |
| `model_id` | `str` | - | モデル ID |
| `to_lang` | `str` | - | ターゲット言語 |
| `chunk_size` | `int` | 3000 | テキストチャンクサイズ |
| `concurrent` | `int` | 10 | 同時リクエスト数 |
| `temperature` | `float` | 0.3 | LLM 温度 |
| `timeout` | `int` | 60 | リクエストタイムアウト（秒） |
| `retry` | `int` | 3 | 再試行回数 |

**フォーマット固有オプション:**

| オプション | 適用ワークフロー | 説明 |
|:---|:---|:---|
| `insert_mode` | Docx, Xlsx, Html, Epub | `"replace"`（デフォルト）, `"append"`, `"prepend"` |
| `json_paths` | Json | JSONPath 式（例: `["$.*", "$.name"]`） |
| `separator` | Docx, Xlsx, Html, Epub | append/prepend モードのテキスト区切り文字 |
| `convert_engine` | MarkdownBased | `"mineru"`（デフォルト）, `"docling"`, `"mineru_deploy"` |

#### 例 1: PDFファイルの翻訳 (`MarkdownBasedWorkflow` を使用)

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

### その他のワークフロー

すべてのワークフローは同じパターンに従います。対応する設定とワークフローをインポートして設定します：

```python
# TXT: from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
# JSON: from docutranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
# DOCX: from docutranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
# XLSX: from docutranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig
# EPUB: from docutranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
# HTML: from docutranslate.workflow.html_workflow import HtmlWorkflow, HtmlWorkflowConfig
# SRT:  from docutranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
# ASS:   from docutranslate.workflow.ass_workflow import AssWorkflow, AssWorkflowConfig
```

主な設定オプション：
- **insert_mode**: `"replace"`, `"append"`, `"prepend"` (docx/xlsx/html/epub 用)
- **json_paths**: JSON 翻訳用の JSONPath 式 (例: `["$.*", "$.name"]`)
- **separator**: `"append"` / `"prepend"` モード用のテキスト区切り文字

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

### 2.3. ローカルデプロイ MinerU サービス

オフライン/イントラネット環境では、ローカルデプロイの `minerU` を推奨します。パフォーマンス向上、API制限なし。`mineru_deploy_base_url` に minerU API アドレスを設定してください。

**Client SDK:**
```python
from docutranslate.sdk import Client

client = Client(
    api_key="YOUR_LLM_API_KEY",
    model_id="llama3",
    to_lang="中文",
    convert_engine="mineru_deploy",
    mineru_deploy_base_url="http://127.0.0.1:8000",  # minerU API アドレス
)
result = client.translate("document.pdf")
result.save(fmt="markdown")
```

## FAQ

**Q: 翻訳結果が原文のまま？**
A: ログを確認。通常、AIプラットフォーム残高不足またはネットワーク問題。

**Q: 8010ポート使用中？**
A: `docutranslate -i -p 8011` または `DOCUTRANSLATE_PORT=8011`。

**Q: スキャンPDF対応？**
A: はい。`mineru` エンジンのOCR機能を使用。

**Q: 最初のPDF翻訳が遅い？**
A: `docling` は初回モデルダウンロードが必要。Hugging Face mirror または artifact 事前ダウンロードで解決。

**Q: イントラネット/オフライン使用？**
A: 可能。ローカルLLM（Ollama/LM Studio）とローカル minerU または docling を使用。

**Q: PDFキャッシュ機構？**
A: `MarkdownBasedWorkflow` がメモリ内に解析結果をキャッシュ（最近10件）。`DOCUTRANSLATE_CACHE_NUM` で変更可。

**Q: プロキシ有効化？**
A: TranslatorConfig で `system_proxy_enable=True` を設定。

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
