#
# spec file for package kci-dev
#

# Please submit bugfixes or comments via https://github.com/kernelci/kci-dev
#

%define srcname kci-dev

Name:           kci-dev
# Version and Release are rewritten by the Fedora GitHub Actions
# workflow using the version declared in pyproject.toml.
Version:        0
Release:        0
Summary:        KernelCI command-line tools for kernel developers
License:        LGPL-2.1-or-later
URL:            https://github.com/kernelci/kci-dev
Source0:        https://github.com/kernelci/kci-dev/archive/refs/tags/v%{version}.tar.gz
BuildArch:      noarch

BuildRequires: pyproject-rpm-macros
BuildRequires: python3-poetry-core
BuildRequires: python3-build
BuildRequires: python3-pip
BuildRequires: python3-installer
BuildRequires: python3-devel

%description
kci-dev provides command-line tools for Linux kernel developers and
maintainers to submit, monitor, and inspect KernelCI test results.

%prep
%autosetup -n %{srcname}-%{version}

%build
%pyproject_wheel

%install
%pyproject_install

# Python library modules are not executable scripts. Remove their upstream
# interpreter lines while retaining the generated command-line entry point.
find %{buildroot}%{python3_sitelib}/kcidev -type f -name '*.py' \
    -exec sed -i '1{/^#!.*python/d}' {} +

%pyproject_save_files kcidev

install -Dpm0644 completions/kci-dev-completion.bash %{buildroot}%{_datadir}/bash-completion/completions/kci-dev || :
install -Dpm0644 completions/_kci-dev %{buildroot}%{_datadir}/zsh/site-functions/_kci-dev || :
install -Dpm0644 completions/kci-dev.fish %{buildroot}%{_datadir}/fish/vendor_completions.d/kci-dev.fish || :
install -Dpm0644 docs/man/kci-dev.1 %{buildroot}%{_mandir}/man1/kci-dev.1

%check
%{python3} -m compileall -q kcidev

%files -f %{pyproject_files}
%doc README.md docs/*
%license LICENSE
%{_bindir}/kci-dev
%{_datadir}/bash-completion/completions/kci-dev
%{_datadir}/zsh/site-functions/_kci-dev
%{_datadir}/fish/vendor_completions.d/kci-dev.fish
%{_mandir}/man1/kci-dev.1*

%changelog
* Thu Jul 30 2026 KernelCI Project <kernelci@groups.io> - 0-0
- Initial RPM package
