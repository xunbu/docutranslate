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
  大規模言語モデルをベースにした軽量なローカルファイル翻訳ツール
</p>

- ✅ **多様なフォーマットをサポート**：`pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt`、`ass`など、さまざまなファイルを翻訳できます。
- ✅ **用語集の自動生成**：用語の整合性を保つための用語集の自動生成をサポートします。
- ✅ **PDFの表、数式、コードの認識**：`docling`、`mineru` PDF解析エンジンにより、学術論文によく見られる表、数式、コードを認識し翻訳します。
- ✅ **JSON翻訳**：JSONパス（`jsonpath-ng`構文仕様）を使用して、JSON内で翻訳が必要な値を指定できます。
- ✅ **Word/Excelのフォーマットを維持した翻訳**：`docx`、`xlsx`ファイルの元のフォーマットを維持したまま翻訳をサポートします（現在
  `doc`、`xls`ファイルは未対応）。
- ✅ **複数のAIプラットフォームをサポート**：ほとんどのAIプラットフォームに対応しており、カスタムプロンプトによる並行高性能なAI翻訳が可能です。
- ✅ **非同期サポート**：高性能なシーン向けに設計され、完全な非同期サポートを提供し、複数のタスクを並行実行できるサービスインターフェースを実現します。
- ✅ **LAN、複数人での使用をサポート**：ローカルエリアネットワーク内で複数人が同時に使用できます。
- ✅ **インタラクティブなWebインターフェース**：すぐに使えるWeb UIとRESTful APIを提供し、統合と使用が容易です。
- ✅ **小型でマルチプラットフォーム対応の統合パッケージ**：40MB未満のWindows、Mac用統合パッケージ（`docling`
  ローカルPDF解析を使用しないバージョン）。

> `pdf`を翻訳する際、まずMarkdownに変換されるため、元のレイアウトが**失われます**。レイアウトにこだわりがあるユーザーはご注意ください。

> QQ交流グループ：1047781902

**UI画面**：
![翻訳効果](/images/UI界面.png)

**論文翻訳**：
![翻訳効果](/images/論文翻訳.png)

**小説翻訳**：
![翻訳効果](/images/小说翻译.png)

## 統合パッケージ

