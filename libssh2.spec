# Fedora 10 onwards support noarch subpackages; by using one, we can
# put the arch-independent docs in a common subpackage and save lots
# of space on the mirrors
%if 0%{?fedora} > 9 || 0%{?rhel} > 5
%global noarch_docs_package 1
%else
%global noarch_docs_package 0
%endif

# Define %%{__isa_bits} for old releases
%{!?__isa_bits: %global __isa_bits %((echo '#include <bits/wordsize.h>'; echo __WORDSIZE) | cpp - | grep -Ex '32|64')}

Name:		libssh2
Version:	1.4.3
Release:	16.1%{?dist}
Summary:	A library implementing the SSH2 protocol
Group:		System Environment/Libraries
License:	BSD
URL:		http://www.libssh2.org/
Source0:	http://libssh2.org/download/libssh2-%{version}.tar.gz
Source1:	libssh2.pc
Patch0:		libssh2-1.4.2-utf8.patch
Patch1:		0001-sftp-seek-Don-t-flush-buffers-on-same-offset.patch
Patch2:		0002-sftp-statvfs-Along-error-path-reset-the-correct-stat.patch
Patch3:		0003-sftp-Add-support-for-fsync-OpenSSH-extension.patch
Patch4:		0004-partially-revert-window_size-explicit-adjustments-on.patch
Patch5:		0005-channel.c-fix-a-use-after-free.patch
Patch6:		0006-_libssh2_channel_write-client-spins-on-write-when-wi.patch
Patch7:		0007-window_size-redid-window-handling-for-flow-control-r.patch
Patch8:		0008-_libssh2_channel_read-fix-data-drop-when-out-of-wind.patch
Patch9:		0009-_libssh2_channel_read-Honour-window_size_initial.patch
Patch10:	0010-Set-default-window-size-to-2MB.patch
Patch11:	0011-channel_receive_window_adjust-store-windows-size-alw.patch
Patch12:	0012-libssh2_agent_init-init-fd-to-LIBSSH2_INVALID_SOCKET.patch
Patch13:	libssh2-1.4.3-cmake.patch
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-root-%(id -nu)
BuildRequires:	cmake
BuildRequires:	git
BuildRequires:	openssl-devel
BuildRequires:	zlib-devel
BuildRequires:	/usr/bin/man

# Test suite requirements - we run the OpenSSH server and try to connect to it
BuildRequires:	openssh-server
# We use matchpathcon to get the correct SELinux context for the ssh server
# initialization script so that it can transition correctly in an SELinux
# environment; matchpathcon is only available from FC-4 and moved from the
# libselinux to libselinux-utils package in F-10
%if (0%{?fedora} >= 4 || 0%{?rhel} >= 5) && !(0%{?fedora} >=17 || 0%{?rhel} >=7)
BuildRequires:	/usr/sbin/matchpathcon selinux-policy-targeted
%endif

%description
libssh2 is a library implementing the SSH2 protocol as defined by
Internet Drafts: SECSH-TRANS(22), SECSH-USERAUTH(25),
SECSH-CONNECTION(23), SECSH-ARCH(20), SECSH-FILEXFER(06)*,
SECSH-DHGEX(04), and SECSH-NUMBERS(10).

%package	devel
Summary:	Development files for libssh2
Group:		Development/Libraries
Requires:	%{name} = %{version}-%{release}
Requires:	pkgconfig

%description	devel
The libssh2-devel package contains libraries and header files for
developing applications that use libssh2.

%package	docs
Summary:	Documentation for libssh2
Group:		Development/Libraries
Requires:	%{name} = %{version}-%{release}
%if %{noarch_docs_package}
BuildArch:	noarch
%endif

%description	docs
The libssh2-docs package contains man pages and examples for
developing applications that use libssh2.

%prep
%setup -q

# remove auto-generated files
rm -v {src,example}/libssh2_config.h.in
find -name Makefile.in -delete

# use git to apply patches
git init
git config user.email 'buildsys@fedoraproject.org'
git config user.name 'Fedora Koji Build System'
git add --all
git commit -m init
git branch init
%global __patch sh -c 'git am --keep-cr'

# Make sure things are UTF-8...
%patch0 -p1

# Three upstream patches required for qemu ssh block driver.
%patch1 -p1
%patch2 -p1
%patch3 -p1

