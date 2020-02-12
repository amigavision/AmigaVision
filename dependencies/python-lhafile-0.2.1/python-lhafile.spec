%define name python-lhafile
%define version 0.1.0fs4
%define unmangled_version 0.1.0fs4
%define release 1

Summary: LHA archive support for Python
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: BSD-3-Clause
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
Vendor: Frode Solheim <frode-code@fengestad.no>
Url: http://fengestad.no/python-lhafile
BuildRequires: python-devel fdupes

%description
This project is an updated version of the project found at
http://trac.neotitans.net/wiki/lhafile. It is primarily used as a component
in FS-UAE Launcher to index and extract files from .lha archives. The project
consists of a Python package (lhafile) and a C extension for Python (lzhlib).

%prep
%setup -n %{name}-%{unmangled_version}

%build
env CFLAGS="$RPM_OPT_FLAGS" python setup.py build

%install
python setup.py install -O1 \
--prefix=%{_prefix} \
--root=$RPM_BUILD_ROOT
%fdupes %{python_sitearch}

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
%{python_sitearch}/*
