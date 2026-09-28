#!/bin/bash

set -e

# Clone ns-3 with 5G-LENA
if [ ! -d "ns-3-dev" ]; then
    git clone https://gitlab.com/nsnam/ns-3-dev.git
fi

cd ns-3-dev

# Enable 5G-LENA module
./ns3 configure --enable-examples --enable-tests

# Build
./ns3 build

