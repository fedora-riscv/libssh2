Name:           libssh2
Version:        1.2
Release:        2%{?dist}
Summary:        A library implementing the SSH2 protocol

Group:          System Environment/Libraries
License:        BSD
URL:            http://www.libssh2.org/
Source0:        http://libssh2.org/download/libssh2-%{version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Patch0:         transport_c_7a9d369.patch

BuildRequires:  openssl-devel
BuildRequires:  zlib-devel

%description
libssh2 is a library implementing the SSH2 protocol as defined by
Internet Drafts: SECSH-TRANS(22), SECSH-USERAUTH(25),
SECSH-CONNECTION(23), SECSH-ARCH(20), SECSH-FILEXFER(06)*,
SECSH-DHGEX(04), and SECSH-NUMBERS(10).


%package        devel
Summary:        Development files for %{name}
Group:          Development/Libraries
Requires:       %{name} = %{version}-%{release}

%description    devel
The %{name}-devel package contains libraries and header files for
developing applications that use %{name}.

%package        docs
Summary:        Documentation for %{name}
Group:          Development/Libraries
Requires:       %{name} = %{version}-%{release}

%description    docs
The %{name}-docs package contains man pages and examples for
developing applications that use %{name}.


%prep
%setup -q
%patch0 -p1

# make sure things are UTF-8...
for i in ChangeLog NEWS ; do
    iconv --from=ISO-8859-1 --to=UTF-8 $i > new
    mv new $i
done

%build
%configure --disable-static --enable-shared

make %{?_smp_mflags}


%install
rm -rf %{buildroot}

make install DESTDIR=%{buildroot} INSTALL="install -p"
find %{buildroot} -name '*.la' -exec rm -f {} +

# clean things up a bit for packaging
( cd example && make clean )
rm -rf example/simple/.deps
find example/ -type f '(' -name '*.am' -o -name '*.in' ')' -exec rm -v {} +

%check
# tests are currently not doing so well under rpmbuild
#(cd tests && make check)

%clean
rm -rf %{buildroot}


%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig


%files
%defattr(-,root,root,-)
%doc AUTHORS ChangeLog COPYING README NEWS
%{_libdir}/*.so.*

%files docs
%defattr(-,root,root,-)
%doc COPYING HACKING example/
%{_mandir}/man?/*

%files devel
%defattr(-,root,root,-)
%doc COPYING
%{_includedir}/*
%{_libdir}/*.so

%changelog
* Mon Sep 21 2009 Chris Weyl <cweyl@alumni.drew.edu> 1.2-2
- patch based on 683aa0f6b52fb1014873c961709102b5006372fc
- disable tests (*sigh*)

* Tue Aug 25 2009 Chris Weyl <cweyl@alumni.drew.edu> 1.2-1
- update to 1.2

* Fri Aug 21 2009 Tomas Mraz <tmraz@redhat.com> - 1.0-4
- rebuilt with new openssl

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.0-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Mon Feb 16 2009 Chris Weyl <cweyl@alumni.drew.edu> 1.0-1
- update to 1.0

* Sat Jan 17 2009 Tomas Mraz <tmraz@redhat.com> - 0.18-8
- rebuild with new openssl

* Mon Feb 18 2008 Fedora Release Engineering <rel-eng@fedoraproject.org> - 0.18-7
- Autorebuild for GCC 4.3

* Wed Dec 05 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.18-6
- rebuild for new openssl...

* Tue Nov 27 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.18-5
- bump

* Tue Nov 27 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.18-4
- add INSTALL arg to make install vs env. var

* Mon Nov 26 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.18-3
- run tests; don't package test

* Sun Nov 18 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.18-2
- split docs into -docs (they seemed... large.)

* Tue Nov 13 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.18-1
- update to 0.18

* Sun Oct 14 2007 Chris Weyl <cweyl@alumni.drew.edu> 0.17-1
- update to 0.17
- many spec file changes

* Wed May 23 2007 Sindre Pedersen Bjørdal <foolish[AT]guezz.net> - 0.15-0.2.20070506
- Fix release tag
- Move manpages to -devel package
- Add Examples dir to -devel package

* Sun May 06 2007 Sindre Pedersen Bjørdal <foolish[AT]guezz.net> - 0.15-0.20070506.1
- Initial build
