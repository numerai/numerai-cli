#!/bin/bash

set -e

{
  # Install xcode cli tools if not found
  if [[ $(which xcode-select) = "xcode-select not installed" ]]; then
    echo "Xcode command line tools not found, installing now..."
    xcode-select --installed
  fi

  # Install Python 3.9.1 if not found, checks for OS X 10.9 or later and Intel vs. Apple Silicon
  if [[ $(which python3) = "python3 not installed" ]]; then
    echo "Python 3 not found, installing now..."

    sys_ver_os=$(system_profiler SPSoftwareDataType | grep "System Version:")
    if [[ $sys_ver =~ .*[macOS 11\.|OS X 10\.[9|1\d]] || ]]; then
      echo "Mac OS 10.9 or later detected, installing Python 3.9.1"

      sys_ver_chip=$(system_profiler SPHardwareDataType | grep "Processor Name:" )
      if [[ $sys_ver_chip =~ .*Intel.* ]]; then
        echo "Intel chip detected..."
        curl https://www.python.org/ftp/python/3.9.1/python-3.9.1-macosx10.9.pkg --output ~/Downloads/python-3.9.1-installer.pkg
      else
        echo "Apple Silicon detected..."
        curl https://www.python.org/ftp/python/3.9.1/python-3.9.1-macos11.0.pkg --output ~/Downloads/python-3.9.1-installer.pkg
      fi
      sudo installer -pkg ~/Downloads/python-3.9.1-installer.pkg -target /

    else
      echo "Your Mac OS version is too old, consider updating to 10.9 before installing python..."
      echo $sys_ver
      exit 1
    fi

    echo "Python 3.9.1 installed!"
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