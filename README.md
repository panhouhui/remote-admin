<p align="center">
  <img src="res/logo-header.svg" alt="瞰域 - 远程桌面"><br>
  <a href="#手动构建">手动构建</a> ·
  <a href="#使用-docker-构建">Docker 构建</a> ·
  <a href="#文件结构">文件结构</a> ·
  <a href="#截图">截图</a><br>
  <b>欢迎帮助我们把这份说明文档、<a href="https://github.com/rustdesk/rustdesk/tree/master/src/lang">RustDesk 界面</a>和<a href="https://github.com/rustdesk/doc.rustdesk.com">RustDesk 文档</a>翻译成你的母语</b>
</p>

> [!Caution]
> **免责声明：**<br>
> 瞰域的开发者不支持任何不道德或违法的用途。未经授权的访问、控制或侵犯隐私等行为都违反我们的原则。作者不对任何滥用本程序的行为负责。

交流频道：[Discord](https://discord.gg/nDceKgxnkV) | [Twitter](https://twitter.com/rustdesk) | [Reddit](https://www.reddit.com/r/rustdesk) | [YouTube](https://www.youtube.com/@rustdesk)

[![RustDesk Server Pro](https://img.shields.io/badge/RustDesk%20Server%20Pro-%E9%AB%98%E7%BA%A7%E5%8A%9F%E8%83%BD-blue)](https://rustdesk.com/pricing.html)

瞰域是一个用 Rust 编写的远程桌面方案。它开箱即用，无需复杂配置。你可以完全掌控自己的数据，也无需担心安全问题。你可以使用我们的中继/转发服务器，也可以[自己搭建](https://rustdesk.com/server)，或者[编写属于你自己的中继/转发服务器](https://github.com/rustdesk/rustdesk-server-demo)。

![示意图](https://user-images.githubusercontent.com/71636191/171661982-430285f0-2e12-4b1d-9957-4a58e375304d.png)

RustDesk 欢迎每个人参与贡献。想开始的话，请先阅读 [贡献指南](docs/CONTRIBUTING.md)。

[**常见问题**](https://github.com/rustdesk/rustdesk/wiki/FAQ)

[**二进制下载**](https://github.com/rustdesk/rustdesk/releases)

[**夜间构建**](https://github.com/rustdesk/rustdesk/releases/tag/nightly)

[<img src="https://f-droid.org/badge/get-it-on.png"
    alt="获取 F-Droid"
    height="80">](https://f-droid.org/en/packages/com.carriez.flutter_hbb)
[<img src="https://flathub.org/api/badge?svg&locale=en"
    alt="获取 Flathub"
    height="80">](https://flathub.org/apps/com.rustdesk.RustDesk)

## 依赖

桌面版可以使用 Flutter 或 Sciter（已弃用）作为图形界面。这里先说明 Sciter 的构建方式，因为它更容易上手。Flutter 版本的构建方法请参考我们的 [持续集成配置](https://github.com/rustdesk/rustdesk/blob/master/.github/workflows/flutter-build.yml)。

请自行下载 Sciter 动态库：

[Windows](https://raw.githubusercontent.com/c-smile/sciter-sdk/master/bin.win/x64/sciter.dll) |
[Linux](https://raw.githubusercontent.com/c-smile/sciter-sdk/master/bin.lnx/x64/libsciter-gtk.so) |
[macOS](https://raw.githubusercontent.com/c-smile/sciter-sdk/master/bin.osx/libsciter.dylib)

## 手动构建

- 准备好 Rust 开发环境和 C++ 编译环境
- 安装 [vcpkg](https://github.com/microsoft/vcpkg)，并正确设置 `VCPKG_ROOT` 环境变量
  - Windows：`vcpkg install libvpx:x64-windows-static libyuv:x64-windows-static opus:x64-windows-static aom:x64-windows-static`
  - Linux/macOS：`vcpkg install libvpx libyuv opus aom`
- 运行 `cargo run`

## [构建文档](https://rustdesk.com/docs/en/dev/build/)

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
git clone https://github.com/rustdesk/rustdesk
cd rustdesk
mkdir -p target/debug
wget https://raw.githubusercontent.com/c-smile/sciter-sdk/master/bin.lnx/x64/libsciter-gtk.so
mv libsciter-gtk.so target/debug
VCPKG_ROOT=$HOME/vcpkg cargo run
```

## 使用 Docker 构建

先克隆仓库并构建 Docker 镜像：

```sh
git clone https://github.com/rustdesk/rustdesk
cd rustdesk
git submodule update --init --recursive
docker build -t "rustdesk-builder" .
```

如果你在国内网络环境下构建，可以考虑下面几项优化：

1. 在 `Dockerfile` 里把系统源换成国内镜像

   ```Dockerfile
   RUN sed -i "s|deb.debian.org|mirrors.aliyun.com|g" /etc/apt/sources.list && \
       sed -i "s|security.debian.org|mirrors.aliyun.com|g" /etc/apt/sources.list
   ```

2. 在容器里修改 Cargo 源

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

4. 在 `docker build` 命令后追加代理参数

   ```sh
   docker build -t "rustdesk-builder" . --build-arg http_proxy=http://host:port --build-arg https_proxy=http://host:port
   ```

### 构建程序

之后每次需要构建应用时，运行：

```sh
docker run --rm -it -v $PWD:/home/user/rustdesk -v rustdesk-git-cache:/home/user/.cargo/git -v rustdesk-registry-cache:/home/user/.cargo/registry -e PUID="$(id -u)" -e PGID="$(id -g)" rustdesk-builder
```

注意：

- 第一次构建通常会比较慢，因为依赖需要先缓存下来；后续构建会快很多。
- 如果你要传入不同的构建参数，可以把参数追加在命令末尾 `<可选参数>` 的位置。比如构建优化过的发布版，只需在上面的命令后面加上 `--release`。
- 生成的可执行文件会在你系统的 `target` 目录里。
- 如果看到下面这类提示，可以尝试去掉 `-e PUID="$(id -u)" -e PGID="$(id -g)"`：

  ```text
  usermod: user user is currently used by process 1
  groupmod: Permission denied.
  groupmod: cannot lock /etc/group; try again later.
  ```

  原因是容器的入口脚本会检查 UID 和 GID；当它们与指定的环境变量不一致时，会尝试强制修改 `user` 的 UID/GID 并重新运行。但重启后如果仍然读不到环境变量里的 UID/GID，就可能再次报错。

### 运行程序

生成的可执行文件位于 `target` 目录下，可以直接运行调试版：

```sh
target/debug/rustdesk
```

也可以运行发布版：

```sh
target/release/rustdesk
```

注意：

- 请确保在 RustDesk 仓库根目录下运行这些命令，否则程序可能找不到所需资源。
- `install`、`run` 等其他 Cargo 子命令目前不支持通过这种方式在容器里执行，因为那样只会把程序安装或运行在容器里，而不是宿主机上。

## 文件结构

- **[libs/hbb_common](https://github.com/rustdesk/rustdesk/tree/master/libs/hbb_common)**：视频编解码、配置、TCP/UDP 封装、protobuf、文件传输相关的文件系统操作，以及其他工具函数
- **[libs/scrap](https://github.com/rustdesk/rustdesk/tree/master/libs/scrap)**：屏幕采集
- **[libs/enigo](https://github.com/rustdesk/rustdesk/tree/master/libs/enigo)**：平台相关的键盘/鼠标控制
- **[libs/clipboard](https://github.com/rustdesk/rustdesk/tree/master/libs/clipboard)**：Windows、Linux、macOS 的文件复制与粘贴实现
- **[src/ui](https://github.com/rustdesk/rustdesk/tree/master/src/ui)**：旧的 Sciter 界面（已弃用）
- **[src/server](https://github.com/rustdesk/rustdesk/tree/master/src/server)**：音频、剪贴板、输入、视频服务，以及网络连接
- **[src/client.rs](https://github.com/rustdesk/rustdesk/tree/master/src/client.rs)**：发起一个对等连接
- **[src/rendezvous_mediator.rs](https://github.com/rustdesk/rustdesk/tree/master/src/rendezvous_mediator.rs)**：与 [rustdesk-server](https://github.com/rustdesk/rustdesk-server) 通信，等待远程直连（TCP 打洞）或中继连接
- **[src/platform](https://github.com/rustdesk/rustdesk/tree/master/src/platform)**：平台相关代码
- **[flutter](https://github.com/rustdesk/rustdesk/tree/master/flutter)**：桌面端和移动端的 Flutter 代码
- **[flutter/web/js](https://github.com/rustdesk/rustdesk/tree/master/flutter/web/v1/js)**：Flutter Web 客户端使用的 JavaScript

## 截图

![连接管理器](https://github.com/rustdesk/rustdesk/assets/28412477/db82d4e7-c4bc-4823-8e6f-6af7eadf7651)

![已连接到 Windows 电脑](https://github.com/rustdesk/rustdesk/assets/28412477/9baa91e9-3362-4d06-aa1a-7518edcbd7ea)

![文件传输](https://github.com/rustdesk/rustdesk/assets/28412477/39511ad3-aa9a-4f8c-8947-1cce286a46ad)

![TCP 隧道](https://github.com/rustdesk/rustdesk/assets/28412477/78e8708f-e87e-4570-8373-1360033ea6c5)
