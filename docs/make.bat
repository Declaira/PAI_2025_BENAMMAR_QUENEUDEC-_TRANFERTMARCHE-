@ECHO OFF
pushd %~dp0
set SPHINXBUILD=sphinx-build
set BUILDDIR=_build

%SPHINXBUILD% -M html . %BUILDDIR% %SPHINXOPTS% %1
popd