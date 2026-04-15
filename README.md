<div align="center">
<p>English | <a href="README.zh-CN.md">简体中文</a></p>
</div>

# ohos-node

This project compiles Node.js for the OpenHarmony platform and releases pre-built packages.

## Get Pre-built Packages

Head to the [releases page](https://github.com/hqzing/ohos-node/releases) to download.

## Usage

**1. On an OpenHarmony PC**

Download the tarball with `curl` in the “Terminal” (HiShell), then extract it and add the bin directory to `PATH`.

```sh
cd ~
curl -L -O https://github.com/hqzing/ohos-node/releases/download/v24.2.0/node-v24.2.0-openharmony-arm64.tar.gz 
tar -zxf node-v24.2.0-openharmony-arm64.tar.gz
export PATH=$PATH:~/node-v24.2.0-openharmony-arm64/bin
alias node="node --jitless"

# You can now use the 'node' command.
```

Note: although current OpenHarmony PCs can execute self-signed binaries directly, this approach still has major restrictions.

The two most common ones:
1. Self-signed binaries lack JIT permission, so node must be started in JIT-less mode.  
2. They are granted no SELinux privileges, so you may hit various permission issues.

If these limits are unacceptable, consider:
1. Repackaging the tar into an hnp. For details, please refer to solution of [DevBox](https://gitcode.com/OpenHarmonyPCDeveloper/devbox).
2. Installing CodeArts IDE from the AppGallery, it ships its own Node.js runtime.

**2. On an OpenHarmony Dev-Board**

Push the tarball to the device with `hdc`, extract, and update `PATH`.

Example:
```sh
hdc file send node-v24.2.0-openharmony-arm64.tar.gz /data
hdc shell

cd /data
tar -zxf node-v24.2.0-openharmony-arm64.tar.gz
export PATH=$PATH:/data/node-v24.2.0-openharmony-arm64/bin

# You can now use the 'node' command.
```

**3. Inside the [OpenHarmony Container](https://github.com/hqzing/dockerharmony)**

Download the tarball with `curl` inside the container, extract, and add to `PATH`.

Example:
```sh
docker run -itd --name=ohos ghcr.io/hqzing/dockerharmony:latest
docker exec -it ohos sh

cd /root
curl -L -O https://github.com/hqzing/ohos-node/releases/download/v24.2.0/node-v24.2.0-openharmony-arm64.tar.gz 
tar -zxf node-v24.2.0-openharmony-arm64.tar.gz -C /opt
export PATH=$PATH:/opt/node-v24.2.0-openharmony-arm64/bin

# You can now use the 'node' command.
```

## Build from Source

**1. Manual Build**

You need a Linux x64 host to cross-compile Node.js with the supplied `build.sh`.

Example on Ubuntu 24.04 x64:
```sh
sudo apt update && sudo apt install -y build-essential unzip jq
./build.sh v24.2.0
```

**2. CI Build**

If you are familiar with GitHub Actions, reuse the workflow file in this repo to build on GitHub’s runners, and no local environment required.

Steps for your own builds:
1. Fork this repo.
2. Enable workflow under the “Actions” tab.
3. Push commits or create a release to trigger the workflow.
