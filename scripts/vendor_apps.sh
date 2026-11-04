#!/usr/bin/env bash
set -euo pipefail

usage() {
    printf 'Usage: %s {vscode|brave} {install|remove} [--dry-run]\n' "$0"
}

app="${1:-}"
action="${2:-}"
dry_run=0
if [[ "${3:-}" == "--dry-run" ]]; then
    dry_run=1
fi

case "$app" in
    vscode)
        package=code
        vendor_name="Microsoft Visual Studio Code"
        apt_repo=/etc/apt/sources.list.d/linuxutil-studio-vscode.sources
        apt_key=/etc/apt/keyrings/linuxutil-studio-vscode.gpg
        rpm_repo=/etc/yum.repos.d/linuxutil-studio-vscode.repo
        suse_repo=/etc/zypp/repos.d/linuxutil-studio-vscode.repo
        key_url=https://packages.microsoft.com/keys/microsoft.asc
        expected_fingerprints=BC528686B50D79E339D3721CEB3E94ADBE1229CF
        apt_uri=https://packages.microsoft.com/repos/code
        ;;
    brave)
        package=brave-browser
        vendor_name="Brave Browser"
        apt_repo=/etc/apt/sources.list.d/linuxutil-studio-brave.sources
        apt_key=/etc/apt/keyrings/linuxutil-studio-brave.gpg
        rpm_repo=/etc/yum.repos.d/linuxutil-studio-brave.repo
        suse_repo=/etc/zypp/repos.d/linuxutil-studio-brave.repo
        key_url=https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg
        expected_fingerprints=$'DBF1A116C220B8C7164F98230686B78420038257\n47D32A74E9A9E013A4B4926C68D513D36A73CD96\nB2A3DCA350E67256740DF904DE4EC67BE4B0DCA0'
        apt_uri=https://brave-browser-apt-release.s3.brave.com
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac

case "$action" in
    install|remove) ;;
    *) usage >&2; exit 2 ;;
esac

os_release=/etc/os-release
if [[ ! -r "$os_release" ]]; then
    printf '[!] Cannot read %s.\n' "$os_release" >&2
    exit 1
fi
# shellcheck disable=SC1091
. "$os_release"

family=""
for candidate in "${ID:-}" ${ID_LIKE:-}; do
    case "$candidate" in
        debian|ubuntu|linuxmint|pop|elementary|zorin|kali)
            family=debian
            break
            ;;
        fedora|rhel|centos|rocky|almalinux|nobara)
            family=fedora
            break
            ;;
        opensuse*|suse)
            family=suse
            break
            ;;
    esac
done

if [[ -z "$family" ]]; then
    printf '[!] No official %s repository is configured for this distribution.\n' "$vendor_name" >&2
    printf '    Use the Flatpak fallback or install from the vendor website.\n' >&2
    exit 1
fi

state_dir=/var/lib/linuxutil-studio/vendor-repos
state_file="$state_dir/$app"

run() {
    if (( dry_run )); then
        printf '    [dry-run] %s\n' "$*"
    else
        printf '    $ %s\n' "$*"
        "$@"
    fi
}

repo_path() {
    case "$family" in
        debian) printf '%s' "$apt_repo" ;;
        fedora) printf '%s' "$rpm_repo" ;;
        suse) printf '%s' "$suse_repo" ;;
    esac
}

configure_apt_repo() {
    local architecture key_created=0
    architecture="$(dpkg --print-architecture)"
    case "$architecture" in
        amd64|arm64) ;;
        *)
            printf '[!] %s does not publish an APT package for %s.\n' "$vendor_name" "$architecture" >&2
            return 1
            ;;
    esac

    if [[ -e "$apt_repo" ]]; then
        printf '[i] Keeping existing repository file %s.\n' "$apt_repo"
        return 0
    fi

    if [[ -e "$apt_key" ]]; then
        printf '[!] Refusing to overwrite existing key file %s.\n' "$apt_key" >&2
        return 1
    fi
    command -v curl >/dev/null || {
        printf '[!] curl is required to fetch the vendor signing key.\n' >&2
        return 1
    }
    command -v gpg >/dev/null || {
        printf '[!] gpg is required to verify the vendor signing key.\n' >&2
        return 1
    }

    local fingerprints key_info primary_keys
    temp_dir="$(mktemp -d)"
    trap 'rm -f "$temp_dir/vendor-key" "$temp_dir/vendor-key.gpg" "$temp_dir/vendor.sources"; rm -rf "$temp_dir/gnupg"; rmdir "$temp_dir"' EXIT
    mkdir -m 0700 "$temp_dir/gnupg"
    curl --proto '=https' --tlsv1.2 --max-filesize 1048576 \
        --fail --location --silent --show-error "$key_url" -o "$temp_dir/vendor-key"
    key_info="$(GNUPGHOME="$temp_dir/gnupg" gpg --no-options --batch --show-keys --with-colons "$temp_dir/vendor-key")"
    primary_keys="$(printf '%s\n' "$key_info" | awk -F: '$1 == "pub" { count++ } END { print count+0 }')"
    fingerprints="$(printf '%s\n' "$key_info" |
        awk -F: '$1 == "pub" { primary=1; next } primary && $1 == "fpr" { print $10; primary=0 }')"
    if [[ "$primary_keys" != "$(printf '%s\n' "$expected_fingerprints" | awk 'NF { count++ } END { print count+0 }')" ]] ||
        [[ "$(printf '%s\n' "$fingerprints" | sort)" != "$(printf '%s\n' "$expected_fingerprints" | sort)" ]]; then
        printf '[!] Vendor signing-key fingerprint mismatch; repository was not added.\n' >&2
        return 1
    fi

    install -d -m 0755 /etc/apt/keyrings
    GNUPGHOME="$temp_dir/gnupg" gpg --no-options --batch --dearmor --yes \
        --output "$temp_dir/vendor-key.gpg" "$temp_dir/vendor-key"
    install -m 0644 "$temp_dir/vendor-key.gpg" "$apt_key"
    key_created=1

    local source_content
    source_content="Types: deb