# http://thread.gmane.org/gmane.network.ssh.libssh2.devel/6428
%patch4 -p1

# https://trac.libssh2.org/ticket/268
%patch5 -p1

# Fix curl's excessive memory consumption during scp download
%patch6 -p1
%patch7 -p1
%patch8 -p1
%patch9 -p1
%patch10 -p1
%patch11 -p1

# prevent a not-connected agent from closing STDIN (#1147717)
%patch12 -p1

# add support for the CMake build system
%patch13 -p1
sed -e 's/LIBRARY DESTINATION lib/LIBRARY DESTINATION ${LIB_INSTALL_DIR}/' \
    -i src/CMakeLists.txt

# Replace hard wired port number in the test suite to avoid collisions
# between 32-bit and 64-bit builds running on a single build-host
sed -i s/4711/47%{?__isa_bits}/ tests/{ssh2.c,sshd_fixture.sh.in}

# Make sshd transition appropriately if building in an SELinux environment
%if !(0%{?fedora} >= 17 || 0%{?rhel} >= 7)
chcon $(/usr/sbin/matchpathcon -n /etc/rc.d/init.d/sshd) tests/ssh2.sh || :
chcon -R $(/usr/sbin/matchpathcon -n /etc) tests/etc || :
chcon $(/usr/sbin/matchpathcon -n /etc/ssh/ssh_host_key) tests/etc/{host,user} || :
%endif

%build
mkdir libssh2_build
cd libssh2_build
%{cmake} .. -DBUILD_SHARED_LIBS=ON
make %{?_smp_mflags}

%install
rm -rf %{buildroot}
cd libssh2_build
make install DESTDIR=%{buildroot} INSTALL="install -p"

# avoid multilib conflict on libssh2-devel
cd ..
rm -f example/Makefile.am
mv -v example example.%{_arch}

# TODO make CMake take care of this
install -D -m0644 -p %{SOURCE1} %{buildroot}%{_libdir}/pkgconfig/libssh2.pc

# remove redundant files installed by CMake
rm -rf %{buildroot}/usr/{lib/cmake,share/libssh2}

%check
echo "Running tests for %{_arch}"
# The SSH test will fail if we don't have /dev/tty, as is the case in some
# versions of mock (#672713)
if [ ! -c /dev/tty ]; then
	echo Skipping SSH test due to missing /dev/tty
	echo "exit 0" > tests/ssh2.sh
fi
# Apparently it fails in the sparc and arm buildsystems too
%ifarch %{sparc} %{arm}
echo Skipping SSH test on sparc/arm
echo "exit 0" > tests/ssh2.sh
%endif
# mansyntax check fails on PPC* and aarch64 with some strange locale error
%ifarch ppc %{power64} aarch64
echo "Skipping mansyntax test on PPC* and aarch64"
echo "exit 0" > tests/mansyntax.sh
%endif
cd libssh2_build
make test

%clean
rm -rf %{buildroot}

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%files
%{!?_licensedir:%global license %%doc}
%license COPYING
%doc AUTHORS ChangeLog README NEWS
%{_libdir}/libssh2.so.1
%{_libdir}/libssh2.so.1.*

%files docs
%doc HACKING
%{_mandir}/man3/libssh2_*.3*

%files devel
%doc example.%{_arch}/
%{_includedir}/libssh2.h
%{_includedir}/libssh2_publickey.h
%{_includedir}/libssh2_sftp.h
%{_libdir}/libssh2.so
%{_libdir}/pkgconfig/libssh2.pc

%changelog
* Mon Dec 08 2014 Kamil Dudka <kdudka@redhat.com> 1.4.3-16.1
- use git to apply patches
- use CMake as the build system

