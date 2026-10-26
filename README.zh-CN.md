<div align="center">
<p><a href="README.md">English</a> | 简体中文 </p>
</div>

# ohos-node

本项目为 OpenHarmony 平台构建 Node.js，并发布预构建包。

## 获取预构建包

预构建包可以从以下两个来源获取：

**1\. [GitHub Release](https://github.com/hqzing/ohos-node/releases)**

**2\. [分发源](https://ohos-node.com/dist)** — 自托管的 Node.js 分发源，与 [nodejs.org/dist](https://nodejs.org/dist) 兼容。

## 用法

**1\. 手动安装**

解压压缩包，将解压出的 `bin` 目录加入 `PATH` 即可：

```sh
tar -zxf node-v26.7.0-openharmony-arm64.tar.gz
export PATH=$PATH:$(realpath node-v26.7.0-openharmony-arm64/bin)

# 现在可以使用 node 命令了
```

**2\. 使用 nvm / fnm 安装**

通过 [Harmonybrew](https://atomgit.com/Harmonybrew) 安装 nvm / fnm，然后指定使用这个分发源：

```sh
# nvm
NVM_NODEJS_ORG_MIRROR=https://ohos-node.com/dist nvm install v26.7.0
# fnm
FNM_NODE_DIST_MIRROR=https://ohos-node.com/dist fnm install 26
```

## 从源码构建

**1\. 手动构建**

需要用一台 Linux x64 服务器来运行项目里的 build.sh，以实现 Node.js 的交叉编译。

这里以 Ubuntu 24.04 x64 作为示例：
```sh
sudo apt-get update && sudo apt-get install -y build-essential unzip jq
./build.sh v26.7.0
```
> 不支持 Ubuntu 26.04。

**2\. 使用流水线构建**

如果你熟悉 GitHub Actions，你可以直接复用项目内的工作流配置，使用 GitHub 的流水线来完成构建。

这种情况下，你使用的是 GitHub 提供的构建机，不需要自己准备构建环境。

只需要这么做，你就可以进行你的个人构建：
1. Fork 本项目，生成个人仓
2. 在个人仓的“Actions”菜单里面启用工作流
3. 在个人仓提交代码或发版本，触发流水线运行