すぐに始めたいユーザーのために、[GitHub Releases](https://github.com/xunbu/docutranslate/releases)
で統合パッケージを提供しています。ダウンロードして解凍し、AIプラットフォームのAPIキーを入力するだけで使用を開始できます。

- **DocuTranslate**: 標準版。オンラインの`minerU`エンジンを使用してPDFドキュメントを解析します。ローカルでのPDF解析が不要な場合はこのバージョンを選択してください（推奨）。
- **DocuTranslate_full**: 完全版。`docling`ローカルPDF解析エンジンを内蔵しています。ローカルでのPDF解析が必要な場合はこのバージョンを選択してください。

## インストール

### pipを使用

```bash
# 基本的なインストール
pip install docutranslate

# doclingを使用してローカルでPDFを解析する場合
pip install docutranslate[docling]
```

### uvを使用

```bash
# 環境の初期化
uv init

# 基本的なインストール
uv add docutranslate

# docling拡張機能のインストール
uv add docutranslate[docling]
```

### gitを使用

```bash
# 環境の初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

## コアコンセプト：ワークフロー (Workflow)

新しいDocuTranslateの中核は**ワークフロー (Workflow)**
です。各ワークフローは、特定のファイルタイプ専用に設計された、完全なエンドツーエンドの翻訳パイプラインです。巨大な単一クラスと対話する代わりに、ファイルタイプに応じて適切なワークフローを選択し、設定します。

**基本的な使用手順は以下の通りです：**

1. **ワークフローの選択**：入力ファイルタイプ（例：PDF/WordまたはTXT）に応じて、`MarkdownBasedWorkflow`や`TXTWorkflow`
   などのワークフローを選択します。
2. **設定の構築**：選択したワークフローに対応する設定オブジェクト（例：`MarkdownBasedWorkflowConfig`
   ）を作成します。この設定オブジェクトには、以下のような必要なすべてのサブ設定が含まれます：
    * **コンバーター設定 (Converter Config)**: 元のファイル（PDFなど）をMarkdownに変換する方法を定義します。
    * **翻訳機設定 (Translator Config)**: 使用するLLM、APIキー、ターゲット言語などを定義します。
    * **エクスポーター設定 (Exporter Config)**: 出力フォーマット（HTMLなど）の特定のオプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳の実行**：ワークフローの`.read_*()`および`.translate()` / `.translate_async()`メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()`または`.save_as_*()`メソッドを呼び出して、翻訳結果を取得または保存します。

## 利用可能なワークフロー

| ワークフロー                      | 適用シーン                                                                  | 入力フォーマット                                  | 出力フォーマット               | コア設定クラス                       |
|:----------------------------|:-----------------------------------------------------------------------|:------------------------------------------|:-----------------------|:------------------------------|
| **`MarkdownBasedWorkflow`** | PDF、Word、画像などのリッチテキストドキュメントを処理。フロー：`ファイル -> Markdown -> 翻訳 -> エクスポート`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` など | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | プレーンテキストドキュメントを処理。フロー：`txt -> 翻訳 -> エクスポート`。                           | `.txt` およびその他のプレーンテキスト形式                  | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | JSONファイルを処理。フロー：`json -> 翻訳 -> エクスポート`。                                | `.json`                                   | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | docxファイルを処理。フロー：`docx -> 翻訳 -> エクスポート`。                                | `.docx`                                   | `.docx`, `.html`       | `DocxWorkflowConfig`          |
| **`XlsxWorkflow`**          | xlsxファイルを処理。フロー：`xlsx -> 翻訳 -> エクスポート`。                                | `.xlsx`, `.csv`                           | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | srtファイルを処理。フロー：`srt -> 翻訳 -> エクスポート`。                                  | `.srt`                                    | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | epubファイルを処理。フロー：`epub -> 翻訳 -> エクスポート`。                                | `.epub`                                   | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | htmlファイルを処理。フロー：`html -> 翻訳 -> エクスポート`。                                | `.html`, `.htm`                           | `.html`                | `HtmlWorkflowConfig`          |

> インタラクティブインターフェースではPDF形式でエクスポートできます。

## Web UIとAPIサービスの起動

利便性のために、DocuTranslateは機能豊富なWebインターフェースとRESTful APIを提供しています。

**サービスの起動:**

```bash
# サービスを起動し、デフォルトで8010ポートをリッスンします
docutranslate -i

# ポートを指定して起動
docutranslate -i -p 8011

# 環境変数でポートを指定することもできます
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **インタラクティブインターフェース**: サービス起動後、ブラウザで`http://127.0.0.1:8010`（または指定したポート）にアクセスしてください。
- **APIドキュメント**: 完全なAPIドキュメント（Swagger UI）は`http://127.0.0.1:8010/docs`にあります。

## 使用方法

### 例1：PDFファイルの翻訳 (`MarkdownBasedWorkflow`を使用)

これは最も一般的な使用例です。`minerU`エンジンを使用してPDFをMarkdownに変換し、LLMで翻訳します。ここでは非同期方式を例にとります。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AIプラットフォームのBase URL
        api_key="YOUR_ZHIPU_API_KEY",  # AIプラットフォームのAPIキー
        model_id="glm-4-air",  # モデルID
        to_lang="English",  # ターゲット言語
        chunk_size=3000,  # テキストのチャンクサイズ
        concurrent=10,  # 並列数
        # glossary_generate_enable=True, # 用語集の自動生成を有効にする
        # glossary_dict={"Jobs":"ジョブズ"}, # 用語集を渡す
        # system_proxy_enable=True,# システムプロキシを有効にする
    )

    # 2. コンバーターの設定を構築 (minerUを使用)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # あなたのminerUトークン
        formula_ocr=True  # 数式認識を有効にする
    )

    # 3. メインワークフローの設定を構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンを指定
        converter_config=converter_config,  # コンバーター設定を渡す
        translator_config=translator_config,  # 翻訳機設定を渡す
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTMLエクスポート設定
    )

    # 4. ワークフローをインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルを読み込んで翻訳を実行
    print("ファイルの読み込みと翻訳を開始します...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()
    print("翻訳が完了しました！")

    # 6. 結果を保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像が埋め込まれたMarkdown
    print("ファイルは ./output フォルダに保存されました。")

    # または直接コンテンツ文字列を取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 例2：TXTファイルの翻訳 (`TXTWorkflow`を使用)

プレーンテキストファイルの場合、ドキュメント解析（変換）ステップが不要なため、プロセスはより簡単です。ここでは非同期方式を例にとります。

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
    )

    # 2. メインワークフローの設定を構築
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = TXTWorkflow(config=workflow_config)

    # 4. ファイルを読み込んで翻訳を実行
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXTファイルが保存されました。")

    # 翻訳後のプレーンテキストをエクスポートすることもできます
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例3：JSONファイルの翻訳 (`JsonWorkflow`を使用)

