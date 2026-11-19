# Experimental OBS RPM: do not ship as a stable release until live session tests.
Name:           tres
Version:        1.0.1
Release:        0.1%{?dist}
Summary:        Minimal three-square Wayland desktop session
License:        GPL-3.0-only
URL:            https://github.com/Drmgiver/tres
Source0:        %{name}-%{version}.tar.xz
BuildArch:      noarch

BuildRequires:  python3
Requires:       python3
Requires:       python3-gobject
Requires:       labwc
Requires:       wlrctl
Requires:       foot
Requires:       swaybg
Requires:       grim
Requires:       slurp
Requires:       wlr-randr
%if 0%{?suse_version}
Requires:       typelib-1_0-GtkLayerShell-0_1
%else
Requires:       gtk-layer-shell
%endif
Recommends:     lxpolkit
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
Recommends:     xdg-desktop-portal-wlr

%description
Tres provides three small, configurable squares for application menus,
running windows, and desktop controls in a standalone Labwc Wayland session.
Installing Tres adds a login-session choice without replacing other desktops.

%prep
%setup -q

%build
# Tres is Python and shell source; no compilation is necessary.

%install
install -d %{buildroot}%{_datadir}/tres
install -d %{buildroot}%{_bindir}
install -d %{buildroot}/usr/lib/tres
install -d %{buildroot}%{_datadir}/wayland-sessions
install -d %{buildroot}%{_datadir}/applications
install -m 0644 src/*.py %{buildroot}%{_datadir}/tres/
install -m 0644 packaging/deb/autostart %{buildroot}%{_datadir}/tres/autostart
chmod 0755 %{buildroot}%{_datadir}/tres/autostart
install -m 0644 packaging/deb/menu.xml %{buildroot}%{_datadir}/tres/menu.xml
install -m 0644 scripts/tres-portals.conf %{buildroot}%{_datadir}/tres/tres-portals.conf
install -m 0755 scripts/migrate-legacy.sh %{buildroot}%{_datadir}/tres/migrate-legacy.sh

for command in tres-panel tres-config tres-open-files tres-open-terminal \
    tres-wallpaper tres-screenshot tres-search tres-panel-supervisor \
    tres-panel-control tres-synaptic; do
    install -m 0755 "packaging/deb/$command" "%{buildroot}%{_bindir}/$command"
done
install -m 0755 packaging/rpm/tres-session %{buildroot}%{_bindir}/tres-session
for helper in tres-session.sh tres-panel-supervisor.sh tres-polkit-agent.sh \
    tres-synaptic.sh install-search-shortcut.sh restore-panel-mouse.sh; do
    install -m 0755 "scripts/$helper" "%{buildroot}/usr/lib/tres/$helper"
done
install -m 0644 packaging/deb/tres.desktop %{buildroot}%{_datadir}/wayland-sessions/tres.desktop
install -m 0644 packaging/deb/tres-screenshot.desktop %{buildroot}%{_datadir}/applications/tres-screenshot.desktop

%check
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

%files
%license LICENSE
%doc README.md
%{_bindir}/tres-*
%dir %{_datadir}/tres
%dir %{_datadir}/wayland-sessions
%{_datadir}/tres/*
%dir /usr/lib/tres
/usr/lib/tres/*
%{_datadir}/wayland-sessions/tres.desktop
%{_datadir}/applications/tres-screenshot.desktop

%changelog
* Wed Nov 18 2026 Tres Project <drmgiver@gmail.com> - 1.0.1-0.1
- Initial experimental OBS RPM packaging; not a published stable release.
