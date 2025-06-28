# 番茄小说下载器 - 优化增强版

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-AGPL--3.0-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-success.svg)]()

> **基于 [ying-ck/fanqienovel-downloader](https://github.com/ying-ck/fanqienovel-downloader) 的优化增强版本**

一个高效、稳定的番茄小说下载器，修复了原版的多个关键问题，提升了下载速度和文件质量。

## ✨ 主要改进

### 🚀 性能优化
- **Cookie获取加速**: 从原版的100次尝试优化到5次，大幅减少等待时间
- **网络请求优化**: 减少不必要的验证步骤，提升下载速度
- **智能重试机制**: 改进错误处理和重试逻辑

### 🔧 Bug修复
- **修复Cookie获取卡死问题**: 解决了原版在获取cookie时长时间卡住的问题
- **修复DownloadProgress错误**: 解决了`name 'DownloadProgress' is not defined`错误
- **修复TXT文件无法生成**: 确保每次下载都能正确生成TXT文件
- **完善字符解码**: 正确应用charset.json，彻底解决乱码问题

### 📁 新增功能
- **精简测试工具**: 新增`test_download.py`用于快速测试下载功能
- **自动化测试**: 新增`auto_test.py`用于验证程序功能
- **增强文件管理**: 同时生成JSON备份和TXT阅读文件

## 🎯 快速开始

### 环境要求
- Python 3.8+
- 网络连接

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行程序
```bash
# 运行主程序(优化版本)
python src/main.py

# 或运行精简测试版本
python test_download.py
```

## 🛠️ 使用方法

### 主程序功能
1. **直接下载**: 输入小说ID或链接直接下载
2. **搜索下载**: 通过关键词搜索并选择小说
3. **批量下载**: 支持批量下载多本小说
4. **更新小说**: 更新已下载的小说
5. **多格式保存**: 支持TXT、EPUB、HTML、LaTeX格式
6. **设置调整**: 自定义保存路径、格式等选项

### 快速测试
```bash
# 测试下载指定小说(ID: 7520128677003136024)
python test_download.py

# 自动化测试main.py功能
python auto_test.py
```

## 📊 支持的保存格式

| 格式 | 描述 | 文件扩展名 |
|------|------|-----------|
| 单文件TXT | 整本小说保存为一个文件 | `.txt` |
| 分章TXT | 每章单独保存 | `.txt` |
| EPUB | 电子书格式 | `.epub` |
| HTML | 网页格式 | `.html` |
| LaTeX | 学术文档格式 | `.tex` |

## 🔍 文件结构

```
fanqienovel-downloader-enhanced/
├── src/
│   ├── main.py           # 主程序(优化版本) ⭐
│   ├── server.py         # Web版服务器
│   ├── charset.json      # 字符解码映射表
│   └── ...
├── test_download.py      # 精简测试下载器 ⭐
├── auto_test.py          # 自动化测试脚本 ⭐
├── requirements.txt      # 依赖包列表
└── README.md            # 项目说明
```

## 🆚 版本对比

| 功能 | 原版 | 优化版 |
|------|------|--------|
| Cookie获取速度 | 慢(可能卡死) | 快(5秒内) |
| TXT文件生成 | 不稳定 | 稳定可靠 |
| 字符解码 | 部分乱码 | 完美解码 |
| 错误处理 | 基础 | 增强 |
| 测试工具 | 无 | 完整 |

## 🐛 已修复的问题

1. **Cookie获取卡死**: 原版在`_get_new_cookie`中使用巨大循环范围导致卡死
2. **DownloadProgress未定义**: 类定义和引用不匹配
3. **TXT文件生成失败**: 缺少return语句和错误的元数据处理
4. **字符乱码**: charset.json解码逻辑不完整
5. **进度显示错误**: 进度回调函数参数不匹配

## 💡 使用建议

- **首次使用**: 推荐使用`test_download.py`进行快速测试
- **日常使用**: 使用`src/main.py`获得完整功能
- **批量下载**: 利用多线程设置提升下载速度
- **格式选择**: TXT格式兼容性最好，EPUB适合电子阅读

## 📱 跨平台支持

| 系统 | 状态 | 备注 |
|------|------|------|
| Windows 10/11 | ✅ 完全支持 | |
| macOS | ✅ 完全支持 | 已测试 |
| Linux | ✅ 完全支持 | |
| Android (Termux) | ✅ 支持 | 参考原版说明 |

## 🙏 致谢

本项目基于 [ying-ck/fanqienovel-downloader](https://github.com/ying-ck/fanqienovel-downloader) 开发，感谢原作者 **Yck (ying-ck)**、**Yqy (qxqycb)** 和 **Lingo (lingo34)** 的出色工作。

在原版基础上，我们专注于性能优化和bug修复，让这个优秀的工具更加稳定可靠。

## ⚠️ 免责声明

此程序仅用于学习和研究Python网络爬虫技术，请勿用于商业用途或侵犯版权的行为。使用者需遵守相关法律法规和网站使用条款，因使用本程序产生的任何法律责任由使用者自行承担。

## 📄 开源协议

本程序遵循 [AGPL-3.0](LICENSE) 开源协议。使用本程序源码时请注明来源，并使用相同的开源协议。

## 🔗 相关链接

- **原项目**: [ying-ck/fanqienovel-downloader](https://github.com/ying-ck/fanqienovel-downloader)
- **问题反馈**: [Issues](../../issues)
- **功能请求**: [Issues](../../issues)

---

📢 **如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**