ここでは非同期方式を例にとります。`JsonTranslatorConfig`の`json_paths`項目で、翻訳したいJSONパス（`jsonpath-ng`
構文仕様に準拠）を指定する必要があります。JSONパスに一致する値のみが翻訳されます。

```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        json_paths=["$.*", "$.name"]  # jsonpath-ng構文に準拠し、一致するパスの値が翻訳されます
    )

    # 2. メインワークフローの設定を構築
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = JsonWorkflow(config=workflow_config)

    # 4. ファイルを読み込んで翻訳を実行
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_json(name="translated_notes.json")
    print("JSONファイルが保存されました。")

    # 翻訳後のJSONテキストをエクスポートすることもできます
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例4：DOCXファイルの翻訳 (`DocxWorkflow`を使用)

ここでは非同期方式を例にとります。

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # 選択肢: "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用する区切り文字
    )

    # 2. メインワークフローの設定を構築
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = DocxWorkflow(config=workflow_config)

    # 4. ファイルを読み込んで翻訳を実行
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_docx(name="translated_notes.docx")
    print("docxファイルが保存されました。")

    # 翻訳後のdocxのバイナリデータをエクスポートすることもできます
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例5：XLSXファイルの翻訳 (`XlsxWorkflow`を使用)

ここでは非同期方式を例にとります。

```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # 選択肢: "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用する区切り文字
    )

    # 2. メインワークフローの設定を構築
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. ファイルを読み込んで翻訳を実行
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("xlsxファイルが保存されました。")

    # 翻訳後のxlsxのバイナリデータをエクスポートすることもできます
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

## 前提条件と設定詳細

### 1. 大規模モデルAPIキーの取得

翻訳機能は大規模言語モデルに依存しているため、対応するAIプラットフォームから`base_url`、`api_key`、`model_id`を取得する必要があります。

> 推奨モデル：火山引擎の`doubao-seed-1-6-flash`、`doubao-seed-1-6`シリーズ、智譜の`glm-4-flash`、阿里雲の`qwen-plus`、 `qwen-flash`、deepseekの`deepseek-chat`など。

