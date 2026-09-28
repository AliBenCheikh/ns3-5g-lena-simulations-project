FROM gitpod/workspace-full

# ns-3 dependencies
RUN sudo apt update && sudo apt install -y \
    gcc g++ python3 python3-dev python3-setuptools \
    git cmake ninja-build pkg-config \
    libgtk-3-dev libsqlite3-dev \
    libboost-all-dev \
    libxml2 libxml2-dev \
    qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools \
    wget
