#!/bin/sh
set -e

if [ -z "$1" ]; then
    echo "usage: ./build.sh <branch name or tag name>"
    echo "example: ./build.sh main"
    echo "example: ./build.sh v24.2.0"
    exit 1
fi

version=$1

query_component() {
  component=$1
  curl -fsSL 'https://ci.openharmony.cn/api/daily_build/build/list/component' \
    -H 'Accept: application/json, text/plain, */*' \
    -H 'Content-Type: application/json' \
    --data-raw '{"projectName":"openharmony","branch":"master","pageNum":1,"pageSize":10,"deviceLevel":"","component":"'${component}'","type":1,"startTime":"2025080100000000","endTime":"20990101235959","sortType":"","sortField":"","hardwareBoard":"","buildStatus":"success","buildFailReason":"","withDomain":1}'
}

# setup openharmony sdk
sdk_download_url=$(query_component "ohos-sdk-public" | jq -r ".data.list.dataList[0].obsPath")
curl $sdk_download_url -o ohos-sdk-public.tar.gz
mkdir -p /opt/ohos-sdk
tar -zxf ohos-sdk-public.tar.gz -C /opt/ohos-sdk
rm -rf ohos-sdk-public.tar.gz /opt/ohos-sdk/windows
cd /opt/ohos-sdk/linux
unzip -q toolchains-*.zip
rm -rf *.zip
cd -

# setup LLVM-19
llvm19_download_url=$(query_component "LLVM-19" | jq -r ".data.list.dataList[0].obsPath")
curl $llvm19_download_url -o LLVM-19.tar.gz
mkdir -p /opt/llvm-19
tar -zxf LLVM-19.tar.gz -C /opt/llvm-19
rm -rf LLVM-19.tar.gz
cd /opt/llvm-19
tar -zxf llvm-linux-x86_64.tar.gz
tar -zxf ohos-sysroot.tar.gz
rm -rf *.tar.gz
cd -

# download Node.js source code
git clone --branch $version --depth 1 https://github.com/nodejs/node.git

# build
cd node
need_patch_versions="v24.2.0 v24.3.0 v24.4.0 v24.4.1 v24.5.0 v24.6.0"
if echo " $need_patch_versions " | grep -q " $version "; then
    patch -p1 < ../0001-fix-argument-list-too-long.patch
fi
export CC="/opt/llvm-19/llvm/bin/aarch64-unknown-linux-ohos-clang"
export CXX="/opt/llvm-19/llvm/bin/aarch64-unknown-linux-ohos-clang++"
need_no_error_versions="v24.2.0 v24.3.0 v24.4.0 v24.4.1 v24.5.0 v24.6.0 v24.7.0 v24.8.0"
if echo " $need_no_error_versions " | grep -q " $version "; then
    export CC="$CC -Wno-error=implicit-function-declaration"
    export CXX="$CXX -Wno-error=implicit-function-declaration"
fi
export CC_host="gcc"
export CXX_host="g++"
./configure --dest-cpu=arm64 --dest-os=openharmony --cross-compiling --prefix=node-${version}-openharmony-arm64 --fully-static --enable-static
make -j$(nproc)
make install


# code signing
/opt/ohos-sdk/linux/toolchains/lib/binary-sign-tool sign \
  -inFile node-${version}-openharmony-arm64/bin/node \
  -outFile node-${version}-openharmony-arm64/bin/node \
  -selfSign 1

cp LICENSE node-${version}-openharmony-arm64
tar -zcf node-${version}-openharmony-arm64.tar.gz node-${version}-openharmony-arm64
