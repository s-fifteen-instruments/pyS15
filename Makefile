.PHONY: clean
all: g2lib

g2lib:
	$(MAKE) -C S15lib/g2lib

clean:
	$(MAKE) clean -C S15lib/g2lib