> [302.AI](https://share.302.ai/BgRLAe)👈 このリンクから登録で1ドル分の無料クレジットを提供

| プラットフォーム名  | APIキー取得                                                                                      | baseurl                                                    |
|:-----------|:---------------------------------------------------------------------------------------------|:-----------------------------------------------------------|
| ollama     |                                                                                              | `http://127.0.0.1:11434/v1`                                |
| lm studio  |                                                                                              | `http://127.0.0.1:1234/v1`                                 |
| 302.AI     | [ここをクリックして取得](https://share.302.ai/BgRLAe)                                                   | `https://api.302.ai/v1`                                      |
| openrouter | [ここをクリックして取得](https://openrouter.ai/settings/keys)                                           | `https://openrouter.ai/api/v1`                             |
| openai     | [ここをクリックして取得](https://platform.openai.com/api-keys)                                          | `https://api.openai.com/v1/`                               |
| gemini     | [ここをクリックして取得](https://aistudio.google.com/u/0/apikey)                                        | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| deepseek   | [ここをクリックして取得](https://platform.deepseek.com/api_keys)                                        | `https://api.deepseek.com/v1`                              |
| 智譜ai       | [ここをクリックして取得](https://open.bigmodel.cn/usercenter/apikeys)                                   | `https://open.bigmodel.cn/api/paas/v4`                     |
| 騰訊混元       | [ここをクリックして取得](https://console.cloud.tencent.com/hunyuan/api-key)                             | `https://api.hunyuan.cloud.tencent.com/v1`                 |
| 阿里雲百煉      | [ここをクリックして取得](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | `https://dashscope.aliyuncs.com/compatible-mode/v1`        |
| 火山引擎       | [ここをクリックして取得](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | `https://ark.cn-beijing.volces.com/api/v3`                 |
| 硅基流動       | [ここをクリックして取得](https://cloud.siliconflow.cn/account/ak)                                       | `https://api.siliconflow.cn/v1`                            |
| DMXAPI     | [ここをクリックして取得](https://www.dmxapi.cn/token)                                                   | `https://www.dmxapi.cn/v1`                                 |
| 聚光AI       | [ここをクリックして取得](https://ai.juguang.chat/console/token)                                         | `https://ai.juguang.chat/v1`                               |

### 2. PDF解析エンジン（PDF翻訳が不要な場合は無視してください）

#### 2.1 minerUトークンの取得（オンラインPDF解析、無料、推奨）

ドキュメント解析エンジンとして`mineru`を選択した場合（`convert_engine="mineru"`）、無料のトークンを申請する必要があります。

1. [minerU公式サイト](https://mineru.net/apiManage/docs)にアクセスして登録し、APIを申請します。
2. [APIトークン管理画面](https://mineru.net/apiManage/token)で新しいAPIトークンを作成します。

> **注意**: minerUトークンの有効期間は14日間です。期限が切れたら再作成してください。

#### 2.2. doclingエンジンの設定（ローカルPDF解析）

ドキュメント解析エンジンとして`docling`を選択した場合（`convert_engine="docling"`）、初回使用時にHugging
Faceから必要なモデルがダウンロードされます。

> より良い選択肢は、[GitHub Releases](https://github.com/xunbu/docutranslate/releases)から`docling_artifact.zip`
> をダウンロードし、作業ディレクトリに解凍することです。

**`docling`モデルのダウンロード時のネットワーク問題解決策:**

1. **Hugging Faceミラーの設定（推奨）**:
    * **方法A（環境変数）**: システム環境変数`HF_ENDPOINT`を設定し、IDEまたはターミナルを再起動します。
      ```
      HF_ENDPOINT=https://hf-mirror.com
      ```

* **方法B（コード内で設定）**: Pythonスクリプトの冒頭に以下のコードを追加します。

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **オフラインでの使用（モデルパッケージを事前にダウンロード）**:
    * [GitHub Releases](https://github.com/xunbu/docutranslate/releases)から`docling_artifact.zip`をダウンロードします。
    * プロジェクトディレクトリに解凍します。

* 設定でモデルのパスを指定します（モデルがスクリプトと同じディレクトリにない場合）：

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 解凍したフォルダへのパス
    code_ocr=True,
    formula_ocr=True
)
```

## FAQ

**Q: なぜ翻訳結果が原文のままなのですか？**  
A: ログにどのようなエラーが出ているか確認してください。通常はAIプラットフォームの料金未払いやネットワークの問題（システムプロキシを有効にする必要があるか確認）が原因です。

**Q: 8010ポートが使用中です。どうすればいいですか？**  
A: `-p`パラメータで新しいポートを指定するか、`DOCUTRANSLATE_PORT`環境変数を設定してください。

**Q: スキャンされたPDFの翻訳はサポートしていますか？**  
A: はい、サポートしています。強力なOCR機能を持つ`mineru`解析エンジンを使用してください。

**Q: なぜ最初のPDF翻訳がとても遅いのですか？**  
A: `docling`エンジンを使用している場合、初回実行時にHugging
Faceからモデルをダウンロードする必要があります。このプロセスを高速化するには、上記の「ネットワーク問題解決策」を参照してください。

**Q: イントラネット（オフライン）環境で使用するにはどうすればいいですか？**  
A: 完全に可能です。以下の条件を満たす必要があります：

1. **ローカルLLM**: [Ollama](https://ollama.com/)や[LM Studio](https://lmstudio.ai/)などのツールを使用してローカルに言語モデルをデプロイし、
   `TranslatorConfig`にローカルモデルの`base_url`を記入します。
2. **ローカルPDF解析エンジン**（PDF解析にのみ必要）: `docling`エンジンを使用し、上記の「オフラインでの使用」の指示に従って事前にモデルパッケージをダウンロードします。

**Q: PDF解析のキャッシュメカニズムはどのように機能しますか？**  
A: `MarkdownBasedWorkflow`
は、ドキュメント解析（ファイルからMarkdownへの変換）の結果を自動的にキャッシュし、時間とリソースの重複消費を防ぎます。キャッシュはデフォルトでメモリに保存され、直近10回の解析が記録されます。
`DOCUTRANSLATE_CACHE_NUM`環境変数でキャッシュ数を変更できます。

**Q: ソフトウェアがプロキシを経由するようにするにはどうすればいいですか？**  
A: デフォルトではシステムプロキシを使用しません。`TranslatorConfig`で`system_proxy_enable=True`と設定することで有効にできます。

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>

## ご支援について

作者へのご支援を歓迎します。備考欄に支援の理由を記載していただけると幸いです。

<p align="center">
  <img src="./images/赞赏码.jpg" alt="支援用QRコード" style="width: 250px;">
</p>