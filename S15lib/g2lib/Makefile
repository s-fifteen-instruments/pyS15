.PHONY: clean
all: clean
	rm -f delta.so
	python3 setup.py build_ext --inplace
	mv *.so delta.so
	make post_build

post_build:
	rm -f delta.c
	rm -rf ./build

clean: post_build
	rm -f delta.so
