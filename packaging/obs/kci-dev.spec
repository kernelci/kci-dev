#
# spec file for package kci-dev
#

# Please submit bugfixes or comments via https://github.com/kernelci/kci-dev
#

%define srcname kci-dev

Name:           kci-dev
Version:        0
Release:        0
Summary:        KernelCI command-line tools for kernel developers
License:        LGPL-2.1-or-later
URL:            https://github.com/kernelci/kci-dev
Source0:        https://github.com/kernelci/kci-dev/archive/refs/tags/v%{version}.tar.gz
BuildArch:      noarch

%if 0%{?suse_version}
BuildRequires: python-rpm-macros
BuildRequires: %{python_module poetry-core}
BuildRequires: %{python_module devel}
BuildRequires: %{python_module build}
BuildRequires: %{python_module installer}
BuildRequires: %{python_module pip}
BuildRequires: %{python_module wheel}
BuildRequires: %{python_module setuptools}
%else
BuildRequires: pyproject-rpm-macros
BuildRequires: python3-poetry-core
BuildRequires: python3-build
BuildRequires: python3-pip
BuildRequires: python3-installer
BuildRequires: python3-devel
%endif

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

%if 0%{?suse_version}
%else
%pyproject_save_files kcidev
%endif

install -Dpm0644 completions/kci-dev-completion.bash %{buildroot}%{_datadir}/bash-completion/completions/kci-dev || :
install -Dpm0644 completions/_kci-dev %{buildroot}%{_datadir}/zsh/site-functions/_kci-dev || :
install -Dpm0644 completions/kci-dev.fish %{buildroot}%{_datadir}/fish/vendor_completions.d/kci-dev.fish || :
install -Dpm0644 packaging/obs/kci-dev.1 %{buildroot}%{_mandir}/man1/kci-dev.1

%check
%{python3} -m compileall -q kcidev

%if 0%{?suse_version}
%files
%doc README.md docs/*
%license LICENSE
%{_bindir}/kci-dev
%{python3_sitelib}/kcidev*
%{python3_sitelib}/kci_dev-*.dist-info/
%dir %{_datadir}/bash-completion
%dir %{_datadir}/bash-completion/completions
%dir %{_datadir}/zsh
%dir %{_datadir}/zsh/site-functions
%dir %{_datadir}/fish
%dir %{_datadir}/fish/vendor_completions.d
%{_datadir}/bash-completion/completions/kci-dev
%{_datadir}/zsh/site-functions/_kci-dev
%{_datadir}/fish/vendor_completions.d/kci-dev.fish
%{_mandir}/man1/kci-dev.1%{?ext_man}
/usr/lib/python3.*/site-packages/kcidev/*
/usr/lib/python3.*/site-packages/kcidev/**/*
/usr/lib/python3.*/site-packages/kci_dev-*.dist-info/*
%else
%files -f %{pyproject_files}
%doc README.md docs/*
%license LICENSE
%{_bindir}/kci-dev
%{_datadir}/bash-completion/completions/kci-dev
%{_datadir}/zsh/site-functions/_kci-dev
%{_datadir}/fish/vendor_completions.d/kci-dev.fish
%{_mandir}/man1/kci-dev.1*
%endif

%changelog
* Thu Jul 30 2026 KernelCI Project <kernelci@groups.io> - 0-0
- Initial RPM package
