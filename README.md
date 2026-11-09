# DeepSeek Search & Fetch CLI

一个基于 DeepSeek Search 与 Fetch API 的命令行程序，可搜索网页、抓取网页内容，并将抓取结果保存为 Markdown 文件。

## 环境要求

- Python 3.9 或更高版本
- 可用的 DeepSeek API Key，以及相应的 API 使用权限

## 安装

安装依赖：

```bash
python3 -m pip install requests PyYAML
```

## 配置

复制示例配置文件：

```bash
cp `config.yaml.example` `config.yaml`
```

编辑 `config.yaml`，填入 API Key：

```yaml
api_key: "你的 DeepSeek API Key"
base_url: "https://api.deepseek.com"
timeout: 30
```

`base_url` 和 `timeout` 为可选配置，默认分别是 `https://api.deepseek.com` 和 `30` 秒。仓库已将 `config.yaml` 加入 `.gitignore`，请勿将包含真实 API Key 的配置文件提交到版本控制。

也可以通过 `-c` 指定其他配置文件路径。该选项应放在子命令之前：

```bash
python3 `main.py` -c ./my-config.yaml search "DeepSeek"
```

## 使用方法

### 搜索网页

```bash
python3 `main.py` search "DeepSeek API 文档"
```

默认返回 10 条结果。可用 `-n` 设置返回条数，范围为 1 到 50：

```bash
python3 `main.py` search "Python asyncio" -n 5
```

使用 `--need-content` 请求搜索结果中的网页正文：

```bash
python3 `main.py` search "DeepSeek API 文档" --need-content
```

还可以提供原始问题或用于本地化结果的 IP 地址：

```bash
python3 `main.py` search "附近的图书馆" \
  --ori-question "我想找附近可以自习的地方" \
  --localization "203.0.113.10"
```

搜索词支持 `site:`、`lang:`、`after:` 等语法。使用 `--help` 查看命令参数：

```bash
python3 `main.py` search --help
```

### 抓取网页

```bash
python3 `main.py` fetch "https://example.com/article"
```

将抓取到的 Markdown 正文保存到文件：

```bash
python3 main.py fetch "https://example.com/article" -s article.md
```

```bash
python3 main.py fetch --help
```

## 错误处理

程序会报告网络请求错误、HTTP 状态码及对应提示。遇到限流、超时或服务器错误时，可稍后重试；遇到认证或余额相关错误时，请检查 API Key 和账号状态。
