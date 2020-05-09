.phony: test
NAME := $(shell xmllint --xpath './addon[@name="eyny"]/@id'  addon.xml | cut -d '=' -f 2 | sed 's/"//g')
VERSION := $(shell xmllint --xpath './addon[@name="eyny"]/@version'  addon.xml | cut -d '=' -f 2 | sed 's/"//g')
test:
	tox

build:
	mkdir -p dist/
	ln -s ./ $(NAME)
	zip -r dist/$(NAME)-$(VERSION).zip  $(NAME)/ \
	    -i $(NAME)/addon.xml \
	       $(NAME)/addon.py \
	       $(NAME)/changelog.txt \
	       $(NAME)/README.md  \
	       $(NAME)/resources/**\/*.png \
	       $(NAME)/resources/**\/*.py

clean:
	rm -rf dist/
	rm $(NAME)
