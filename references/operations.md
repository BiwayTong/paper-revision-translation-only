# 操作与恢复

从技能目录运行命令。PDF 定位和 Word 回填使用 Python、pdfplumber 和 lxml。先创建独立的任务文件夹（本例为 `job/`）。

## 从 PDF 定位到 Word

先渲染有标记的页面观察颜色、版心和页码。用下列命令查看每页的矩形填充色和批注数。

```sh
python scripts/highlights.py inspect report.pdf
```

下例参数仅演示一种版面。先创建输出目录，再把页码改成该报告中**论文的全部页面**（包含未标记的参考文献页），把裁切高度和颜色换成实测值。高度以 PDF 点数计，自页面顶部向下。RGB 为 0 至 1 的数值。

```sh
mkdir -p job
python scripts/highlights.py extract report.pdf submitted.docx job/scope.json \
  --pages 3 8 --y 50 790 --rgb 0.3203 0.7773 0.8555
```

工具按整个正文的字符流校验 PDF 与 Word，忽略排版空白并兼容连字，再把落在色带里的字形中心映射回 Word 的原始字符位置。同段不连续的标记保留为不同编号。输出包含底稿指纹、编号、PDF 页码、段落位置、起止偏移及高亮原文。

- PDF 高亮为批注时，读取 Highlight 批注的四边形并与字形相交，复用整篇对齐原则。扫描图像用页面渲染识别色带，OCR 仅供定位，以图面和 Word 原句校正。颜色或页眉随页变化时分页面确认。
- 表格、文本框、多栏、脚注、PDF 特殊字符可能影响阅读顺序。按实际段落或单元格上下文重建对应关系；不通过宽松的全文搜索替换重复短语。保留可核验的原文与位置。
- 先依据 `scope.json` 逐一核对选区。完成内容核查后，把英文基准稿保存为 `job/baseline.json`，例如 `{"P001":"The bridge opened in 2012."}`。每个高亮编号对应一段完整的选中文本。程序在翻译前核对编号，打包时从选区清单读取原始摘录。
- 如果输入只有编号摘录，可直接建立最小的 `job/scope.json`，例如 `{"spans":[{"id":"P001","text":"The bridge opened in 2012.","pages":[]}]}`。有报告页码时填写实际页码。可以先翻译和打包。回填 Word 前用匹配的原稿核实每个位置，并补齐完整的定位清单和底稿指纹。

## 每轮的实际调用

### 使用 Google Cloud 自动翻译

使用已启用 Cloud Translation API 的 Google Cloud 项目。可以在运行进程中设置环境变量 `GOOGLE_TRANSLATE_API_KEY`，或为 Python 安装 `google-auth[requests]` 并配置应用默认凭据（ADC）。使用个人 ADC 时，需要具备相应权限的配额项目，可通过 `GOOGLE_CLOUD_QUOTA_PROJECT` 指定。密钥留在本机的环境变量或密钥管理器中。实际提交给 Google 的是当前选中的片段，费用和配额以所用项目为准。[身份验证](https://cloud.google.com/translate/docs/authentication) · [官方接口](https://cloud.google.com/translate/docs/reference/rest/v2/translate) · [计费](https://cloud.google.com/translate/pricing)

```sh
python scripts/google_rounds.py job 1 zh
# 阅读 r1-zh-raw.json，将中文建议稿或作者修改稿写入 job/r1-zh-edit.json
python scripts/google_rounds.py job 1 en
# 阅读 r1-en-raw.json，将核对后的英文写入 job/r1-en-edit.json
```

第二轮和第三轮分别把轮次改为 `2` 和 `3`。英译中的输入是第一轮的基准稿或上一轮英文调整稿，中译英的输入始终是本轮中文调整稿。JSON 调整稿沿用基准稿的全部编号。对于 Google 原样返回的空格、标点或字符实体，保留原始输出，在调整稿中按语境处理。

每个成功段落独立记录翻译渠道、语言方向、输入与译文指纹。临时网络错误或限流缓解后重跑当前步骤，程序会从缺失的段落继续。出现 `SERVICE_DISABLED` 时，检查所用项目是否已启用 Cloud Translation API，或继续使用网页方式。遇到长度上限应按句界分段，记录各段位置及原始译文，再按原顺序回填。

### 使用 Google 翻译网页

没有 Cloud 凭据也可完成三轮。每次导出当前步骤的待译表，在 Google 翻译网页设置表内指定的英中方向，逐段提交 `source`，把显示的完整译文原样填入对应的 `translation`。保留编号、轮次、语言和源文。编辑者有网页访问权限时直接操作，否则请用户返回填好的表。每次都要实际取得本轮译文。[打开 Google 翻译](https://translate.google.com/)

```sh
python scripts/google_rounds.py job 1 zh --export-web r1-zh-web.json
# 填入网页译文后导入
python scripts/google_rounds.py job 1 zh --import-web r1-zh-web.json
```

中译英将 `zh` 换为 `en`，各轮各方向使用独立文件。部分导入会保存已填段落并列出缺少的编号。导入时程序核对源文、轮次和方向。归档中的 `provider` 用 `google-translate-web` 标记网页译文，用 `google-cloud-translation-v2` 标记 API 返回值。若两种渠道均不可用，交付当前待译表及进度。

## 回填与验证

第三轮英文回译原样存入 `job/r3-en-raw.json`，直接对照英文基准稿，仅修复确认的偏移，将结果另存为 `job/r3-en-edit.json`。对照基准稿时，若回译把 “The estimate may rise by 4–6% [7].” 改成 “The estimate will rise by 4–6% [7].”，只将 `will` 改回 `may`。若原句仅换了一种同义说法，最终稿采用作者原句。未发现具体问题时，编辑稿直接沿用回译，在 `job/review.md` 简记复核结果。

将最终对照检查稿保存为 `job/check.json`，将最小校对后的定稿保存为 `job/final.json`，两者使用相同的编号。将修改理由、中文稿来源、待核实问题、整篇词数及计入口径写入 `job/review.md`。只有摘录时给出选区词数。

```sh
python scripts/highlights.py merge submitted.docx job/scope.json job/final.json revised.docx
python scripts/package_process.py job process.zip
```

输出使用新文件名。工具核实底稿指纹、编号全集和每一处原文，按倒序替换以避免偏移，检查所有其他 Word 部件。常规正文和同一文字节点内的局部选区可直接处理。

若选区跨越斜体、超链接或多个文字节点，按原格式单元在副本中编辑，保留各节点的字符样式、域和链接目标；必要时用 Word 的范围编辑能力处理。遇到有歧义的边界，只回填能确证的部分。最后检查未选文字和结构，将 Word 渲染成页面检查。过程包包含带页码的编号摘录、每轮四份稿件、Google 翻译来源记录、基准稿与定稿对照和修改说明。
