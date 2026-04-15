#!/bin/sh
set -e

if [ -z "$1" ]; then
    echo "usage: ./build.sh <branch name or tag name>"
    echo "example: ./build.sh main"
    echo "example: ./build.sh v24.2.0"
    exit 1
fi

version=$1
workdir=$(pwd)

query_component() {
  component=$1
  curl -fsSL 'https://dcp.openharmony.cn/api/daily_build/build/list/component' \
    -H 'Accept: application/json, text/plain, */*' \
    -H 'Content-Type: application/json' \
    --data-raw '{"projectName":"openharmony","branch":"master","pageNum":1,"pageSize":10,"deviceLevel":"","component":"'${component}'","type":1,"startTime":"2025080100000000","endTime":"20990101235959","sortType":"","sortField":"","hardwareBoard":"","buildStatus":"success","buildFailReason":"","withDomain":1}'
}

# clean old files if exist
rm -rf *.tar.gz \
  ohos-sdk \
  llvm-19 \
  node \
  node-${version}-openharmony-arm64

# setup openharmony sdk
sdk_download_url=$(query_component "ohos-sdk-public" | jq -r ".data.list.dataList[0].obsPath")
curl $sdk_download_url -o ohos-sdk-public.tar.gz
mkdir ohos-sdk
tar -zxf ohos-sdk-public.tar.gz -C ohos-sdk
cd ohos-sdk/linux
unzip -q toolchains-*.zip
cd ../..

# setup LLVM-19
llvm19_download_url=$(query_component "LLVM-19" | jq -r ".data.list.dataList[0].obsPath")
curl $llvm19_download_url -o LLVM-19.tar.gz
mkdir llvm-19
tar -zxf LLVM-19.tar.gz -C llvm-19
cd llvm-19
tar -zxf llvm-linux-x86_64.tar.gz
tar -zxf ohos-sysroot.tar.gz
cd ..

git clone --branch $version --depth 1 https://github.com/nodejs/node.git
cd node

export CC="$workdir/llvm-19/llvm/bin/aarch64-unknown-linux-ohos-clang"
export CXX="$workdir/llvm-19/llvm/bin/aarch64-unknown-linux-ohos-clang++"
export CC_host="gcc"
export CXX_host="g++"

need_patch_versions="v24.2.0 v24.3.0 v24.4.0 v24.4.1 v24.5.0 v24.6.0"
if echo " $need_patch_versions " | grep -q " $version "; then
    patch -p1 < ../0001-fix-argument-list-too-long.patch
fi

need_no_error_versions="v24.2.0 v24.3.0 v24.4.0 v24.4.1 v24.5.0 v24.6.0 v24.7.0 v24.8.0"
if echo " $need_no_error_versions " | grep -q " $version "; then
    export CC="$CC -Wno-error=implicit-function-declaration"
    export CXX="$CXX -Wno-error=implicit-function-declaration"
fi

CONFIGURE_ARGS="--dest-cpu=arm64 \
  --dest-os=openharmony \
  --cross-compiling \
  --prefix=$workdir/node-${version}-openharmony-arm64"

# Node.js's build system enables Temporal by default when a Rust environment
# is available on the build machine.
# For details, see this PR: https://github.com/nodejs/node/pull/61806.
# However, enabling Temporal causes build failures during cross-compilation for OHOS.
# To ensure this build script works correctly on machines with Rust environments
# (such as GitHub Actions runners), Temporal is explicitly disabled here.
if ./configure --help 2>&1 | grep -q -- "--v8-disable-temporal-support"; then
    CONFIGURE_ARGS="$CONFIGURE_ARGS --v8-disable-temporal-support"
fi

./configure $CONFIGURE_ARGS
make -j$(nproc)
make install
cd ..

# code signing
$workdir/ohos-sdk/linux/toolchains/lib/binary-sign-tool sign \
  -inFile node-${version}-openharmony-arm64/bin/node \
  -outFile node-${version}-openharmony-arm64/bin/node \
  -selfSign 1

cp LICENSE node-${version}-openharmony-arm64
tar -zcf node-${version}-openharmony-arm64.tar.gz node-${version}-openharmony-arm64
