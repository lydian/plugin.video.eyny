.PHONY: test build build-eyny clean
test:
	tox -e eyny

build: build-eyny


build-eyny: PACKAGE := plugin.video.eyny
build-eyny:
	mkdir -p dist/
	cd src/  && \
	export VERSION=$$(xmllint --xpath './addon[@name="eyny"]/@version'  $(PACKAGE)/addon.xml | cut -d '=' -f 2 | sed 's/"//g') && \
	rm -f dist/$(PACKAGE)-$${VERSION}.zip && \
	zip -r ../dist/$(PACKAGE)-$${VERSION}.zip  $(PACKAGE)/ -x **/*.pyc **/*.pyo **/.\* *__pycache__*

clean:
	rm -rf dist/
	rm $(NAME)
