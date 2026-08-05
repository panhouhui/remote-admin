<p align="center">
  <img src="res/kanyu-logo.png" alt="瞰域" width="128"><br>
  <b>瞰域</b><br>
  <span>基于 RustDesk 二次开发的远程桌面客户端</span><br>
  <a href="#快速开始">快速开始</a> ·
  <a href="#手动构建">手动构建</a> ·
  <a href="#使用-docker-构建">Docker 构建</a> ·
  <a href="#目录结构">目录结构</a> ·
  <a href="#截图">截图</a>
</p>

> [!Caution]
> **使用说明：**瞰域仅用于合法授权的远程协助、设备维护和自建环境管理。请不要把它用于未经允许的访问、控制或监控场景。

瞰域保留了 RustDesk 的核心连接与控制能力，同时把界面名称、图标、文案和默认分发方式整理成了自己的版本。它适合自建服务端、内网协助，以及需要统一品牌的二开场景。

如果你正在使用自建服务端，请确保客户端、转发节点和密钥配置一致；这样连接、注册和后续的中继过程才会稳定。

## 快速开始

1. 准备好你的服务端地址、转发地址和密钥。
2. 启动客户端，在设置里填入对应信息。
3. 保存后重新连接，即可开始使用。

如果你只是想看怎么从源码打包，可以直接跳到下面的构建部分。

## 手动构建

