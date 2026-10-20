# AI 法规雷达

一个独立的法律政策监控网页项目，聚焦中国生成式人工智能、算法治理、AI 司法、内容标识与相关监管政策。

## 在线地址

- 网页：https://zishengliu.github.io/ai-law-radar/
- GitHub 仓库：https://github.com/zishengliu/ai-law-radar
- 个人主页：https://zishengliu.github.io/personal-portfolio/

## 功能
- 响应式网页仪表盘，支持关键词搜索、主题筛选、时间/优先级排序。
- 展示标题、发布机构、发布日期、摘要、法律关注点和官方原文链接。
- Python 标准库脚本通过 Google News RSS 搜索，并将查询限制在中国网信网、最高人民法院、中国政府网、工信部、国家发展改革委等官方域名。
- GitHub Actions 每天北京时间/新加坡时间 09:15 自动运行，更新数据并部署 GitHub Pages。
- 使用历史 ID 去重、标记新发现内容；抓取失败时提示数据源异常并尽量保留最近成功结果，不把网络错误误判为“没有新政策”。
- 页面提供固定的返回个人主页链接。

## 首次启用 GitHub Pages

GitHub 不允许此项目使用的自动化连接首次为仓库打开 Pages，所以需要在 GitHub 网页里手动设置一次：

1. 打开仓库 **Settings → Pages**。
2. 在 **Build and deployment → Source** 中选择 **GitHub Actions**。
3. 打开 **Settings → Actions → General → Workflow permissions**。如默认限制写入，请允许 **Read and write permissions**，供自动任务保存最新的 `data.json`。
4. 打开 **Actions**，运行 **Update and deploy AI Law Radar**，或向 `main` 推送一个提交触发部署。

完成首次设置后，工作流会在代码变更后部署网页，并每日自动运行。

## 本地运行

要求 Python 3.10+，仅使用标准库：

```bash
python scripts/update_law_radar.py
```

## 自动更新机制

`.github/workflows/pages.yml` 设置每日 `01:15 UTC`（北京时间/新加坡时间 `09:15`）运行，也支持手动触发。任务会尝试获取 5 组公开 RSS 搜索结果、进行关键词筛选和分类、与历史 ID 去重，保存数据后部署网页。

如果 RSS 服务或网络访问失败：
- 有旧的实时数据时，保留旧数据并显示异常状态；
- 尚无实时数据时，显示明确标注的离线官方网页样例；
- 离线样例不会伪装成刚刚抓取的信息。

## 使用说明

这是学习和信息发现工具，不构成法律意见。RSS 搜索可能遗漏未被索引的法规、公告或政策文件。应以官方原文为准，并由人工核对文件效力、适用对象、生效日期和具体义务。