URIs: $apt_uri
Suites: stable
Components: main
Architectures: $architecture
Signed-By: $apt_key"
    printf '%s\n' "$source_content" > "$temp_dir/vendor.sources"
    install -m 0644 "$temp_dir/vendor.sources" "$apt_repo"

    install -d -m 0755 "$state_dir"
    write_state 1 "$key_created"
}

configure_rpm_repo() {
    local target
    target="$(repo_path)"
    if [[ -e "$target" ]]; then
        printf '[i] Keeping existing repository file %s.\n' "$target"
        return 0
    fi

    install -d -m 0755 "$(dirname "$target")"
    if [[ "$app" == "vscode" ]]; then
        cat > "$target" <<'REPO'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
REPO
    else
        cat > "$target" <<'REPO'
[brave-browser]
name=Brave Browser
baseurl=https://brave-browser-rpm-release.s3.brave.com/$basearch
enabled=1
autorefresh=1
type=rpm-md
gpgcheck=1
gpgkey=https://brave-browser-rpm-release.s3.brave.com/brave-core.asc
REPO
    fi
    chmod 0644 "$target"
    install -d -m 0755 "$state_dir"
    write_state 1 0
}

write_state() {
    local repo_owned="$1" key_owned="$2"
    local repo_hash key_hash=""
    repo_hash="$(sha256sum "$(repo_path)" | awk '{print $1}')"
    if (( key_owned )); then
        key_hash="$(sha256sum "$apt_key" | awk '{print $1}')"
    fi
    printf 'repo=%s\nkey=%s\nrepo_sha256=%s\nkey_sha256=%s\n' \
        "$repo_owned" "$key_owned" "$repo_hash" "$key_hash" > "$state_file"
}

install_app() {
    if (( dry_run )); then
        printf '==> Add the official %s repository for %s\n' "$vendor_name" "$family"
        if [[ "$family" == "debian" ]]; then
            printf '    [dry-run] Download and verify pinned vendor signing-key fingerprint(s)\n'
            printf '    [dry-run] Write %s (signed-by keyring)\n' "$apt_repo"
            run apt-get update
            run apt-get install -y "$package"
        else
            printf '    [dry-run] Write %s (package signature checking enabled)\n' "$(repo_path)"
            if [[ "$family" == "fedora" ]]; then
                run dnf install -y "$package"
            else
                run zypper --non-interactive install "$package"
            fi
        fi
        printf '[+] Preview finished; nothing was changed.\n'
        return 0
    fi

    if [[ "$family" == "debian" ]]; then
        configure_apt_repo
        apt-get update
        apt-get install -y "$package"
    else
        configure_rpm_repo
        if [[ "$family" == "fedora" ]]; then
            dnf install -y "$package"
        else
            zypper --non-interactive refresh
            zypper --non-interactive install "$package"
        fi
    fi
}

remove_app() {
    if (( dry_run )); then
        if [[ "$family" == "debian" ]]; then
            run apt-get remove -y "$package"
            printf '    [dry-run] Remove only LinuxUtil-managed source/key files, if owned\n'
            run apt-get update
        elif [[ "$family" == "fedora" ]]; then
            run dnf remove -y "$package"
            printf '    [dry-run] Remove only LinuxUtil-managed repository file, if owned\n'
        else
            run zypper --non-interactive remove "$package"
            printf '    [dry-run] Remove only LinuxUtil-managed repository file, if owned\n'
        fi
        printf '[+] Preview finished; nothing was changed.\n'
        return 0
    fi

    case "$family" in
        debian) apt-get remove -y "$package" ;;
        fedora) dnf remove -y "$package" ;;
        suse) zypper --non-interactive remove "$package" ;;
    esac

    if [[ -f "$state_file" ]]; then
        local repo_owned=0 key_owned=0 repo_hash="" key_hash=""
        while IFS='=' read -r key value; do
            case "$key:$value" in
                repo:1) repo_owned=1 ;;
                key:1) key_owned=1 ;;
                repo_sha256:*) repo_hash="$value" ;;
                key_sha256:*) key_hash="$value" ;;
            esac
        done < "$state_file"

        local repo_removed=0
        if (( repo_owned )) && [[ -f "$(repo_path)" && -n "$repo_hash" ]] &&
            [[ "$(sha256sum "$(repo_path)" | awk '{print $1}')" == "$repo_hash" ]]; then
            rm -f "$(repo_path)"
            repo_removed=1
        elif (( repo_owned )) && [[ ! -e "$(repo_path)" ]]; then
            repo_removed=1
        elif (( repo_owned )); then
            printf '[!] Repository file changed since install; keeping %s.\n' "$(repo_path)"
        fi
        if (( key_owned && repo_removed )) && [[ "$family" == "debian" ]] &&
            [[ -f "$apt_key" && -n "$key_hash" ]] &&
            [[ "$(sha256sum "$apt_key" | awk '{print $1}')" == "$key_hash" ]]; then
            rm -f "$apt_key"
        elif (( key_owned && repo_removed )) && [[ -e "$apt_key" ]]; then
            printf '[!] Signing key changed since install; keeping %s.\n' "$apt_key"
        fi
        rm -f "$state_file"
        if (( repo_removed )) && [[ "$family" == "debian" ]]; then
            apt-get update
        fi
    else
        printf '[i] No LinuxUtil ownership record; leaving repository configuration untouched.\n'
    fi
}

if [[ "$action" == "install" ]]; then
    install_app
else
    remove_app
fi
