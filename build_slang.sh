git clone https://github.com/MikePopoloski/slang.git

cd ./slang

cmake -B build
cmake --build build

cd ..

export PATH=$PATH:"$(pwd)/slang/build/bin"

slang --version