- 准备好 Rust 开发环境和 C++ 编译环境
- 安装 [vcpkg](https://github.com/microsoft/vcpkg)，并正确设置 `VCPKG_ROOT` 环境变量
  - Windows：`vcpkg install libvpx:x64-windows-static libyuv:x64-windows-static opus:x64-windows-static aom:x64-windows-static`
  - Linux/macOS：`vcpkg install libvpx libyuv opus aom`
- 运行 `cargo run`

## 构建文档

桌面端目前以 Flutter 为主，Sciter 相关目录保留给历史兼容和参考。更完整的构建说明可以继续参考上游的持续集成配置：

https://github.com/rustdesk/rustdesk/blob/master/.github/workflows/flutter-build.yml

## 在 Linux 上构建

### Ubuntu 18（Debian 10）

```sh
sudo apt install -y zip g++ gcc git curl wget nasm yasm libgtk-3-dev clang libxcb-randr0-dev libxdo-dev \
        libxfixes-dev libxcb-shape0-dev libxcb-xfixes0-dev libasound2-dev libpulse-dev cmake make \
        libclang-dev ninja-build libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libpam0g-dev
```

### openSUSE Tumbleweed

```sh
sudo zypper install gcc-c++ git curl wget nasm yasm gcc gtk3-devel clang libxcb-devel libXfixes-devel cmake alsa-lib-devel gstreamer-devel gstreamer-plugins-base-devel xdotool-devel pam-devel
```

### Fedora 28（CentOS 8）

```sh
sudo yum -y install gcc-c++ git curl wget nasm yasm gcc gtk3-devel clang libxcb-devel libxdo-devel libXfixes-devel pulseaudio-libs-devel cmake alsa-lib-devel gstreamer1-devel gstreamer1-plugins-base-devel pam-devel
```

### Arch（Manjaro）

```sh
sudo pacman -Syu --needed unzip git cmake gcc curl wget yasm nasm zip make pkg-config clang gtk3 xdotool libxcb libxfixes alsa-lib pipewire
```

### 安装 vcpkg

```sh
git clone https://github.com/microsoft/vcpkg
cd vcpkg
git checkout 2023.04.15
cd ..
vcpkg/bootstrap-vcpkg.sh
export VCPKG_ROOT=$HOME/vcpkg
vcpkg/vcpkg install libvpx libyuv opus aom
```

### 修复 libvpx（仅 Fedora）

```sh
cd vcpkg/buildtrees/libvpx/src
cd *
./configure
sed -i 's/CFLAGS+=-I/CFLAGS+=-fPIC -I/g' Makefile
sed -i 's/CXXFLAGS+=-I/CXXFLAGS+=-fPIC -I/g' Makefile
make
cp libvpx.a $HOME/vcpkg/installed/x64-linux/lib/
cd
```

### 构建

```sh
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
git clone <你的仓库地址>
cd <仓库目录>
mkdir -p target/debug
wget https://raw.githubusercontent.com/c-smile/sciter-sdk/master/bin.lnx/x64/libsciter-gtk.so
mv libsciter-gtk.so target/debug
VCPKG_ROOT=$HOME/vcpkg cargo run
```

## 使用 Docker 构建

先克隆仓库并构建 Docker 镜像：

```sh
git clone <你的仓库地址>
cd <仓库目录>
git submodule update --init --recursive
docker build -t "kanyu-builder" .
```

如果你在国内网络环境下构建，可以按需做下面几项优化：

1. 把系统源换成国内镜像

   ```Dockerfile
   RUN sed -i "s|deb.debian.org|mirrors.aliyun.com|g" /etc/apt/sources.list && \
       sed -i "s|security.debian.org|mirrors.aliyun.com|g" /etc/apt/sources.list
   ```

2. 修改 Cargo 源

   ```Dockerfile
   RUN echo '[source.crates-io]' > ~/.cargo/config \
    && echo 'registry = "https://github.com/rust-lang/crates.io-index"'  >> ~/.cargo/config \
    && echo '# 替换成你偏好的镜像源'  >> ~/.cargo/config \
    && echo "replace-with = 'sjtu'"  >> ~/.cargo/config \
    && echo '# 上海交通大学镜像'  >> ~/.cargo/config \
    && echo '[source.sjtu]'   >> ~/.cargo/config \
    && echo 'registry = "https://mirrors.sjtug.sjtu.edu.cn/git/crates.io-index"'  >> ~/.cargo/config \
    && echo '' >> ~/.cargo/config
   ```

3. 给容器设置代理环境变量

   ```Dockerfile
   ENV http_proxy=http://host:port
   ENV https_proxy=http://host:port
   ```

4. 在 `docker build` 命令里追加代理参数

   ```sh
   docker build -t "kanyu-builder" . --build-arg http_proxy=http://host:port --build-arg https_proxy=http://host:port
   ```

### 构建程序

之后每次需要构建应用时，运行：

```sh
docker run --rm -it -v $PWD:/home/user/rustdesk -v kanyu-git-cache:/home/user/.cargo/git -v kanyu-registry-cache:/home/user/.cargo/registry -e PUID="$(id -u)" -e PGID="$(id -g)" kanyu-builder
```

注意：

- 第一次构建通常会比较慢，因为依赖需要先缓存下来，后续构建会快很多。
- 如果你要传入不同的构建参数，可以把参数追加在命令末尾；例如构建发布版，只需再加上 `--release`。
- 生成的可执行文件会放在你本机的 `target` 目录里。
- 如果看到下面这类提示，可以尝试去掉 `-e PUID="$(id -u)" -e PGID="$(id -g)"`：

  ```text
  usermod: user user is currently used by process 1
  groupmod: Permission denied.
  groupmod: cannot lock /etc/group; try again later.
  ```

  原因是容器入口脚本会检查 UID 和 GID；当它们与指定的环境变量不一致时，会尝试修改 `user` 的 UID/GID 并重新运行。重启后如果仍然读不到环境变量里的 UID/GID，就可能再次报错。

### 运行程序

生成的可执行文件位于 `target` 目录下，可直接运行调试版：

```sh
target/debug/瞰域
```

或者运行发布版：

```sh
target/release/瞰域
```

注意：

- 请确保在仓库根目录下运行这些命令，否则程序可能找不到所需资源。
- `install`、`run` 等其他 Cargo 子命令目前不建议通过这种方式在容器里执行，因为那样只会把程序安装或运行在容器中，而不是宿主机上。

## 目录结构

- **[libs/hbb_common](https://github.com/rustdesk/rustdesk/tree/master/libs/hbb_common)**：视频编解码、配置、TCP/UDP 封装、protobuf、文件传输相关的文件系统操作，以及其他通用工具函数
- **[libs/scrap](https://github.com/rustdesk/rustdesk/tree/master/libs/scrap)**：屏幕采集
- **[libs/enigo](https://github.com/rustdesk/rustdesk/tree/master/libs/enigo)**：平台相关的键盘和鼠标控制
- **[libs/clipboard](https://github.com/rustdesk/rustdesk/tree/master/libs/clipboard)**：Windows、Linux、macOS 的文件复制和粘贴实现
- **[src/ui](https://github.com/rustdesk/rustdesk/tree/master/src/ui)**：旧的 Sciter 界面（已弃用）
- **[src/server](https://github.com/rustdesk/rustdesk/tree/master/src/server)**：音频、剪贴板、输入、视频服务，以及网络连接
- **[src/client.rs](https://github.com/rustdesk/rustdesk/tree/master/src/client.rs)**：发起对等连接
- **[src/rendezvous_mediator.rs](https://github.com/rustdesk/rustdesk/tree/master/src/rendezvous_mediator.rs)**：与服务端协调注册、直连和中继连接
- **[src/platform](https://github.com/rustdesk/rustdesk/tree/master/src/platform)**：平台相关代码
- **[flutter](https://github.com/rustdesk/rustdesk/tree/master/flutter)**：桌面端和移动端的 Flutter 代码
- **[flutter/web/js](https://github.com/rustdesk/rustdesk/tree/master/flutter/web/v1/js)**：Flutter Web 客户端使用的 JavaScript

## 截图

![连接管理器](https://github.com/rustdesk/rustdesk/assets/28412477/db82d4e7-c4bc-4823-8e6f-6af7eadf7651)

![已连接到 Windows 电脑](https://github.com/rustdesk/rustdesk/assets/28412477/9baa91e9-3362-4d06-aa1a-7518edcbd7ea)

![文件传输](https://github.com/rustdesk/rustdesk/assets/28412477/39511ad3-aa9a-4f8c-8947-1cce286a46ad)

![TCP 隧道](https://github.com/rustdesk/rustdesk/assets/28412477/78e8708f-e87e-4570-8373-1360033ea6c5)