* Fri Oct 10 2014 Kamil Dudka <kdudka@redhat.com> 1.4.3-16
- prevent a not-connected agent from closing STDIN (#1147717)

* Sun Aug 17 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.3-15
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Fri Jul 18 2014 Tom Callaway <spot@fedoraproject.org> - 1.4.3-14
- fix license handling

* Sat Jun 07 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.3-13
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Wed Apr 30 2014 Kamil Dudka <kdudka@redhat.com> 1.4.3-12
- Fix curl's excessive memory consumption during scp download

* Mon Feb 17 2014 Paul Howarth <paul@city-fan.org> - 1.4.3-11
- The aarch64 buildroot seems to have the same locale issue as the PPC one

* Mon Feb 17 2014 Karsten Hopp <karsten@redhat.com> 1.4.3-10
- Next attempt to work around a self check problem on PPC*

* Mon Feb 17 2014 Karsten Hopp <karsten@redhat.com> 1.4.3-9
- Skip self checks on ppc*

* Wed Aug 14 2013 Kamil Dudka <kdudka@redhat.com> 1.4.3-8
- Fix very slow sftp upload to localhost
- Fix a use after free in channel.c

* Sat Aug 03 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.3-7
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue Apr  9 2013 Paul Howarth <paul@city-fan.org> 1.4.3-6
- Revert 'Modernize the spec file' so as to retain EL-5 spec compatibility

* Tue Apr  9 2013 Richard W.M. Jones <rjones@redhat.com> 1.4.3-5
- Add three patches from upstream git required for qemu ssh block driver
- Modernize the spec file:
  * Remove BuildRoot
  * Remove Group
  * Remove clean section
  * Don't need to clean up buildroot before installing

* Wed Apr  3 2013 Paul Howarth <paul@city-fan.org> 1.4.3-4
- Avoid polluting libssh2.pc with linker options (#947813)

* Tue Mar 26 2013 Kamil Dudka <kdudka@redhat.com> 1.4.3-3
- Avoid collisions between 32-bit and 64-bit builds running on a single build
  host

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.3-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Wed Nov 28 2012 Paul Howarth <paul@city-fan.org> 1.4.3-1
- Update to 1.4.3
  - compression: add support for zlib@openssh.com
  - sftp_read: return error if a too large package arrives
  - libssh2_hostkey_hash.3: update the description of return value
  - Fixed MSVC NMakefile
  - examples: use stderr for messages, stdout for data
  - openssl: do not leak memory when handling errors
  - improved handling of disabled MD5 algorithm in OpenSSL
  - known_hosts: Fail when parsing unknown keys in known_hosts file
  - configure: gcrypt doesn't come with pkg-config support
  - session_free: wrong variable used for keeping state
  - libssh2_userauth_publickey_fromfile_ex.3: mention publickey == NULL
  - comp_method_zlib_decomp: handle Z_BUF_ERROR when inflating
- Drop upstreamed patches

* Wed Nov 07 2012 Kamil Dudka <kdudka@redhat.com> 1.4.2-4
- examples: use stderr for messages, stdout for data (upstream commit b31e35ab)
- Update libssh2_hostkey_hash(3) man page (upstream commit fe8f3deb)

* Wed Sep 26 2012 Kamil Dudka <kdudka@redhat.com> 1.4.2-3
- Fix basic functionality of libssh2 in FIPS mode
- Skip SELinux-related quirks on recent distros to prevent a test-suite failure

* Thu Jul 19 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 1.4.2-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Sun May 20 2012 Paul Howarth <paul@city-fan.org> 1.4.2-1
- Update to 1.4.2
  - Return LIBSSH2_ERROR_SOCKET_DISCONNECT on EOF when reading banner
  - userauth.c: fread() from public key file to correctly detect any errors
  - configure.ac: add option to disable build of the example applications
  - added 'Requires.private:' line to libssh2.pc
  - SFTP: filter off incoming "zombie" responses
  - gettimeofday: no need for a replacement under cygwin
  - SSH_MSG_CHANNEL_REQUEST: default to want_reply
  - win32/libssh2_config.h: remove hardcoded #define LIBSSH2_HAVE_ZLIB

* Fri Apr 27 2012 Paul Howarth <paul@city-fan.org> 1.4.1-2
- Fix multi-arch conflict again (#816969)

* Thu Apr  5 2012 Paul Howarth <paul@city-fan.org> 1.4.1-1
- Update to 1.4.1
  - Build error with gcrypt backend
  - Always do "forced" window updates to avoid corner case stalls
  - aes: the init function fails when OpenSSL has AES support
  - transport_send: finish in-progress key exchange before sending data
  - channel_write: acknowledge transport errors
  - examples/x11.c: make sure sizeof passed to read operation is correct
  - examples/x11.c: fix suspicious sizeof usage
  - sftp_packet_add: verify the packet before accepting it
  - SFTP: preserve the original error code more
  - sftp_packet_read: adjust window size as necessary
  - Use safer snprintf rather then sprintf in several places
  - Define and use LIBSSH2_INVALID_SOCKET instead of INVALID_SOCKET
  - sftp_write: cannot return acked data *and* EAGAIN
  - sftp_read: avoid data *and* EAGAIN
  - libssh2.h: add missing prototype for libssh2_session_banner_set()
- Drop upstream patches now included in release tarball

* Mon Mar 19 2012 Kamil Dudka <kdudka@redhat.com> 1.4.0-4
- Don't ignore transport errors when writing to channel (#804150)

* Sun Mar 18 2012 Paul Howarth <paul@city-fan.org> 1.4.0-3
- Don't try to use openssl's AES-CTR functions
  (http://www.libssh2.org/mail/libssh2-devel-archive-2012-03/0111.shtml)

* Fri Mar 16 2012 Paul Howarth <paul@city-fan.org> 1.4.0-2
- fix libssh2 failing key re-exchange when write channel is saturated (#804156)
- drop %%defattr, redundant since rpm 4.4

* Wed Feb  1 2012 Paul Howarth <paul@city-fan.org> 1.4.0-1
- update to 1.4.0
  - added libssh2_session_supported_algs()
  - added libssh2_session_banner_get()
  - added libssh2_sftp_get_channel()
  - libssh2.h: bump the default window size to 256K
  - sftp-seek: clear EOF flag
  - userauth: provide more informations if ssh pub key extraction fails
  - ssh2_exec: skip error outputs for EAGAIN
  - LIBSSH2_SFTP_PACKET_MAXLEN: increase to 80000
  - knownhost_check(): don't dereference ext if NULL is passed
  - knownhost_add: avoid dereferencing uninitialized memory on error path
  - OpenSSL EVP: fix threaded use of structs
  - _libssh2_channel_read: react on errors from receive_window_adjust
  - sftp_read: cap the read ahead maximum amount
  - _libssh2_channel_read: fix non-blocking window adjusting 
- add upstream patch fixing undefined function reference in libgcrypt backend
- BR: /usr/bin/man for test suite

* Sun Jan 15 2012 Peter Robinson <pbrobinson@fedoraproject.org> 1.3.0-4
- skip the ssh test on ARM too

* Fri Jan 13 2012 Paul Howarth <paul@city-fan.org> 1.3.0-3
- make docs package noarch where possible
- example includes arch-specific bits, so move to devel package
- use patch rather than scripted iconv to fix character encoding
- don't make assumptions about SELinux context types used for the ssh server
  in the test suite
- skip the ssh test if /dev/tty isn't present, as in some versions of mock
- make the %%files list more explicit
- use tabs for indentation

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> 1.3.0-2
- rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Thu Sep 08 2011 Kamil Dudka <kdudka@redhat.com> 1.3.0-1
- update to 1.3.0

* Sat Jun 25 2011 Dennis Gilmore <dennis@ausil.us> 1.2.7-2
- sshd/loopback test fails in the sparc buildsystem

* Tue Oct 12 2010 Kamil Dudka <kdudka@redhat.com> 1.2.7-1
- update to 1.2.7 (#632916)
- avoid multilib conflict on libssh2-docs
- avoid build failure in mock with SELinux in the enforcing mode (#558964)

* Fri Mar 12 2010 Chris Weyl <cweyl@alumni.drew.edu> 1.2.4-1
- update to 1.2.4
- drop old patch0
- be more aggressive about keeping .deps from intruding into -docs

* Wed Jan 20 2010 Chris Weyl <cweyl@alumni.drew.edu> 1.2.2-5
- pkgconfig dep should be with -devel, not -docs

* Mon Jan 18 2010 Chris Weyl <cweyl@alumni.drew.edu> 1.2.2-4
- enable tests; conditionalize sshd test, which fails with a funky SElinux
  error when run locally

* Mon Jan 18 2010 Chris Weyl <cweyl@alumni.drew.edu> 1.2.2-3
- patch w/1aba38cd7d2658146675ce1737e5090f879f306; not yet in a GA release

* Thu Jan 14 2010 Chris Weyl <cweyl@alumni.drew.edu> 1.2.2-2
- correct bad file entry under -devel

* Thu Jan 14 2010 Chris Weyl <cweyl@alumni.drew.edu> 1.2.2-1
- update to 1.2.2
- drop old patch now in upstream
- add new pkgconfig file to -devel

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
