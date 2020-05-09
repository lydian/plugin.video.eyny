.phony: test
NAME := $$(xmllint --xpath './addon[@name="eyny"]/@id'  addon.xml | cut -d '=' -f 2 | sed 's/"//g')
VERSION := $$(xmllint --xpath './addon[@name="eyny"]/@version'  addon.xml | cut -d '=' -f 2 | sed 's/"//g')

test:
	tox

build:
	mkdir -p dist/
	zip -r dist/$(NAME)-$(VERSION).zip  ./ \
	    -i addon.xml \
	       addon.py \
	       changelog.txt \
	       README.md  \
	       resources/**\/*.png \
	       resources/**\/*.py

