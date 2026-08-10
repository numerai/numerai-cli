#!/bin/bash

{
  # Install xcode cli tools if not found
  if [[ $(which xcode-select) = "xcode-select not installed" ]]; then
    echo "Xcode command line tools not found, installing now..."
    xcode-select --installed
  fi

  # Install Python 3.12.10 if not found. Its universal2 installer supports
  # both Intel and Apple Silicon on macOS 10.13 or later.
  if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 not found, installing now..."

    sys_ver_os=$(sw_vers -productVersion)
    sys_ver_major=${sys_ver_os%%.*}
    sys_ver_minor=${sys_ver_os#*.}
    sys_ver_minor=${sys_ver_minor%%.*}
    if (( sys_ver_major > 10 || (sys_ver_major == 10 && sys_ver_minor >= 13) )); then
      echo "macOS 10.13 or later detected, installing Python 3.12.10"
      curl -fL https://www.python.org/ftp/python/3.12.10/python-3.12.10-macos11.pkg --output ~/Downloads/python-3.12.10-installer.pkg
      sudo installer -pkg ~/Downloads/python-3.12.10-installer.pkg -target /

    else
      echo "Your macOS version is too old, consider updating to 10.13 before installing Python..."
      echo $sys_ver_os
      exit 1
    fi

    echo "Python 3.12.10 installed!"
  else
    echo "Python 3 installed!"
  fi

  if [[ $(which docker) = "docker not found" ]]; then
    echo "Docker not found, downloading Docker Desktop now..."
    curl https://desktop.docker.com/mac/stable/Docker.dmg --output ~/Downloads/docker-installer.dmg

    echo "Installing..."
    MOUNTDIR=$(echo `hdiutil mount ~/Downloads/docker-installer.dmg | tail -1 | awk '{$1=$2=""; print $0}'` | xargs -0 echo)
    cp -R "${MOUNTDIR}/Docker.app" "${MOUNTDIR}/Applications/Docker.app"

    echo "Cleaning up..."
    hdiutil unmount "${MOUNTDIR}"
    rm docker.dmg

    echo "Starting Docker, please walk through the setup steps to finish the installation..."
    open /Applications/Docker.app

    echo "Docker started! After finishing the install, run 'docker' in your terminal to ensure it's installed."
  else
    echo "Docker installed!"
  fi

  echo "Setup done, ready for you to install numerai-cli :)"
} || {
  echo "Setup script failed, please include the following along with the error if you report this:"
  system_profiler SPSoftwareDataType
  system_profiler SPHardwareDataType
}
